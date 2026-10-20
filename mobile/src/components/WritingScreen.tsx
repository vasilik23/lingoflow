import { useCallback, useEffect, useMemo, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import type { Session } from '@supabase/supabase-js';

import { checkWritingDraft, loadWritingPrompts, type WritingCheck, type WritingCheckResult, type WritingPrompt } from '../lib/writing-api';
import { RequestGate } from '../lib/request-gate';
import type { Colors } from '../theme';

export function WritingScreen({ session, colors, onClose }: { session: Session; colors: Colors; onClose: () => void }) {
  const [prompts, setPrompts] = useState<WritingPrompt[]>([]);
  const [selectedId, setSelectedId] = useState('');
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [result, setResult] = useState<WritingCheckResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState('');
  const [requests] = useState(() => new RequestGate());
  const selected = prompts.find((prompt) => prompt.id === selectedId) ?? prompts[0];
  const draft = selected ? drafts[selected.id] ?? '' : '';
  const wordCount = useMemo(() => draft.trim().match(/\S+/gu)?.length ?? 0, [draft]);

  const load = useCallback(async () => {
    requests.invalidate(); setChecking(false); setLoading(true); setError('');
    try {
      const catalog = await loadWritingPrompts(session.access_token);
      setPrompts(catalog.prompts);
      setSelectedId((current) => current || catalog.prompts[0]?.id || '');
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Не удалось загрузить задания.');
    } finally { setLoading(false); }
  }, [session.access_token, requests]);
  useEffect(() => { void load(); return () => requests.invalidate(); }, [load, requests]);

  function choosePrompt(promptId: string) { requests.invalidate(); setChecking(false); setSelectedId(promptId); setResult(null); setError(''); }
  function changeDraft(text: string) {
    if (!selected) return;
    requests.invalidate(); setChecking(false); setError('');
    setDrafts((current) => ({ ...current, [selected.id]: text }));
    setResult(null);
  }
  async function check() {
    if (!selected || !draft.trim()) return;
    const ticket = requests.begin();
    if (ticket === null) return;
    setChecking(true); setError(''); setResult(null);
    try { const checked = await checkWritingDraft(selected.id, draft, session.access_token); if (requests.isCurrent(ticket)) setResult(checked); }
    catch (checkError) { if (requests.isCurrent(ticket)) setError(checkError instanceof Error ? checkError.message : 'Не удалось проверить структуру.'); }
    finally { if (requests.finish(ticket)) setChecking(false); }
  }

  return <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={styles.page}>
    <Pressable accessibilityRole="button" onPress={onClose}><Text style={[styles.back, { color: colors.primary }]}>‹ Сегодня</Text></Pressable>
    <Text style={[styles.title, { color: colors.text }]}>Письмо</Text>
    <Text style={[styles.copy, { color: colors.muted }]}>Черновик хранится только в памяти приложения. Он не сохраняется и не отправляется, пока вы явно не нажмёте «Проверить структуру».</Text>

    {loading ? <ActivityIndicator accessibilityLabel="Загрузка заданий" color={colors.primary} /> : <>
      <Text style={[styles.section, { color: colors.text }]}>Выберите задание</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.selector} accessibilityRole="radiogroup">
        {prompts.map((prompt) => <Pressable key={prompt.id} accessibilityRole="radio" accessibilityLabel={`${prompt.level}. ${prompt.title}`} accessibilityState={{ checked: selected?.id === prompt.id }} onPress={() => choosePrompt(prompt.id)} style={[styles.chip, { borderColor: selected?.id === prompt.id ? colors.primary : colors.border, backgroundColor: selected?.id === prompt.id ? colors.selected : colors.surface }]}><Text style={{ color: selected?.id === prompt.id ? colors.primary : colors.text, fontWeight: '800' }}>{prompt.level} · {prompt.title}</Text></Pressable>)}
      </ScrollView>

      {selected && <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
        <Text style={[styles.level, { color: colors.primary }]}>{selected.level}</Text>
        <Text style={[styles.promptTitle, { color: colors.text }]}>{selected.title}</Text>
        <Text style={[styles.copy, { color: colors.text }]}>{selected.task}</Text>
        <Text style={[styles.hint, { color: colors.muted, borderColor: colors.primary }]}>{selected.hint}</Text>
        <Text style={[styles.criteriaTitle, { color: colors.text }]}>Критерии для самопроверки</Text>
        {selected.checklist.map((item) => <Text key={item} style={[styles.criterion, { color: colors.text }]}>• {item}</Text>)}
        <Text style={[styles.structure, { color: colors.muted }]}>Автопроверка увидит только объём (от {selected.minimum_words} слов), абзацы (от {selected.minimum_paragraphs}) и маркеры: {selected.required_markers.join(', ')}.</Text>
      </View>}

      {selected && <>
        <TextInput accessibilityLabel={`Черновик: ${selected.title}`} multiline textAlignVertical="top" maxLength={16000} value={draft} onChangeText={changeDraft} placeholder="Напишите текст по-польски…" placeholderTextColor={colors.muted} style={[styles.input, { color: colors.text, backgroundColor: colors.surface, borderColor: colors.border }]} />
        <View style={styles.meta}><Text style={{ color: colors.muted }}>{wordCount} слов</Text><Text style={{ color: colors.muted }}>Только в памяти · не сохранено</Text></View>
        <Pressable accessibilityRole="button" accessibilityHint="Отправляет текст на сервер только для проверки наблюдаемой структуры" disabled={!draft.trim() || checking} onPress={check} style={({ pressed }) => [styles.action, { backgroundColor: colors.primary, opacity: !draft.trim() || checking ? .45 : pressed ? .7 : 1 }]}><Text style={[styles.actionText, { color: colors.onPrimary }]}>{checking ? 'Проверяем…' : 'Проверить структуру'}</Text></Pressable>
      </>}
      {!selected && !error && <Text style={{ color: colors.muted }}>Задания пока недоступны.</Text>}
    </>}

    {!!error && <View accessibilityRole="alert" style={styles.error}><Text style={{ color: colors.danger }}>{error}</Text>{!prompts.length && <Pressable accessibilityRole="button" onPress={() => void load()}><Text style={{ color: colors.primary, fontWeight: '800' }}>Повторить загрузку</Text></Pressable>}</View>}
    {result && <Result result={result} colors={colors} />}
  </ScrollView>;
}

