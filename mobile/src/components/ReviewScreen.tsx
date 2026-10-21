import { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View, ScrollView } from 'react-native';
import type { Session } from '@supabase/supabase-js';

import { gradeSm2Review, loadSm2Reviews, type Sm2Quality, type Sm2Review } from '../lib/api';
import { RequestGate } from '../lib/request-gate';
import type { Colors } from '../theme';

const grades: { id: Sm2Quality; label: string; hint: string }[] = [
  { id: 'again', label: 'Снова', hint: 'не вспомнил' }, { id: 'hard', label: 'Трудно', hint: 'с подсказкой' },
  { id: 'good', label: 'Хорошо', hint: 'вспомнил' }, { id: 'easy', label: 'Легко', hint: 'сразу' },
];

export function ReviewScreen({ session, colors, onClose }: { session: Session; colors: Colors; onClose: () => void }) {
  const [queue, setQueue] = useState<Sm2Review[]>([]);
  const [confirmedCount, setConfirmedCount] = useState(0);
  const [revealed, setRevealed] = useState(false);
  const [ready, setReady] = useState(false);
  const [loading, setLoading] = useState(true);
  const [refreshRequired, setRefreshRequired] = useState(false);
  const [error, setError] = useState('');
  const [gate] = useState(() => new RequestGate());

  const close = () => { gate.invalidate(); onClose(); };
  const load = useCallback(async () => {
    const ticket = gate.begin();
    if (ticket === null) return;
    setLoading(true); setReady(false); setError(''); setRevealed(false);
    try {
      const data = await loadSm2Reviews(session.access_token);
      if (!gate.isCurrent(ticket)) return;
      setQueue(data.reviews.filter(item => item.due));
      setRefreshRequired(false); setReady(true);
    } catch {
      if (gate.isCurrent(ticket)) setError('Не удалось загрузить слова для повторения.');
    } finally {
      if (gate.finish(ticket)) setLoading(false);
    }
  }, [session.access_token, gate]);
  useEffect(() => {
    void load();
    return () => gate.invalidate();
  }, [load, gate]);

  async function grade(quality: Sm2Quality) {
    const current = queue[0];
    if (!current || !revealed || refreshRequired) return;
    const ticket = gate.begin();
    if (ticket === null) return;
    setLoading(true); setError('');
    try {
      await gradeSm2Review(current.id, quality, session.access_token, current.last_reviewed_at);
      if (!gate.isCurrent(ticket)) return;
      setQueue(items => items[0]?.id === current.id ? items.slice(1) : items);
      setConfirmedCount(count => count + 1); setRevealed(false);
    } catch {
      if (!gate.isCurrent(ticket)) return;
      setRefreshRequired(true);
      setError('Не удалось подтвердить оценку. Она могла сохраниться. Обнови очередь перед следующей оценкой.');
    } finally {
      if (gate.finish(ticket)) setLoading(false);
    }
  }

  const current = queue[0];
  if (!ready) return <View style={styles.center}>
    {loading ? <><ActivityIndicator size="large" color={colors.primary} /><Text style={{ color: colors.muted }}>Готовим повторение…</Text></>
      : <><Text style={[styles.title, { color: colors.text }]}>Повторение недоступно</Text><Text accessibilityRole="alert" style={{ color: colors.danger }}>{error}</Text><Action title="Повторить загрузку" colors={colors} onPress={() => void load()} /></>}
    <Action title="Вернуться в Сегодня" colors={colors} onPress={close} />
  </View>;
  if (!current) return <View style={styles.center}>
    <Text style={styles.emoji}>✅</Text>
    <Text style={[styles.title, { color: colors.text }]}>{confirmedCount ? 'Повторение завершено' : 'На сегодня всё'}</Text>
    <Text style={[styles.copy, { color: colors.muted }]}>{confirmedCount ? `Оценок подтверждено: ${confirmedCount}` : 'Карточек по расписанию SM‑2 сейчас нет.'}</Text>
    <Action title="Вернуться в Сегодня" colors={colors} onPress={close} />
  </View>;

  return <ScrollView contentContainerStyle={styles.page}>
    <View style={styles.header}><Pressable accessibilityRole="button" onPress={close}><Text style={[styles.back, { color: colors.primary }]}>‹ Сегодня</Text></Pressable><Text style={{ color: colors.muted }}>Осталось: {queue.length}</Text></View>
    <Text style={[styles.eyebrow, { color: colors.primary }]}>SM‑2 ПОВТОРЕНИЕ</Text>
    <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
      <Text style={[styles.word, { color: colors.text }]}>{current.word}</Text>
      {current.context ? <Text style={[styles.context, { color: colors.muted }]}>{current.context}</Text> : null}
      {revealed ? <><View style={[styles.answer, { borderTopColor: colors.border }]}><Text style={[styles.translation, { color: colors.primary }]}>{current.translation}</Text></View><Text style={[styles.prompt, { color: colors.text }]}>Насколько легко вспомнилось?</Text><View style={styles.grades}>{grades.map(item => <Pressable key={item.id} accessibilityRole="button" accessibilityState={{ disabled: loading || refreshRequired }} disabled={loading || refreshRequired} onPress={() => grade(item.id)} style={({ pressed }) => [styles.grade, { borderColor: colors.border, opacity: pressed || loading || refreshRequired ? .55 : 1 }]}><Text style={[styles.gradeLabel, { color: colors.text }]}>{item.label}</Text><Text style={{ color: colors.muted, fontSize: 11 }}>{item.hint}</Text></Pressable>)}</View></>
      : <Action title="Показать перевод" colors={colors} onPress={() => setRevealed(true)} />}
    </View>
    {!!error && <Text accessibilityRole="alert" style={{ color: colors.danger }}>{error}</Text>}
    {refreshRequired && <Action title="Обновить очередь" colors={colors} onPress={() => void load()} />}
    <Text style={[styles.note, { color: colors.muted }]}>Оценка меняет дату следующего повторения. До показа ответа выбрать её нельзя.</Text>
  </ScrollView>;
}

