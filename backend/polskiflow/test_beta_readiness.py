import json
from datetime import date
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase
from polskiflow.domain.beta_readiness import MANUAL, readiness_report

SHA = "a" * 40
TODAY = date(2026, 10, 10)


def evidence():
    return {"schema_version":1,"commit":SHA,"window":{"start":"2026-10-01","end":"2026-10-07"},"participants":20,
            "journey":{"started":100,"completed":95,"lost_results":0,"duplicate_results":0},
            "runtime":{"requests":1000,"server_errors":5,"response_p95_ms":2000},
            "feedback":{"open_blocking":0,"open_high":0},"manual":dict.fromkeys(MANUAL,True)}


class BetaReadinessTests(SimpleTestCase):
    def report(self, value):
        return readiness_report(value,SHA,TODAY)

    def test_boundaries_pass_without_authorizing_release(self):
        report = self.report(evidence())
        self.assertEqual(report["status"],"checks_passed")
        self.assertFalse(report["release_authorized"])
        for section, key, value in (("journey","completed",94),("runtime","server_errors",6),("runtime","response_p95_ms",2001)):
            data=evidence();data[section][key]=value
            self.assertEqual(self.report(data)["status"],"blocked")

    def test_small_empty_stale_or_unconfirmed_evidence_is_insufficient(self):
        for field,value in (("participants",19),("commit",None)):
            data=evidence();data[field]=value
            self.assertEqual(self.report(data)["status"],"insufficient_data")
        for section,key,value in (("journey","started",49),("runtime","requests",499),("manual","iphone_audio",None)):
            data=evidence();data[section][key]=value
            if section=="journey":data[section]["completed"]=49
            self.assertEqual(self.report(data)["status"],"insufficient_data")
        data=evidence();data["window"]={"start":"2026-09-01","end":"2026-09-07"}
        self.assertEqual(self.report(data)["status"],"insufficient_data")
        data=evidence();data["window"]["start"]="2026-10-02"
        self.assertEqual(self.report(data)["status"],"insufficient_data")
        template=json.loads((Path(__file__).resolve().parents[2]/"docs/beta-summary.example.json").read_text())
        self.assertEqual(self.report(template)["status"],"insufficient_data")

    def test_data_loss_duplicates_issues_failed_manual_or_wrong_commit_block(self):
        for section,key,value in (("journey","lost_results",1),("journey","duplicate_results",1),("feedback","open_blocking",1),
                                  ("feedback","open_high",1),("manual","account_deletion",False)):
            data=evidence();data[section][key]=value
            self.assertEqual(self.report(data)["status"],"blocked")
        data=evidence();data["participants"]=1;data["journey"]["lost_results"]=1
        self.assertEqual(self.report(data)["status"],"blocked","observed data loss blocks even a small sample")
        data=evidence();data["commit"]="b"*40
        self.assertEqual(self.report(data)["status"],"blocked")

    def test_strict_schema_and_consistent_counts_reject_personal_or_invalid_data(self):
        for mutate in (lambda d:d.update(email="private@example.test"),lambda d:d.update(schema_version=True),
                       lambda d:d.update(participants=True),lambda d:d["manual"].update(iphone_audio="true"),
                       lambda d:d["journey"].update(completed=101),lambda d:d["runtime"].update(server_errors=1001),
                       lambda d:d["window"].update(end="2026-10-11"),lambda d:d["feedback"].update(open_high=-1),
                       lambda d:d["window"].update(start="2026-02-30")):
            data=evidence();mutate(data)
            with self.assertRaises(ValueError):self.report(data)

    def test_command_check_fails_closed_and_never_echoes_invalid_input(self):
        with TemporaryDirectory() as directory:
            path=Path(directory)/"summary.json";path.write_text(json.dumps(evidence()))
            output=StringIO()
            with patch("polskiflow.domain.beta_readiness.date") as clock:
                clock.today.return_value=TODAY;clock.fromisoformat.side_effect=date.fromisoformat
                call_command("beta_readiness",str(path),expected_commit=SHA,check=True,stdout=output)
            self.assertEqual(json.loads(output.getvalue())["status"],"checks_passed")
            data=evidence();data["manual"]["iphone_audio"]=None;path.write_text(json.dumps(data));output=StringIO()
            with self.assertRaises(CommandError):call_command("beta_readiness",str(path),expected_commit=SHA,check=True,stdout=output)
            self.assertFalse(json.loads(output.getvalue())["release_authorized"])
            for raw in ('{"email":"private@example.test"}', '{"commit":null,"commit":null}', 'x'*16385):
                path.write_text(raw);output=StringIO()
                with self.assertRaises(CommandError) as error:call_command("beta_readiness",str(path),expected_commit=SHA,stdout=output)
                self.assertNotIn("private@example.test",str(error.exception))
                self.assertEqual(output.getvalue(),"")
