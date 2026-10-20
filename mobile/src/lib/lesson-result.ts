export type LessonResultPayload = Readonly<{
  event_id: string; lesson_id: string; plan_date: string; completed_at: string;
  cards_total: number; cards_known: number; contract_version: '1.0'; client_instance_id: string;
}>;

// Freeze the whole event: a retry with the same ID but a new timestamp conflicts.
export function createLessonResult(lessonId: string, total: number, known: number, eventId: string): LessonResultPayload {
  const completedAt = new Date().toISOString();
  return Object.freeze({
    event_id: eventId, lesson_id: lessonId, plan_date: completedAt.slice(0, 10), completed_at: completedAt,
    cards_total: total, cards_known: known, contract_version: '1.0', client_instance_id: 'polskiflow-mobile-v1',
  });
}
