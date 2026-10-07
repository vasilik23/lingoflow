import { config } from './config';

export type TodayTask = { id: string; title: string; description: string; minutes: number; emoji: string; completed: boolean; plan_type: string; reinforcement_reason: string | null };
export type LessonStep = { position: number; type: 'flashcard' | 'choice' | 'sentence_builder'; polish?: string; translation?: string; example?: string; prompt?: string; options?: string[]; tokens?: string[] };
export type NativeLesson = { lesson: { id: string; kind: string; title: string; description?: string }; theory: { title: string; sections: unknown[] } | null; steps: LessonStep[]; step_count: number };
export type AnswerResult = { correct: boolean; correct_index?: number; correct_sentence?: string; explanation: string };
export type BootstrapData = {
  profile: { display_name: string; level: string; daily_goal_lessons: number; daily_goal_minutes: number };
  progress: { streak_days: number; active_days: number; completed_lesson_count: number };
  today: { date: string; completed_count: number; task_count: number; progress_percent: number; tasks: TodayTask[]; resume: { lesson_id: string; title: string; kind: string; step: number } | null };
};
export type LessonDraft = { lesson_id: string; lesson_kind: string; step_index: number; score: number };
export type LearnerProfile = { display_name: string; level: string; daily_goal_lessons: number; daily_goal_minutes: number };
export type ReminderPreferences = { daily_reminder_enabled: boolean; reminder_time: string; timezone: string };
export type Achievement = {
  id: string;
  icon: string;
  title: string;
  description: string;
  current: number;
  target: number;
  progress_percent: number;
  unlocked: boolean;
};
export type AchievementsData = { unlocked_count: number; achievement_count: number; achievements: Achievement[] };

export async function loadBootstrap(accessToken: string): Promise<BootstrapData> {
  return apiRequest('/api/v1/me/bootstrap/', accessToken);
}

export async function loadLearnerProfile(accessToken: string): Promise<LearnerProfile> {
  const result = await apiRequest<{ profile: LearnerProfile }>('/api/v1/me/profile/', accessToken);
  return result.profile;
}

export async function updateLearnerProfile(profile: LearnerProfile, accessToken: string): Promise<LearnerProfile> {
  const result = await apiRequest<{ profile: LearnerProfile }>('/api/v1/me/profile/', accessToken, { display_name: profile.display_name, level: profile.level, daily_goal_minutes: profile.daily_goal_minutes }, 'PATCH');
  return result.profile;
}

export async function loadReminderPreferences(accessToken: string): Promise<{ preferences: ReminderPreferences; delivery_active: boolean }> {
  return apiRequest('/api/v1/me/reminder-preferences/', accessToken);
}

export function updateReminderPreferences(preferences: Pick<ReminderPreferences, 'daily_reminder_enabled' | 'reminder_time'>, accessToken: string) {
  return apiRequest<{ preferences: ReminderPreferences; delivery_active: boolean }>('/api/v1/me/reminder-preferences/', accessToken, preferences, 'PATCH');
}

export function loadAchievements(accessToken: string): Promise<AchievementsData> {
  return apiRequest('/api/v1/me/achievements/', accessToken);
}

export function loadLesson(lessonId: string, accessToken: string): Promise<NativeLesson> {
  return apiRequest(`/api/v1/lessons/${encodeURIComponent(lessonId)}/`, accessToken);
}

export async function loadLatestDraft(accessToken: string): Promise<LessonDraft | null> {
  const result = await apiRequest<{ draft: LessonDraft | null }>('/api/v1/me/lesson-drafts/latest/', accessToken);
  return result.draft;
}

export function saveLessonDraft(lessonId: string, stepIndex: number, score: number, accessToken: string) {
  return apiRequest(`/api/v1/me/lesson-drafts/${encodeURIComponent(lessonId)}/`, accessToken, { step_index: stepIndex, score }, 'PUT');
}

export function deleteLessonDraft(lessonId: string, accessToken: string) {
  return apiRequest(`/api/v1/me/lesson-drafts/${encodeURIComponent(lessonId)}/`, accessToken, undefined, 'DELETE');
}

export type FeedbackCategory = 'content' | 'translation' | 'interface' | 'technical' | 'idea';
export function sendFeedback(category: FeedbackCategory, message: string, accessToken: string) {
  return apiRequest<{ created: boolean; status: string }>('/api/v1/me/feedback/', accessToken, { category, message, page_url: '/mobile/today/' }, 'POST');
}

