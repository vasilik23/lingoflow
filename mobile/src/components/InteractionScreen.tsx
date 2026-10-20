import { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import type { Session } from '@supabase/supabase-js';
import { checkInteraction, loadInteraction, type InteractionAnswer, type InteractionScenario } from '../lib/interaction-api';
import { RequestGate } from '../lib/request-gate';
import type { Colors } from '../theme';

export function InteractionScreen({ session, colors, onClose }: { session: Session; colors: Colors; onClose: () => void }) {
  const [items, setItems] = useState<InteractionScenario[]>([]); const [selectedId, setSelectedId] = useState('');
  const [choice, setChoice] = useState(''); const [order, setOrder] = useState<string[]>([]); const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [checked, setChecked] = useState<Record<string, boolean>>({}); const [result, setResult] = useState<InteractionAnswer | null>(null);
  const [loading, setLoading] = useState(true); const [busy, setBusy] = useState(false); const [error, setError] = useState('');
  const [requests] = useState(() => new RequestGate());
  const selected = items.find((item) => item.id === selectedId) ?? items[0];
  const load = useCallback(async () => { requests.invalidate(); setBusy(false); setLoading(true); setError(''); try { const next = await loadInteraction(session.access_token); setItems(next); setSelectedId((value) => value || next[0]?.id || ''); } catch (reason) { setError(reason instanceof Error ? reason.message : 'Не удалось загрузить задания.'); } finally { setLoading(false); } }, [session.access_token, requests]);
  useEffect(() => { void load(); return () => requests.invalidate(); }, [load, requests]);
  function select(id: string) { invalidateAnswer(); setSelectedId(id); setChoice(''); setOrder([]); setResult(null); setError(''); }
  function invalidateAnswer() { requests.invalidate(); setBusy(false); setResult(null); setError(''); }
  async function submit() {
    if (!selected || selected.kind === 'free_production') return;
    const ticket = requests.begin(); if (ticket === null) return;
    setBusy(true); setError(''); setResult(null);
    try {
      const checked = await checkInteraction(selected.id, selected.kind === 'choice' ? { option_id: choice } : { block_ids: order }, session.access_token);
      if (requests.isCurrent(ticket)) setResult(checked);
    } catch (reason) { if (requests.isCurrent(ticket)) setError(reason instanceof Error ? reason.message : 'Не удалось проверить ответ.'); }
    finally { if (requests.finish(ticket)) setBusy(false); }
  }

  return <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={styles.page}>
    <Pressable accessibilityRole="button" onPress={onClose}><Text style={[styles.back, { color: colors.primary }]}>‹ Сегодня</Text></Pressable>
    <Text accessibilityRole="header" style={[styles.title, { color: colors.text }]}>Общение и медиация</Text>
    <Text style={[styles.copy, { color: colors.muted }]}>Тренируйте выбор реплики, порядок аргументов и самостоятельный ответ в ситуациях B1–B2.</Text>
    {loading ? <ActivityIndicator color={colors.primary} /> : <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.tabs} accessibilityRole="radiogroup">{items.map((item) => <Pressable key={item.id} accessibilityRole="radio" accessibilityState={{ checked: selected?.id === item.id }} onPress={() => select(item.id)} style={[styles.tab, { borderColor: selected?.id === item.id ? colors.primary : colors.border, backgroundColor: selected?.id === item.id ? colors.selected : colors.surface }]}><Text style={{ color: selected?.id === item.id ? colors.primary : colors.text, fontWeight: '800' }}>{item.level} · {item.title}</Text></Pressable>)}</ScrollView>}
    {selected && <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
      <Text style={[styles.eyebrow, { color: colors.primary }]}>{selected.level} · {selected.mode}</Text><Text style={[styles.cardTitle, { color: colors.text }]}>{selected.title}</Text><Text style={[styles.copy, { color: colors.muted }]}>{selected.situation}</Text>
      {selected.kind === 'choice' && <><Text style={[styles.prompt, { color: colors.text }]}>{selected.prompt}</Text>{selected.options.map((option) => <Pressable key={option.id} accessibilityRole="radio" accessibilityState={{ checked: choice === option.id }} onPress={() => { invalidateAnswer(); setChoice(option.id); }} style={[styles.option, { borderColor: choice === option.id ? colors.primary : colors.border, backgroundColor: choice === option.id ? colors.selected : colors.surface }]}><Text style={{ color: colors.text, flex: 1 }}>{option.text}</Text></Pressable>)}</>}
      {selected.kind === 'sequence' && <><Text style={[styles.prompt, { color: colors.text }]}>{selected.prompt}</Text><Text style={[styles.copy, { color: colors.muted }]}>Нажимайте блоки в нужном порядке.</Text>{selected.blocks.filter((block) => !order.includes(block.id)).map((block) => <Pressable key={block.id} onPress={() => { invalidateAnswer(); setOrder((current) => current.includes(block.id) ? current : [...current, block.id]); }} style={[styles.option, { borderColor: colors.border }]}><Text style={{ color: colors.text }}>{block.text}</Text></Pressable>)}{!!order.length && <View style={styles.order}>{order.map((id, index) => <Text key={id} style={{ color: colors.text }}>{index + 1}. {selected.blocks.find((block) => block.id === id)?.text}</Text>)}</View>}<Pressable onPress={() => { invalidateAnswer(); setOrder([]); }}><Text style={{ color: colors.primary, fontWeight: '800' }}>Сбросить порядок</Text></Pressable></>}
      {selected.kind === 'free_production' && <><Text style={[styles.prompt, { color: colors.text }]}>{selected.task}</Text><TextInput accessibilityLabel={`Черновик: ${selected.title}`} multiline textAlignVertical="top" maxLength={4000} value={drafts[selected.id] ?? ''} onChangeText={(text) => setDrafts({ ...drafts, [selected.id]: text })} placeholder="Подготовьте ответ по-польски…" placeholderTextColor={colors.muted} style={[styles.input, { color: colors.text, borderColor: colors.border, backgroundColor: colors.background }]} /><Text style={[styles.notice, { color: colors.muted }]}>Черновик остаётся только в памяти устройства и не отправляется на сервер.</Text>{selected.checklist.map((item, index) => { const key = `${selected.id}:${index}`; return <Pressable key={key} accessibilityRole="checkbox" accessibilityState={{ checked: !!checked[key] }} onPress={() => setChecked({ ...checked, [key]: !checked[key] })} style={styles.check}><Text style={{ color: colors.primary, fontWeight: '900' }}>{checked[key] ? '✓' : '○'}</Text><Text style={{ color: colors.text, flex: 1 }}>{item}</Text></Pressable>; })}</>}
      {selected.kind !== 'free_production' && <Pressable accessibilityRole="button" disabled={busy || (selected.kind === 'choice' ? !choice : order.length !== selected.blocks.length)} onPress={submit} style={[styles.button, { backgroundColor: colors.primary, opacity: busy || (selected.kind === 'choice' ? !choice : order.length !== selected.blocks.length) ? .45 : 1 }]}>{busy ? <ActivityIndicator color={colors.onPrimary} /> : <Text style={[styles.buttonText, { color: colors.onPrimary }]}>Проверить ответ</Text>}</Pressable>}
    </View>}
    {!!error && <View style={[styles.alert, { borderColor: colors.danger }]}><Text accessibilityRole="alert" style={{ color: colors.danger }}>{error}</Text>{!items.length && <Pressable onPress={load}><Text style={{ color: colors.primary, fontWeight: '800' }}>Повторить</Text></Pressable>}</View>}
    {result && <View accessibilityRole="summary" style={[styles.feedback, { borderColor: result.correct ? colors.success : colors.danger, backgroundColor: colors.surface }]}><Text style={{ color: result.correct ? colors.success : colors.danger, fontWeight: '900', fontSize: 17 }}>{result.correct ? 'Верно' : 'Стоит попробовать ещё раз'}</Text><Text style={[styles.copy, { color: colors.text }]}>{result.explanation}</Text></View>}
    <Text style={[styles.notice, { color: colors.muted }]}>Ответы не сохраняются и не влияют на официальный уровень или сертификат.</Text>
  </ScrollView>;
}

