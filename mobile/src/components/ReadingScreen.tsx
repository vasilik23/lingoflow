import { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import type { Session } from '@supabase/supabase-js';

import { addReadingWord, loadReadingDetail, loadReadingLibrary, setReadingBookmark, type ReadingDetail, type ReadingSummary } from '../lib/api';
import type { Colors } from '../theme';

const levels = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'];

export function ReadingScreen({ session, colors, onClose, onOpenLesson }: { session: Session; colors: Colors; onClose: () => void; onOpenLesson: (lessonId: string) => void }) {
  const [level, setLevel] = useState('A1'); const [items, setItems] = useState<ReadingSummary[]>([]);
  const [detail, setDetail] = useState<ReadingDetail | null>(null); const [savedWords, setSavedWords] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true); const [error, setError] = useState('');
  const loadLibrary = useCallback(async () => { setLoading(true); setError(''); try { setItems(await loadReadingLibrary(level, session.access_token)); } catch { setError('Не удалось загрузить библиотеку.'); } finally { setLoading(false); } }, [level, session.access_token]);
  useEffect(() => { void loadLibrary(); }, [loadLibrary]);

  async function openText(textId: string) { setLoading(true); setError(''); try { setDetail(await loadReadingDetail(textId, session.access_token)); setSavedWords(new Set()); } catch { setError('Не удалось открыть текст.'); } finally { setLoading(false); } }
  async function toggleBookmark() { if (!detail) return; setLoading(true); setError(''); try { const next = !detail.saved; await setReadingBookmark(detail.id, next, session.access_token); setDetail({ ...detail, saved: next }); setItems((rows) => rows.map((row) => row.id === detail.id ? { ...row, saved: next } : row)); } catch { setError('Закладка не сохранилась.'); } finally { setLoading(false); } }
  async function saveWord(surface: string) { if (!detail || savedWords.has(surface)) return; setLoading(true); setError(''); try { await addReadingWord(detail.id, surface, session.access_token); setSavedWords((words) => new Set(words).add(surface)); } catch { setError('Слово не добавилось в словарь.'); } finally { setLoading(false); } }

  if (detail) return <ScrollView contentContainerStyle={styles.page}>
    <View style={styles.header}><Pressable accessibilityRole="button" onPress={() => setDetail(null)}><Text style={[styles.back, { color: colors.primary }]}>‹ Библиотека</Text></Pressable><Pressable accessibilityRole="button" disabled={loading} onPress={toggleBookmark}><Text style={[styles.back, { color: colors.primary }]}>{detail.saved ? '★ Сохранено' : '☆ В закладки'}</Text></Pressable></View>
    <Text style={[styles.level, { color: colors.primary }]}>{detail.level} · {detail.minutes} мин.</Text><Text style={[styles.title, { color: colors.text }]}>{detail.emoji} {detail.title}</Text><Text style={[styles.description, { color: colors.muted }]}>{detail.description}</Text>
    {detail.paragraphs.map((paragraph, index) => <Text key={index} style={[styles.paragraph, { color: colors.text }]}>{paragraph}</Text>)}
    {!!detail.glossary.length && <><Text style={[styles.section, { color: colors.text }]}>Слова из текста</Text>{detail.glossary.map((entry) => <View key={entry.surface} style={[styles.wordRow, { borderColor: colors.border }]}><View style={{ flex: 1 }}><Text style={[styles.word, { color: colors.text }]}>{entry.surface} → {entry.lemma}</Text><Text style={{ color: colors.muted }}>{entry.translation}{entry.part_of_speech ? ` · ${entry.part_of_speech}` : ''}</Text></View><Pressable accessibilityRole="button" disabled={loading || savedWords.has(entry.surface)} onPress={() => saveWord(entry.surface)}><Text style={[styles.add, { color: colors.primary }]}>{savedWords.has(entry.surface) ? '✓' : '+ Словарь'}</Text></Pressable></View>)}</>}
    {detail.comprehension_lesson_id && <Action title="Проверить понимание" colors={colors} onPress={() => onOpenLesson(detail.comprehension_lesson_id!)} />}
    {!!error && <Text accessibilityRole="alert" style={{ color: colors.danger }}>{error}</Text>}
  </ScrollView>;

  return <ScrollView contentContainerStyle={styles.page}>
    <View style={styles.header}><Pressable accessibilityRole="button" onPress={onClose}><Text style={[styles.back, { color: colors.primary }]}>‹ Сегодня</Text></Pressable><Text style={{ color: colors.muted }}>{items.length} текстов</Text></View>
    <Text style={[styles.title, { color: colors.text }]}>Читать</Text><Text style={[styles.description, { color: colors.muted }]}>Учебные тексты с леммами и личным словарём.</Text>
    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.levels}>{levels.map((item) => <Pressable key={item} accessibilityRole="button" accessibilityState={{ selected: level === item }} onPress={() => { setLevel(item); setDetail(null); }} style={[styles.levelChip, { borderColor: level === item ? colors.primary : colors.border }]}><Text style={{ color: level === item ? colors.primary : colors.text, fontWeight: '800' }}>{item}</Text></Pressable>)}</ScrollView>
    {loading ? <ActivityIndicator color={colors.primary} /> : items.map((item) => <Pressable accessibilityRole="button" key={item.id} onPress={() => openText(item.id)} style={({ pressed }) => [styles.item, { backgroundColor: colors.surface, borderColor: colors.border, opacity: pressed ? .65 : 1 }]}><Text style={styles.itemEmoji}>{item.emoji || '📄'}</Text><View style={{ flex: 1, gap: 4 }}><Text style={[styles.itemTitle, { color: colors.text }]}>{item.saved ? '★ ' : ''}{item.title}</Text><Text style={{ color: colors.muted }}>{item.description}</Text><Text style={[styles.level, { color: colors.primary }]}>{item.level} · {item.minutes} мин.</Text></View></Pressable>)}
    {!loading && !items.length && !error && <Text style={{ color: colors.muted }}>На этом уровне пока нет текстов.</Text>}{!!error && <Text accessibilityRole="alert" style={{ color: colors.danger }}>{error}</Text>}
  </ScrollView>;
}