function Action({ title, colors, onPress }: { title: string; colors: Colors; onPress: () => void }) {
  return <Pressable accessibilityRole="button" onPress={onPress} style={({ pressed }) => [styles.action, { backgroundColor: colors.primary, opacity: pressed ? .65 : 1 }]}><Text style={[styles.actionText, { color: colors.onPrimary }]}>{title}</Text></Pressable>;
}

const styles = StyleSheet.create({
  page: { flexGrow: 1, padding: 20, gap: 16 }, center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 28, gap: 14 }, header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }, back: { fontSize: 16, fontWeight: '800', paddingVertical: 8 }, eyebrow: { fontSize: 12, fontWeight: '900', letterSpacing: 1 }, card: { borderWidth: 1, borderRadius: 24, padding: 22, gap: 18 }, word: { fontSize: 36, fontWeight: '900', textAlign: 'center' }, context: { fontSize: 16, lineHeight: 24, textAlign: 'center' }, answer: { borderTopWidth: 1, paddingTop: 18 }, translation: { fontSize: 24, fontWeight: '900', textAlign: 'center' }, prompt: { fontWeight: '800', textAlign: 'center' }, grades: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 }, grade: { width: '48%', minHeight: 62, borderWidth: 1, borderRadius: 13, alignItems: 'center', justifyContent: 'center' }, gradeLabel: { fontWeight: '800' }, action: { minHeight: 50, borderRadius: 14, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 18 }, actionText: { fontWeight: '900' }, note: { fontSize: 12, lineHeight: 18 }, title: { fontSize: 28, fontWeight: '900', textAlign: 'center' }, copy: { fontSize: 15, lineHeight: 22, textAlign: 'center' }, emoji: { fontSize: 50 },
});
