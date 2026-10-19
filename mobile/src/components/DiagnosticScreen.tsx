import { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import type { Session } from '@supabase/supabase-js';

import { evaluateDiagnostic, loadDiagnostic, type DiagnosticForm, type DiagnosticResult } from '../lib/diagnostic-api';
import type { Colors } from '../theme';

type Props = { session: Session; colors: Colors; onClose: () => void };

export function DiagnosticScreen({ session, colors, onClose }: Props) {
  const [form, setForm] = useState<DiagnosticForm | null>(null);
  const [selfRatings, setSelfRatings] = useState<Record<string, string>>({});
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [result, setResult] = useState<DiagnosticResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true); setError('');
    try { setForm(await loadDiagnostic(session.access_token)); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Не удалось загрузить диагностику.'); }
    finally { setLoading(false); }
  }, [session.access_token]);
  useEffect(() => { void load(); }, [load]);

  const submit = async () => {
    if (!form) return;
    const missingSelf = form.self_assessment.filter((item) => !selfRatings[item.id]).length;
    const missingTasks = form.checked_tasks.filter((item) => !answers[item.id]).length;
    if (missingSelf || missingTasks) {
      setError(`Заполните всё: самооценка ${form.self_assessment.length - missingSelf}/${form.self_assessment.length}, задания ${form.checked_tasks.length - missingTasks}/${form.checked_tasks.length}.`);
      return;
    }
    setSubmitting(true); setError('');
    try { setResult(await evaluateDiagnostic(session.access_token, selfRatings, answers)); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Не удалось получить результат.'); }
    finally { setSubmitting(false); }
  };

  if (!form && loading) return <View style={styles.center}><ActivityIndicator size="large" color={colors.primary} /><Text style={{ color: colors.muted }}>Загружаем диагностику…</Text></View>;
  if (!form) return <View style={styles.center}><Text accessibilityRole="alert" style={[styles.centerCopy, { color: colors.danger }]}>{error}</Text><Pressable accessibilityRole="button" onPress={load}><Text style={[styles.action, { color: colors.primary }]}>Повторить</Text></Pressable><Pressable accessibilityRole="button" onPress={onClose}><Text style={[styles.action, { color: colors.primary }]}>Вернуться на Сегодня</Text></Pressable></View>;

  if (result) return <ScrollView contentContainerStyle={styles.page}>
    <Pressable accessibilityRole="button" accessibilityLabel="Вернуться на экран Сегодня" onPress={onClose}><Text style={[styles.back, { color: colors.primary }]}>‹ Сегодня</Text></Pressable>
    <Text style={[styles.eyebrow, { color: colors.primary }]}>ПРЕДВАРИТЕЛЬНАЯ РЕКОМЕНДАЦИЯ</Text>
    <Text accessibilityRole="header" style={[styles.title, { color: colors.text }]}>Начните с {result.recommended_level}</Text>
    <Text style={[styles.copy, { color: colors.muted }]}>{result.disclaimer}</Text>
    <SignalCard title="Самооценка" level={result.self_assessment.level} detail={`Фокус: ${result.self_assessment.focus_modes.join(', ')}`} calculation={result.self_assessment.calculation} colors={colors} />
    <SignalCard title="Проверяемая проба" level={result.checked_sample.level} detail={`${result.checked_sample.correct} из ${result.checked_sample.total} правильных ответов`} calculation={result.checked_sample.calculation} colors={colors} />
    <Text accessibilityRole="header" style={[styles.sectionTitle, { color: colors.text }]}>Результаты по навыкам</Text>
    {result.checked_sample.mode_scores.map((score) => <View key={score.mode} accessible accessibilityLabel={`${score.mode}: ${score.correct} из ${score.total}`} style={[styles.compactCard, { backgroundColor: colors.surface, borderColor: colors.border }]}><Text style={[styles.optionText, { color: colors.text }]}>{score.mode}</Text><Text style={[styles.score, { color: colors.primary }]}>{score.correct}/{score.total}</Text></View>)}
    <Text accessibilityRole="header" style={[styles.sectionTitle, { color: colors.text }]}>Разбор заданий</Text>
    {result.checked_sample.feedback.map((item, index) => {
      const task = form.checked_tasks.find((candidate) => candidate.id === item.task_id);
      const correctText = task?.options.find((option) => option.id === item.correct_option_id)?.text;
      return <View key={item.task_id} accessible style={[styles.feedback, { backgroundColor: colors.surface, borderColor: item.correct ? colors.success : colors.danger }]}><Text style={[styles.optionText, { color: item.correct ? colors.success : colors.danger }]}>{index + 1}. {item.correct ? 'Верно' : 'Нужно повторить'}</Text>{!item.correct && correctText && <Text style={[styles.copy, { color: colors.text }]}>Правильный ответ: {correctText}</Text>}<Text style={[styles.copy, { color: colors.muted }]}>{item.explanation}</Text></View>;
    })}
    <Text style={[styles.disclaimer, { color: colors.muted }]}>Ответы и результат не сохранены в профиле. Диагностика не является экзаменом, сертификатом или подтверждением уровня CEFR.</Text>
    <Pressable accessibilityRole="button" onPress={() => { setResult(null); setSelfRatings({}); setAnswers({}); setError(''); }} style={[styles.primaryButton, { backgroundColor: colors.primary }]}><Text style={[styles.primaryText, { color: colors.onPrimary }]}>Пройти заново</Text></Pressable>
  </ScrollView>;

  return <ScrollView contentContainerStyle={styles.page} keyboardShouldPersistTaps="handled">
    <Pressable accessibilityRole="button" accessibilityLabel="Вернуться на экран Сегодня" onPress={onClose}><Text style={[styles.back, { color: colors.primary }]}>‹ Сегодня</Text></Pressable>
    <Text accessibilityRole="header" style={[styles.title, { color: colors.text }]}>Диагностика</Text>
    <Text style={[styles.copy, { color: colors.muted }]}>Сначала оцените четыре навыка, затем выполните восемь коротких заданий. Выбирайте один ответ в каждом блоке.</Text>
    <View style={[styles.notice, { borderColor: colors.border, backgroundColor: colors.surface }]}><Text style={[styles.disclaimer, { color: colors.muted }]}>{form.disclaimer} Ответы не сохраняются.</Text></View>
    <Text accessibilityRole="header" style={[styles.sectionTitle, { color: colors.text }]}>1. Самооценка</Text>
    {form.self_assessment.map((item) => <View key={item.id} accessible={false} style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}><Text accessibilityRole="header" style={[styles.cardTitle, { color: colors.text }]}>{item.title}</Text><Text style={[styles.copy, { color: colors.muted }]}>{item.description}</Text>{item.options.map((option) => <Choice key={option.value} label={option.label} selected={selfRatings[item.id] === option.value} onPress={() => setSelfRatings((current) => ({ ...current, [item.id]: option.value }))} colors={colors} />)}</View>)}
    <Text accessibilityRole="header" style={[styles.sectionTitle, { color: colors.text }]}>2. Короткая проба</Text>
    {form.checked_tasks.map((task, index) => <View key={task.id} accessible={false} style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}><Text style={[styles.eyebrow, { color: colors.primary }]}>{task.mode} · {index + 1}/{form.checked_tasks.length}</Text><Text accessibilityRole="header" style={[styles.prompt, { color: colors.text }]}>{task.prompt}</Text>{task.options.map((option) => <Choice key={option.id} label={option.text} selected={answers[task.id] === option.id} onPress={() => setAnswers((current) => ({ ...current, [task.id]: option.id }))} colors={colors} />)}</View>)}
    {!!error && <View style={[styles.notice, { borderColor: colors.danger }]}><Text accessibilityRole="alert" style={{ color: colors.danger }}>{error}</Text></View>}
    <Pressable accessibilityRole="button" accessibilityState={{ disabled: submitting }} disabled={submitting} onPress={submit} style={[styles.primaryButton, { backgroundColor: colors.primary, opacity: submitting ? .65 : 1 }]}>{submitting ? <ActivityIndicator color={colors.onPrimary} /> : <Text style={[styles.primaryText, { color: colors.onPrimary }]}>Получить рекомендацию</Text>}</Pressable>
    <Text style={[styles.disclaimer, { color: colors.muted }]}>Результат сопоставляет два отдельных сигнала и выбирает более осторожный уровень. Это не экзамен и не сертификат CEFR.</Text>
  </ScrollView>;
}