function Action({ title, colors, onPress }: { title: string; colors: Colors; onPress: () => void }) { return <Pressable accessibilityRole="button" onPress={onPress} style={({ pressed }) => [styles.action, { backgroundColor: colors.primary, opacity: pressed ? .65 : 1 }]}><Text style={[styles.actionText, { color: colors.onPrimary }]}>{title}</Text></Pressable>; }
const styles = StyleSheet.create({
  page: { padding: 20, paddingBottom: 40, gap: 14 }, header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }, back: { fontSize: 15, fontWeight: '800', paddingVertical: 8 }, title: { fontSize: 30, lineHeight: 38, fontWeight: '900' }, description: { fontSize: 15, lineHeight: 22 }, levels: { gap: 8, paddingVertical: 4 }, levelChip: { borderWidth: 1, borderRadius: 999, paddingHorizontal: 16, paddingVertical: 10 }, item: { flexDirection: 'row', borderWidth: 1, borderRadius: 18, padding: 16, gap: 12 }, itemEmoji: { fontSize: 28 }, itemTitle: { fontSize: 17, fontWeight: '800' }, level: { fontSize: 13, fontWeight: '800' }, paragraph: { fontSize: 18, lineHeight: 29 }, section: { fontSize: 21, fontWeight: '900', marginTop: 8 }, wordRow: { flexDirection: 'row', alignItems: 'center', borderBottomWidth: 1, paddingVertical: 12, gap: 10 }, word: { fontSize: 16, fontWeight: '800' }, add: { fontWeight: '900', paddingVertical: 10 }, action: { minHeight: 50, borderRadius: 14, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 18, marginTop: 8 }, actionText: { fontWeight: '900' },
});
