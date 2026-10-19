import { randomUUID } from 'expo-crypto';
import { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import type { Session } from '@supabase/supabase-js';

import { checkAnswer, deleteLessonDraft, loadLesson, saveLessonDraft, saveLessonResult, type AnswerResult, type NativeLesson } from '../lib/api';
import type { Colors } from '../theme';

export function LessonScreen({ lessonId, stepIndex, score, session, colors, onClose }: { lessonId: string; stepIndex: number; score: number; session: Session; colors: Colors; onClose: () => void }) {
  const [lesson, setLesson] = useState<NativeLesson | null>(null);
  const [position, setPosition] = useState(stepIndex);
  const [known, setKnown] = useState(score);
  const [selected, setSelected] = useState<number | null>(null);
  const [tokenOrder, setTokenOrder] = useState<number[]>([]);
  const [feedback, setFeedback] = useState<AnswerResult | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(true);
  const [saved, setSaved] = useState(false);
  const [finalKnown, setFinalKnown] = useState(0);

  const open = useCallback(async () => {
    setBusy(true); setError('');
    try {
      const loaded = await loadLesson(lessonId, session.access_token);
      if (stepIndex < 0 || stepIndex >= loaded.steps.length || score < 0 || score > stepIndex) throw new Error('Черновик урока устарел. Откройте урок заново.');
      setLesson(loaded);
    }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Не удалось открыть урок.'); }
    finally { setBusy(false); }
  }, [lessonId, session.access_token]);
  useEffect(() => { void open(); }, [open]);

  if (busy && !lesson) return <View style={styles.center}><ActivityIndicator size="large" color={colors.primary} /><Text style={{ color: colors.muted }}>Открываем урок…</Text></View>;
  if (!lesson) return <View style={styles.center}><Text accessibilityRole="alert" style={{ color: colors.danger }}>{error}</Text><Pressable onPress={open}><Text style={{ color: colors.primary, fontWeight: '800' }}>Повторить</Text></Pressable><Pressable onPress={onClose}><Text style={{ color: colors.primary }}>Назад</Text></Pressable></View>;

  const step = lesson.steps[position];
  const stepCount = lesson.steps.length;
  async function submitAnswer() {
    if (!step) return;
    const answer = step.type === 'sentence_builder' ? { token_order: tokenOrder } : { selected_index: selected as number };
    setBusy(true); setError('');
    try {
      const result = await checkAnswer(lessonId, step.position, answer, session.access_token);
      setFeedback(result); if (result.correct) setKnown((value) => value + 1);
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Ответ не отправлен.'); }
    finally { setBusy(false); }
  }
  async function advance(cardKnown?: boolean) {
    const nextKnown = known + (cardKnown ? 1 : 0);
    if (cardKnown) setKnown(nextKnown);
    if (position + 1 < stepCount) {
      setBusy(true); setError('');
      try {
        await saveLessonDraft(lessonId, position + 1, nextKnown, session.access_token);
        setPosition(position + 1); setSelected(null); setTokenOrder([]); setFeedback(null);
      } catch (reason) { setError(reason instanceof Error ? reason.message : 'Не удалось сохранить позицию урока.'); }
      finally { setBusy(false); }
      return;
    }
    setBusy(true); setError('');
    try {
      await saveLessonResult(lessonId, stepCount, nextKnown, randomUUID(), session.access_token);
      try { await deleteLessonDraft(lessonId, session.access_token); } catch { /* completion hides stale drafts; cleanup can retry later */ }
      setFinalKnown(nextKnown); setSaved(true);
    }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Результат не сохранён.'); }
    finally { setBusy(false); }
  }

  if (saved) return <View style={styles.center}><Text style={styles.doneEmoji}>🎉</Text><Text style={[styles.heading, { color: colors.text }]}>Урок завершён</Text><Text style={{ color: colors.muted }}>{finalKnown} из {lesson.steps.length} правильных ответов</Text><Action title="Вернуться к плану" colors={colors} onPress={onClose} /></View>;

  const answerReady = step.type === 'sentence_builder' ? tokenOrder.length === (step.tokens?.length || 0) : selected !== null;
  return <ScrollView contentContainerStyle={styles.page}>
    <View style={styles.top}><Pressable accessibilityRole="button" onPress={onClose}><Text style={[styles.back, { color: colors.primary }]}>‹ Сегодня</Text></Pressable><Text style={{ color: colors.muted }}>{position + 1} / {lesson.steps.length}</Text></View>
    <View style={[styles.progress, { backgroundColor: colors.border }]}><View style={[styles.progressFill, { backgroundColor: colors.primary, width: `${((position + 1) / lesson.steps.length) * 100}%` }]} /></View>
    <Text style={[styles.heading, { color: colors.text }]}>{lesson.lesson.title}</Text>
    <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
      {step.type === 'flashcard' ? <><Text style={[styles.word, { color: colors.text }]}>{step.polish}</Text><Text style={[styles.translation, { color: colors.primary }]}>{step.translation}</Text><Text style={[styles.example, { color: colors.muted }]}>{step.example}</Text><View style={styles.row}><Action title="Ещё учу" colors={colors} secondary onPress={() => advance(false)} /><Action title="Знаю" colors={colors} onPress={() => advance(true)} /></View></>
      : <><Text style={[styles.prompt, { color: colors.text }]}>{step.prompt}</Text>
        {step.type === 'choice' ? step.options?.map((option, index) => <Pressable key={option} disabled={!!feedback} onPress={() => setSelected(index)} style={[styles.option, { borderColor: selected === index ? colors.primary : colors.border, backgroundColor: selected === index ? colors.selected : colors.surface }]}><Text style={{ color: colors.text }}>{option}</Text></Pressable>)
        : <><View style={styles.tokens}>{step.tokens?.map((token, index) => <Pressable key={`${token}-${index}`} disabled={tokenOrder.includes(index) || !!feedback} onPress={() => setTokenOrder([...tokenOrder, index])} style={[styles.token, { borderColor: colors.border, opacity: tokenOrder.includes(index) ? .35 : 1 }]}><Text style={{ color: colors.text }}>{token}</Text></Pressable>)}</View><Text style={[styles.assembled, { color: colors.text }]}>{tokenOrder.map((index) => step.tokens?.[index]).join(' ') || 'Соберите предложение'}</Text>{!feedback && tokenOrder.length > 0 && <Pressable onPress={() => setTokenOrder([])}><Text style={{ color: colors.primary }}>Сбросить</Text></Pressable>}</>}
        {feedback ? <View accessibilityRole="alert" style={[styles.feedback, { borderColor: feedback.correct ? colors.success : colors.danger }]}><Text style={{ color: feedback.correct ? colors.success : colors.danger, fontWeight: '800' }}>{feedback.correct ? 'Верно' : 'Нужно поправить'}</Text><Text style={{ color: colors.text }}>{feedback.correct_sentence || feedback.explanation}</Text>{feedback.correct_sentence && <Text style={{ color: colors.muted }}>{feedback.explanation}</Text>}<Action title={position + 1 === lesson.steps.length ? 'Завершить' : 'Дальше'} colors={colors} onPress={() => advance(false)} /></View>
        : <Action title="Проверить" colors={colors} disabled={!answerReady || busy} onPress={submitAnswer} />}</>}
    </View>
    {!!error && <Text accessibilityRole="alert" style={{ color: colors.danger }}>{error}</Text>}
  </ScrollView>;
}

function Action({ title, colors, onPress, secondary = false, disabled = false }: { title: string; colors: Colors; onPress: () => void; secondary?: boolean; disabled?: boolean }) {
  return <Pressable accessibilityRole="button" disabled={disabled} onPress={onPress} style={({ pressed }) => [styles.action, { backgroundColor: secondary ? 'transparent' : colors.primary, borderColor: colors.primary, opacity: pressed || disabled ? .55 : 1 }]}><Text style={{ color: secondary ? colors.primary : colors.onPrimary, fontWeight: '800' }}>{title}</Text></Pressable>;
}

const styles = StyleSheet.create({
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24, gap: 14 }, page: { padding: 20, paddingBottom: 40, gap: 16 }, top: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }, back: { fontSize: 16, fontWeight: '800', paddingVertical: 8 }, progress: { height: 6, borderRadius: 8 }, progressFill: { height: 6, borderRadius: 8 }, heading: { fontSize: 28, fontWeight: '900' },
  card: { borderWidth: 1, borderRadius: 22, padding: 20, gap: 14 }, word: { fontSize: 36, fontWeight: '900', textAlign: 'center' }, translation: { fontSize: 21, fontWeight: '800', textAlign: 'center' }, example: { fontSize: 16, lineHeight: 24, textAlign: 'center' }, prompt: { fontSize: 21, lineHeight: 29, fontWeight: '800' }, option: { borderWidth: 2, borderRadius: 14, minHeight: 50, padding: 14, justifyContent: 'center' }, row: { flexDirection: 'row', gap: 10, marginTop: 8 }, action: { flex: 1, minHeight: 48, paddingHorizontal: 18, borderWidth: 1, borderRadius: 14, alignItems: 'center', justifyContent: 'center' }, feedback: { borderWidth: 1, borderRadius: 14, padding: 14, gap: 8 }, tokens: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 }, token: { borderWidth: 1, borderRadius: 10, padding: 10 }, assembled: { minHeight: 48, fontSize: 17, lineHeight: 24, fontWeight: '700' }, doneEmoji: { fontSize: 52 },
});
