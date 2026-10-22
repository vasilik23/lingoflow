"""Contextual feedback, explicit self-assessment and owner-scoped repeats."""
from unittest.mock import patch
from django.test import TestCase, RequestFactory, override_settings
from polskiflow.auth import ACCESS_COOKIE, SupabaseUser
from polskiflow.learning.models import Question
from polskiflow.domain.lesson_feedback_hint import feedback_hint
from polskiflow.domain.mistake_practice import sign_mistake
from polskiflow.domain.lesson_state import sign_lesson_state
from polskiflow.lesson_views import _complete
from polskiflow.progress_store import CompletionSaveResult


@override_settings(SUPABASE_URL='', SUPABASE_ANON_KEY='')
class LearnerFeedbackTests(TestCase):
    def setUp(self):
        self.client.cookies[ACCESS_COOKIE]='access'
        auth=patch('polskiflow.auth.authenticate_access_token',return_value=SupabaseUser('learner','fixture@example.test'))
        auth.start()
        self.addCleanup(auth.stop)

    def test_a1_contrast_is_after_answer_and_never_in_ready_question(self):
        state=sign_lesson_state('learner','grammar','grammar',0,0)
        ready=self.client.post('/lesson/grammar/step/',{'state':state,'action':'start'})
        self.assertNotContains(ready,'data-feedback-hint')
        answered=self.client.post('/lesson/grammar/step/',{'state':ready.context['lesson_state'],'action':'answer','choice':'1'})
        self.assertContains(answered,'Jestem — форма для «я», jesteś — для «ты»')
        self.assertIsNone(feedback_hint('grammar',0,{'options':['Changed content'],'correct':0}))

    def test_b1_demo_hint_survives_refresh(self):
        ready=self.client.get('/demo/?level=B1&step=exercise')
        question=ready.context['lesson']['question']
        wrong=(question['correct']+1)%len(question['options'])
        checked=self.client.post('/demo/?level=B1',{'state':ready.context['state'],'answer':str(wrong)},follow=True)
        self.assertContains(checked,'Ponieważ — «потому что»')
        self.assertContains(checked,'Chociaż — «хотя»')
        refreshed=self.client.get(checked.redirect_chain[-1][0])
        self.assertContains(refreshed,'data-feedback-hint')
        self.assertEqual(refreshed.context['selected_text'],checked.context['selected_text'])

    def test_flashcard_names_self_assessment_with_buttons(self):
        page=self.client.get('/lesson/bio-review/')
        self.assertNotContains(page,'data-self-assessment')
        revealed=self.client.post('/lesson/bio-review/step/',{'state':page.context['lesson_state'],'action':'reveal'})
        self.assertContains(revealed,'data-self-assessment')
        self.assertContains(revealed,'Ответ не проверяется автоматически')
        self.assertContains(revealed,'value="know"')

    @patch('polskiflow.lesson_views.delete_lesson_draft')
    @patch('polskiflow.lesson_views.save_lesson_completion_result',return_value=CompletionSaveResult(True,False))
    def test_high_scores_still_offer_actual_mistakes_of_that_lesson(self,save,delete):
        for lesson,score,total in [('grammar',4,5),('housing-grammar',6,7),('bio-grammar',5,6)]:
            request=RequestFactory().post('/lesson/'+lesson+'/step/')
            request.supabase_access_token='access'
            request.supabase_user=SupabaseUser('learner','fixture@example.test')
            with patch('polskiflow.lesson_views.load_mistakes',return_value=[{'lesson_id':'other','question_position':0},{'lesson_id':lesson,'question_position':True},{'lesson_id':lesson,'question_position':0}]):
                response=_complete(request,lesson,score,total)
            self.assertContains(response,'/mistakes/practice/?lesson='+lesson)
            self.assertContains(response,'Балл урока не изменится')
            self.assertContains(response,'Общее закрепление')
        with patch('polskiflow.lesson_views.load_mistakes',return_value=[]):
            self.assertNotContains(_complete(request,'bio-grammar',5,6),'data-lesson-mistakes')
        with patch('polskiflow.lesson_views.load_mistakes') as load:
            self.assertNotContains(_complete(request,'bio-grammar',6,6),'data-lesson-mistakes')
            load.assert_not_called()

    @patch('polskiflow.mistake_views.load_mistakes')
    def test_scope_filters_owner_queue_and_empty_does_not_clear_other_lessons(self,load):
        load.return_value=[{'lesson_id':'grammar','question_position':0},{'lesson_id':'housing-grammar','question_position':0}]
        page=self.client.get('/mistakes/practice/?lesson=housing-grammar')
        self.assertEqual(page.context['question'].lesson_id,'housing-grammar')
        self.assertContains(page,'action="/mistakes/practice/?lesson=housing-grammar"')
        self.assertEqual(page.context['remaining'],1)
        empty=self.client.get('/mistakes/practice/?lesson=bio-grammar')
        self.assertContains(empty,'Ошибок этого урока нет')
        self.assertNotContains(empty,'Все сохранённые задания решены правильно')
        self.assertEqual(self.client.get('/mistakes/practice/?lesson=missing').status_code,400)

    @patch('polskiflow.mistake_views.set_mistake')
    @patch('polskiflow.mistake_views.load_mistakes')
    def test_post_cannot_escape_lesson_scope_or_owner(self,load,save):
        load.return_value=[{'lesson_id':'grammar','question_position':0},{'lesson_id':'housing-grammar','question_position':0}]
        for token in [sign_mistake('learner','grammar',0),sign_mistake('other','housing-grammar',0)]:
            self.assertEqual(self.client.post('/mistakes/practice/?lesson=housing-grammar',{'state':token,'choice':'1'}).status_code,400)
        save.assert_not_called()

    @patch('polskiflow.lesson_views.save_lesson_completion_result')
    @patch('polskiflow.mistake_views.set_mistake',return_value=True)
    @patch('polskiflow.mistake_views.load_mistakes',return_value=[{'lesson_id':'housing-grammar','question_position':0}])
    def test_repeat_clears_only_mistake_and_keeps_lesson_score(self,load,save,completion):
        response=self.client.post('/mistakes/practice/?lesson=housing-grammar',{'state':sign_mistake('learner','housing-grammar',0),'choice':str(Question.objects.get(lesson_id='housing-grammar',position=0).correct)})
        self.assertContains(response,'ошибка убрана из очереди')
        self.assertContains(response,'href="/mistakes/practice/?lesson=housing-grammar"')
        self.assertEqual(response.context['remaining'],0)
        save.assert_called_once_with('access','learner','housing-grammar',0,False)
        completion.assert_not_called()

    @patch('polskiflow.mistake_views.set_mistake',return_value=False)
    @patch('polskiflow.mistake_views.load_mistakes',return_value=[{'lesson_id':'housing-grammar','question_position':0}])
    def test_failed_ack_does_not_claim_removed(self,load,save):
        response=self.client.post('/mistakes/practice/?lesson=housing-grammar',{'state':sign_mistake('learner','housing-grammar',0),'choice':str(Question.objects.get(lesson_id='housing-grammar',position=0).correct)})
        self.assertContains(response,'Верно, но сохранение не подтверждено')
        self.assertNotContains(response,'ошибка убрана из очереди')
        self.assertEqual(response.context['remaining'],1)
        self.assertContains(response,'Обновить тренировку')
