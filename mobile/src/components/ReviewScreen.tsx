import { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';
import type { Session } from '@supabase/supabase-js';

import { gradeSm2Review, loadSm2Reviews, type Sm2Quality, type Sm2Review } from '../lib/api';
import type { Colors } from '../theme';

const grades: { id: Sm2Quality; label: string; hint: string }[] = [
  { id: 'again', label: 'Снова', hint: 'не вспомнил' }, { id: 'hard', label: 'Трудно', hint: 'с подсказкой' },
  { id: 'good', label: 'Хорошо', hint: 'вспомнил' }, { id: 'easy', label: 'Легко', hint: 'сразу' },
];

export function ReviewScreen({ session, colors, onClose }: { session: Session; colors: Colors; onClose: () => void }) {
  const [queue, setQueue] = useState<Sm2Review[]>([]); const [initialCount, setInitialCount] = useState(0);
  const [revealed, setRevealed] = useState(false); const [loading, setLoading] = useState(true); const [error, setError] = useState('');
  const load = useCallback(async () => {
    setLoading(true); setError('');
    try { const data = await loadSm2Reviews(session.access_token); const due = data.reviews.filter((item) => item.due); setQueue(due); setInitialCount(due.length); }
    catch { setError('Не удалось загрузить слова для повторения.'); }
    finally { setLoading(false); }
  }, [session.access_token]);
  useEffect(() => { void load(); }, [load]);

  async function grade(quality: Sm2Quality) {
    const current = queue[0]; if (!current || !revealed) return;
    setLoading(true); setError('');
    try { await gradeSm2Review(current.id, quality, session.access_token); setQueue((items) => items.slice(1)); setRevealed(false); }
    catch { setError('Оценка не сохранилась. Карточка останется в очереди.'); }
    finally { setLoading(false); }
  }

  const current = queue[0];
  if (loading && initialCount === 0 && !current) return <View style={styles.center}><ActivityIndicator size="large" color={colors.primary} /><Text style={{ color: colors.muted }}>Готовим повторение…</Text></View>;
  if (!current) return <View style={styles.center}><Text style={styles.emoji}>✅</Text><Text style={[styles.title, { color: colors.text }]}>{initialCount ? 'Повторение завершено' : 'На сегодня всё'}</Text><Text style={[styles.copy, { color: colors.muted }]}>{initialCount ? `Повторено слов: ${initialCount}` : 'Новых карточек по расписанию SM‑2 пока нет.'}</Text>{!!error && <Text accessibilityRole="alert" style={{ color: colors.danger }}>{error}</Text>}<Action title="Вернуться в Сегодня" colors={colors} onPress={onClose} /></View>;

  return <View style={styles.page}>
    <View style={styles.header}><Pressable accessibilityRole="button" onPress={onClose}><Text style={[styles.back, { color: colors.primary }]}>‹ Сегодня</Text></Pressable><Text style={{ color: colors.muted }}>{initialCount - queue.length + 1} / {initialCount}</Text></View>
    <Text style={[styles.eyebrow, { color: colors.primary }]}>SM‑2 ПОВТОРЕНИЕ</Text>
    <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
      <Text style={[styles.word, { color: colors.text }]}>{current.word}</Text>
      {current.context ? <Text style={[styles.context, { color: colors.muted }]}>{current.context}</Text> : null}
      {revealed ? <><View style={[styles.answer, { borderTopColor: colors.border }]}><Text style={[styles.translation, { color: colors.primary }]}>{current.translation}</Text></View><Text style={[styles.prompt, { color: colors.text }]}>Насколько легко вспомнилось?</Text><View style={styles.grades}>{grades.map((item) => <Pressable key={item.id} accessibilityRole="button" disabled={loading} onPress={() => grade(item.id)} style={({ pressed }) => [styles.grade, { borderColor: colors.border, opacity: pressed || loading ? .55 : 1 }]}><Text style={[styles.gradeLabel, { color: colors.text }]}>{item.label}</Text><Text style={{ color: colors.muted, fontSize: 11 }}>{item.hint}</Text></Pressable>)}</View></>
      : <Action title="Показать перевод" colors={colors} onPress={() => setRevealed(true)} />}
    </View>
    {!!error && <Text accessibilityRole="alert" style={{ color: colors.danger }}>{error}</Text>}
    <Text style={[styles.note, { color: colors.muted }]}>Оценка меняет дату следующего повторения. До показа ответа выбрать её нельзя.</Text>
  </View>;
}

function Action({ title, colors, onPress }: { title: string; colors: Colors; onPress: () => void }) {
  return <Pressable accessibilityRole="button" onPress={onPress} style={({ pressed }) => [styles.action, { backgroundColor: colors.primary, opacity: pressed ? .65 : 1 }]}><Text style={[styles.actionText, { color: colors.onPrimary }]}>{title}</Text></Pressable>;
}

const styles = StyleSheet.create({
  page: { flex: 1, padding: 20, gap: 16 }, center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 28, gap: 14 }, header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }, back: { fontSize: 16, fontWeight: '800', paddingVertical: 8 }, eyebrow: { fontSize: 12, fontWeight: '900', letterSpacing: 1 }, card: { borderWidth: 1, borderRadius: 24, padding: 22, gap: 18 }, word: { fontSize: 36, fontWeight: '900', textAlign: 'center' }, context: { fontSize: 16, lineHeight: 24, textAlign: 'center' }, answer: { borderTopWidth: 1, paddingTop: 18 }, translation: { fontSize: 24, fontWeight: '900', textAlign: 'center' }, prompt: { fontWeight: '800', textAlign: 'center' }, grades: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 }, grade: { width: '48%', minHeight: 62, borderWidth: 1, borderRadius: 13, alignItems: 'center', justifyContent: 'center' }, gradeLabel: { fontWeight: '800' }, action: { minHeight: 50, borderRadius: 14, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 18 }, actionText: { fontWeight: '900' }, note: { fontSize: 12, lineHeight: 18 }, title: { fontSize: 28, fontWeight: '900', textAlign: 'center' }, copy: { fontSize: 15, lineHeight: 22, textAlign: 'center' }, emoji: { fontSize: 50 },
});
