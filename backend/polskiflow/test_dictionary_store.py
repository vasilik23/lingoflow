import json
from datetime import date
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from polskiflow.dictionary_store import (
    load_personal_words,
    save_personal_word,
    save_personal_word_review,
)
from polskiflow.domain.sm2 import Sm2Result


class DictionaryStoreTests(SimpleTestCase):
    def test_unconfigured_store_stays_local(self):
        self.assertEqual(load_personal_words("token", "user"), [])
        self.assertFalse(
            save_personal_word("token", "user", "dom", "дом", "", "story")
        )

    @override_settings(
        SUPABASE_URL="https://project.supabase.co",
        SUPABASE_ANON_KEY="public-key",
        SUPABASE_AUTH_TIMEOUT=2,
    )
    @patch("polskiflow.dictionary_store.urlopen")
    def test_word_is_upserted_with_user_token(self, mocked_urlopen):
        mocked_urlopen.return_value.__enter__.return_value = MagicMock(status=201)

        saved = save_personal_word(
            "access", "user-123", "dom", "дом", "To jest dom.", "story"
        )

        self.assertTrue(saved)
        request = mocked_urlopen.call_args.args[0]
        self.assertEqual(request.headers["Authorization"], "Bearer access")
        self.assertEqual(json.loads(request.data)["user_id"], "user-123")
        self.assertIn("on_conflict=user_id%2Cword", request.full_url)

    @override_settings(
        SUPABASE_URL="https://project.supabase.co",
        SUPABASE_ANON_KEY="public-key",
        SUPABASE_AUTH_TIMEOUT=2,
    )
    @patch("polskiflow.dictionary_store.urlopen")
    def test_sm2_review_updates_only_owned_word(self, mocked_urlopen):
        mocked_urlopen.return_value.__enter__.return_value = MagicMock(status=204)
        result = Sm2Result(
            ease_factor=2.5,
            interval_days=6,
            repetitions=2,
            next_review_date=date(2026, 9, 2),
        )

        saved = save_personal_word_review(
            "access", "user-123", "word-123", result, "2026-08-27T12:00:00+00:00"
        )

        self.assertTrue(saved)
        request = mocked_urlopen.call_args.args[0]
        self.assertEqual(request.method, "PATCH")
        self.assertIn("id=eq.word-123", request.full_url)
        self.assertIn("user_id=eq.user-123", request.full_url)
        payload = json.loads(request.data)
        self.assertEqual(payload["next_review_date"], "2026-09-02")
        self.assertNotIn("user_id", payload)

    @override_settings(
        SUPABASE_URL="https://project.supabase.co",
        SUPABASE_ANON_KEY="public-key",
        SUPABASE_AUTH_TIMEOUT=2,
    )
    @patch("polskiflow.dictionary_store.urlopen")
    def test_words_are_filtered_by_authenticated_user(self, mocked_urlopen):
        response = MagicMock()
        response.read.return_value = json.dumps(
            [{"id": "word-1", "word": "dom", "translation": "дом"}]
        ).encode()
        mocked_urlopen.return_value.__enter__.return_value = response

        words = load_personal_words("access", "user-123")

        self.assertEqual(words[0]["word"], "dom")
        request = mocked_urlopen.call_args.args[0]
        self.assertIn("user_id=eq.user-123", request.full_url)
        self.assertEqual(request.headers["Authorization"], "Bearer access")


@override_settings(SUPABASE_URL='https://project.supabase.co', SUPABASE_ANON_KEY='public-key')
class ConditionalReviewStoreTests(SimpleTestCase):
    @patch('polskiflow.dictionary_store.urlopen')
    def test_conditional_patch_requires_owned_snapshot_and_representation_ack(self, urlopen):
        from urllib.parse import parse_qs, urlsplit
        from polskiflow.dictionary_store import compare_and_save_personal_word_review
        result = Sm2Result(2.5, 6, 2, date(2026, 10, 27))
        now = '2026-10-21T12:00:00+00:00'
        for previous in (None, '2026-10-20T12:00:00Z'):
            response = MagicMock()
            response.read.return_value = json.dumps([{'id': 'word-1', 'last_reviewed_at': now}]).encode()
            urlopen.return_value.__enter__.return_value = response
            self.assertEqual(compare_and_save_personal_word_review('access', 'owner', 'word-1', result, now, previous), 'saved')
            request = urlopen.call_args.args[0]
            query = parse_qs(urlsplit(request.full_url).query)
            self.assertEqual(query['user_id'], ['eq.owner'])
            self.assertEqual(query['id'], ['eq.word-1'])
            self.assertEqual(query['last_reviewed_at'], ['is.null' if previous is None else 'eq.' + previous])
            self.assertEqual(request.get_header('Prefer'), 'return=representation')
            self.assertEqual(request.get_header('Authorization'), 'Bearer access')
            self.assertEqual(json.loads(request.data)['repetitions'], 2)

    @patch('polskiflow.dictionary_store.urlopen')
    def test_empty_patch_is_stale_and_malformed_or_failed_ack_is_unavailable(self, urlopen):
        from urllib.error import URLError
        from polskiflow.dictionary_store import compare_and_save_personal_word_review
        result = Sm2Result(2.5, 6, 2, date(2026, 10, 27))
        now = '2026-10-21T12:00:00+00:00'
        for payload, expected in (([], 'stale'), ({}, 'unavailable'), ([{'id': 'other', 'last_reviewed_at': now}], 'unavailable'), ([{'id': 'word-1', 'last_reviewed_at': None}], 'unavailable')):
            response = MagicMock()
            response.read.return_value = json.dumps(payload).encode()
            urlopen.return_value.__enter__.return_value = response
            self.assertEqual(compare_and_save_personal_word_review('access', 'owner', 'word-1', result, now, None), expected)
        urlopen.side_effect = URLError('lost ACK')
        self.assertEqual(compare_and_save_personal_word_review('access', 'owner', 'word-1', result, now, None), 'unavailable')