export type Sm2Quality = 'again' | 'hard' | 'good' | 'easy';
export type Sm2Review = { id: string; word: string; translation: string; context: string; source_text_id: string; next_review_date: string | null; due: boolean };
export async function loadSm2Reviews(accessToken: string): Promise<{ as_of: string; due_count: number; reviews: Sm2Review[] }> {
  return apiRequest('/api/v1/me/sm2/', accessToken);
}
export function gradeSm2Review(wordId: string, quality: Sm2Quality, accessToken: string) {
  return apiRequest<{ word_id: string; quality: Sm2Quality; next_review_date: string }>(`/api/v1/me/sm2/${encodeURIComponent(wordId)}/review/`, accessToken, { quality }, 'POST');
}

export type ReadingSummary = { id: string; title: string; description: string; level: string; minutes: number; emoji: string; saved: boolean };
export type GlossaryEntry = { surface: string; lemma: string; translation: string; part_of_speech: string };
export type ReadingDetail = ReadingSummary & { paragraphs: string[]; glossary: GlossaryEntry[]; comprehension_lesson_id: string | null; comprehension_api_path: string | null };
export async function loadReadingLibrary(level: string, accessToken: string): Promise<ReadingSummary[]> {
  const result = await apiRequest<{ texts: ReadingSummary[] }>(`/api/v1/reading/?level=${encodeURIComponent(level)}`, accessToken);
  return result.texts;
}
export async function loadReadingDetail(textId: string, accessToken: string): Promise<ReadingDetail> {
  const result = await apiRequest<{ text: ReadingDetail }>(`/api/v1/reading/${encodeURIComponent(textId)}/`, accessToken);
  return result.text;
}
export function setReadingBookmark(textId: string, saved: boolean, accessToken: string) {
  return apiRequest<{ reading_text_id: string; saved: boolean }>(`/api/v1/me/reading-bookmarks/${encodeURIComponent(textId)}/`, accessToken, undefined, saved ? 'PUT' : 'DELETE');
}
export function addReadingWord(textId: string, surface: string, accessToken: string) {
  return apiRequest<{ text_id: string; surface: string; word: string; translation: string; part_of_speech: string }>(`/api/v1/reading/${encodeURIComponent(textId)}/dictionary/`, accessToken, { surface }, 'POST');
}

export type ListeningQuestion = { id: string; prompt: string; options: string[] };
export type ListeningExercise = { id: string; title: string; level: string; delivery: 'device_tts' | 'audio_files'; transcript: string; fragments: { id: string; transcript: string; audio_path?: string }[]; questions: ListeningQuestion[] };
export type ListeningAnswer = { question_id: string; correct: boolean; correct_index: number; explanation: string };
export async function loadListening(accessToken: string): Promise<ListeningExercise[]> {
  const result = await apiRequest<{ exercises: ListeningExercise[] }>('/api/v1/listening/', accessToken);
  return result.exercises;
}
export function checkListeningAnswer(exerciseId: string, questionId: string, selectedIndex: number, accessToken: string) {
  return apiRequest<ListeningAnswer>(`/api/v1/listening/${encodeURIComponent(exerciseId)}/answer/`, accessToken, { question_id: questionId, selected_index: selectedIndex }, 'POST');
}

export function checkAnswer(lessonId: string, position: number, answer: { selected_index: number } | { token_order: number[] }, accessToken: string): Promise<AnswerResult> {
  return apiRequest(`/api/v1/lessons/${encodeURIComponent(lessonId)}/answer/`, accessToken, { position, ...answer }, 'POST');
}

export function saveLessonResult(lessonId: string, cardsTotal: number, cardsKnown: number, eventId: string, accessToken: string) {
  const completedAt = new Date().toISOString();
  return apiRequest('/api/v1/me/lesson-results/', accessToken, {
    event_id: eventId, lesson_id: lessonId, plan_date: completedAt.slice(0, 10), completed_at: completedAt,
    cards_total: cardsTotal, cards_known: cardsKnown, contract_version: '1.0', client_instance_id: 'polskiflow-mobile-v1',
  }, 'POST');
}

async function apiRequest<T>(path: string, accessToken: string, body?: object, method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE' = 'GET'): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 12_000);
  try {
    const response = await fetch(`${config.apiBaseUrl}${path}`, {
      method,
      headers: { Accept: 'application/json', Authorization: `Bearer ${accessToken}`, ...(body ? { 'Content-Type': 'application/json' } : {}) },
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });
    if (!response.ok) throw new Error(response.status === 401 ? 'Сессия истекла. Войдите снова.' : 'Не удалось выполнить запрос.');
    const payload = (await response.json()) as { data: T };
    if (!payload || !('data' in payload)) throw new Error('Сервер вернул неполный ответ.');
    return payload.data;
  } finally { clearTimeout(timeout); }
}