function Result({ result, colors }: { result: WritingCheckResult; colors: Colors }) {
  return <View accessibilityRole="summary" style={[styles.result, { backgroundColor: colors.surface, borderColor: colors.border }]}>
    <Text style={[styles.section, { color: colors.text }]}>Результат структурной проверки</Text>
    <Text style={{ color: result.all_observable_checks_passed ? colors.success : colors.text, fontWeight: '900' }}>{result.all_observable_checks_passed ? 'Все наблюдаемые условия выполнены' : 'Некоторые условия пока не выполнены'}</Text>
    {result.checks.map((check) => <Text key={check.id} style={{ color: check.passed ? colors.success : colors.text }}>{check.passed ? '✓' : '○'} {checkLabel(check)}</Text>)}
    <Text style={[styles.limitations, { color: colors.muted, borderColor: colors.border }]}>{result.limitations}</Text>
    <Text style={{ color: colors.muted, fontSize: 12 }}>Текст не сохранён. Это не автоматическая оценка качества и не определение уровня CEFR.</Text>
  </View>;
}

function checkLabel(check: WritingCheck): string {
  if (check.id === 'minimum_words') return `Объём: ${check.observed} из ${check.required} слов`;
  if (check.id === 'minimum_paragraphs') return `Абзацы: ${check.observed} из ${check.required}`;
  const missing = check.required.filter((marker) => !check.found.includes(marker));
  return missing.length ? `Не найдены маркеры: ${missing.join(', ')}` : 'Все заданные маркеры найдены';
}

const styles = StyleSheet.create({
  page: { padding: 20, paddingBottom: 48, gap: 14 }, back: { fontSize: 15, fontWeight: '800', paddingVertical: 8 }, title: { fontSize: 30, lineHeight: 38, fontWeight: '900' }, copy: { fontSize: 15, lineHeight: 22 }, section: { fontSize: 20, fontWeight: '900', marginTop: 4 }, selector: { gap: 8, paddingVertical: 2 }, chip: { minHeight: 48, maxWidth: 260, borderWidth: 1, borderRadius: 999, paddingHorizontal: 16, justifyContent: 'center' }, card: { borderWidth: 1, borderRadius: 18, padding: 17, gap: 9 }, level: { fontSize: 12, fontWeight: '900', letterSpacing: .5 }, promptTitle: { fontSize: 21, lineHeight: 27, fontWeight: '900' }, hint: { borderLeftWidth: 3, paddingLeft: 12, lineHeight: 21 }, criteriaTitle: { fontSize: 16, fontWeight: '900', marginTop: 4 }, criterion: { lineHeight: 21 }, structure: { fontSize: 12, lineHeight: 18, marginTop: 3 }, input: { minHeight: 240, borderWidth: 1, borderRadius: 16, padding: 15, fontSize: 17, lineHeight: 26 }, meta: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between', gap: 8 }, action: { minHeight: 52, borderRadius: 14, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 18 }, actionText: { fontWeight: '900' }, error: { gap: 10 }, result: { borderWidth: 1, borderRadius: 18, padding: 17, gap: 10 }, limitations: { borderTopWidth: 1, paddingTop: 10, lineHeight: 20 },
});