const styles = StyleSheet.create({ page: { padding: 20, paddingBottom: 48, gap: 14 }, back: { fontSize: 16, fontWeight: '800', paddingVertical: 8 }, title: { fontSize: 30, fontWeight: '900' }, copy: { fontSize: 14, lineHeight: 21 }, tabs: { gap: 8 }, tab: { minHeight: 48, maxWidth: 260, justifyContent: 'center', borderWidth: 1, borderRadius: 999, paddingHorizontal: 15 }, card: { borderWidth: 1, borderRadius: 18, padding: 16, gap: 12 }, eyebrow: { fontSize: 12, fontWeight: '900' }, cardTitle: { fontSize: 21, fontWeight: '900' }, prompt: { fontSize: 16, lineHeight: 23, fontWeight: '800' }, option: { minHeight: 50, borderWidth: 1, borderRadius: 13, padding: 13, justifyContent: 'center' }, order: { gap: 8, padding: 12 }, input: { minHeight: 180, borderWidth: 1, borderRadius: 14, padding: 14, fontSize: 16, lineHeight: 23 }, check: { flexDirection: 'row', gap: 10, alignItems: 'flex-start', paddingVertical: 5 }, button: { minHeight: 52, borderRadius: 14, alignItems: 'center', justifyContent: 'center' }, buttonText: { fontWeight: '900' }, alert: { borderWidth: 1, borderRadius: 14, padding: 14, gap: 8 }, feedback: { borderWidth: 1, borderLeftWidth: 4, borderRadius: 14, padding: 15, gap: 7 }, notice: { fontSize: 12, lineHeight: 18 } });