function Choice({ label, selected, onPress, colors }: { label: string; selected: boolean; onPress: () => void; colors: Colors }) {
  return <Pressable accessibilityRole="radio" accessibilityState={{ checked: selected }} accessibilityLabel={label} onPress={onPress} style={[styles.choice, { borderColor: selected ? colors.primary : colors.border, backgroundColor: selected ? colors.selected : colors.background }]}><View style={[styles.radio, { borderColor: selected ? colors.primary : colors.muted }]}>{selected && <View style={[styles.radioDot, { backgroundColor: colors.primary }]} />}</View><Text style={[styles.choiceText, { color: colors.text }]}>{label}</Text></Pressable>;
}

function SignalCard({ title, level, detail, calculation, colors }: { title: string; level: string; detail: string; calculation: string; colors: Colors }) {
  return <View accessible accessibilityLabel={`${title}: ${level}. ${detail}. ${calculation}`} style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}><Text style={[styles.eyebrow, { color: colors.primary }]}>{title}</Text><Text style={[styles.level, { color: colors.text }]}>{level}</Text><Text style={[styles.optionText, { color: colors.text }]}>{detail}</Text><Text style={[styles.copy, { color: colors.muted }]}>{calculation}</Text></View>;
}

const styles = StyleSheet.create({
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', gap: 14, padding: 24 }, centerCopy: { textAlign: 'center', lineHeight: 21 }, page: { padding: 20, paddingBottom: 48, gap: 14 }, back: { fontSize: 16, fontWeight: '800', paddingVertical: 8 }, title: { fontSize: 32, fontWeight: '900' }, sectionTitle: { fontSize: 21, fontWeight: '900', marginTop: 8 }, copy: { fontSize: 14, lineHeight: 21 }, disclaimer: { fontSize: 12, lineHeight: 18 }, eyebrow: { fontSize: 12, fontWeight: '900', letterSpacing: .7 }, card: { borderWidth: 1, borderRadius: 18, padding: 16, gap: 10 }, cardTitle: { fontSize: 19, fontWeight: '900' }, prompt: { fontSize: 16, lineHeight: 23, fontWeight: '800' }, choice: { minHeight: 52, flexDirection: 'row', alignItems: 'center', borderWidth: 1, borderRadius: 13, padding: 12, gap: 10 }, choiceText: { flex: 1, fontSize: 14, lineHeight: 20 }, radio: { width: 22, height: 22, borderWidth: 2, borderRadius: 11, alignItems: 'center', justifyContent: 'center' }, radioDot: { width: 10, height: 10, borderRadius: 5 }, notice: { borderWidth: 1, borderRadius: 14, padding: 14 }, primaryButton: { minHeight: 52, borderRadius: 14, padding: 14, alignItems: 'center', justifyContent: 'center' }, primaryText: { fontWeight: '900', fontSize: 16 }, action: { fontWeight: '900', padding: 8 }, level: { fontSize: 34, fontWeight: '900' }, optionText: { fontSize: 15, lineHeight: 21, fontWeight: '700' }, compactCard: { flexDirection: 'row', justifyContent: 'space-between', borderWidth: 1, borderRadius: 14, padding: 14 }, score: { fontSize: 16, fontWeight: '900' }, feedback: { borderWidth: 1, borderLeftWidth: 4, borderRadius: 14, padding: 14, gap: 5 },
});
