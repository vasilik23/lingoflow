import { useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import type { Session } from '@supabase/supabase-js';
import { loadPracticePreferences, type PracticePreferences } from '../lib/api';
import type { Colors } from '../theme';

const sections = [
  { id: 'reading', emoji: '📖', title: 'Читать', copy: 'Тексты A1–C2, закладки и словарь' },
  { id: 'listening', emoji: '🎧', title: 'Аудирование', copy: 'Диалоги A1–B2 и проверка понимания' },
  { id: 'writing', emoji: '📝', title: 'Письмо', copy: 'Задания B1–B2 и проверка структуры' },
  { id: 'interaction', emoji: '💬', title: 'Общение', copy: 'Взаимодействие и медиация B1–B2' },
  { id: 'diagnostic', emoji: '🧭', title: 'Диагностика', copy: 'Самооценка и короткая проверяемая проба' },
  { id: 'achievements', emoji: '🏆', title: 'Достижения', copy: 'Цели по урокам, серии и словарю' },
  { id: 'history', emoji: '📈', title: 'История', copy: 'Завершённые уроки и результаты' },
] as const;

type SectionId = typeof sections[number]['id'];

export function PracticeScreen({ session, colors, onClose, onOpen }: { session: Session; colors: Colors; onClose: () => void; onOpen: (id: SectionId) => void }) {
  const [recommendation, setRecommendation] = useState<PracticePreferences['recommendation']>(null);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let active = true;
    setLoading(true); setFailed(false); setRecommendation(null);
    void loadPracticePreferences(session.access_token).then((result) => {
      if (active) setRecommendation(result.recommendation);
    }).catch(() => { if (active) setFailed(true); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [session.access_token, retry]);
  return <ScrollView contentContainerStyle={styles.page}>
    <Pressable accessibilityRole="button" onPress={onClose}><Text style={[styles.back, { color: colors.primary }]}>‹ Сегодня</Text></Pressable>
    <Text accessibilityRole="header" style={[styles.title, { color: colors.text }]}>Практика</Text>
    <Text style={[styles.copy, { color: colors.muted }]}>Выберите навык или посмотрите свой прогресс.</Text>
    {loading ? <ActivityIndicator color={colors.primary} /> : failed ? <View>
      <Text accessibilityRole="alert" style={[styles.copy, { color: colors.muted }]}>Рекомендация недоступна. Каталог навыков работает; выбор тем не изменён.</Text>
      <Pressable accessibilityRole="button" onPress={() => setRetry((value) => value + 1)}><Text style={[styles.back, { color: colors.primary }]}>Повторить загрузку рекомендации</Text></Pressable>
    </View> : recommendation ? <Pressable accessibilityRole="button" onPress={() => onOpen(recommendation.screen)} style={[{ borderWidth: 1, borderRadius: 18, padding: 16, gap: 7, borderColor: colors.primary, backgroundColor: colors.surface }]}>
      <Text style={[styles.cardCopy, { color: colors.muted }]}>Рекомендуем с учётом тем из профиля</Text>
      <Text style={[styles.cardTitle, { color: colors.primary }]}>{recommendation.title} →</Text>
    </Pressable> : null}
    <View style={styles.grid}>{sections.map((item) => <Pressable key={item.id} accessibilityRole="button" onPress={() => onOpen(item.id)} style={({ pressed }) => [styles.card, { backgroundColor: colors.surface, borderColor: colors.border, opacity: pressed ? .7 : 1 }]}><Text style={styles.emoji}>{item.emoji}</Text><Text style={[styles.cardTitle, { color: colors.text }]}>{item.title}</Text><Text style={[styles.cardCopy, { color: colors.muted }]}>{item.copy}</Text></Pressable>)}</View>
  </ScrollView>;
}

const styles = StyleSheet.create({ page: { padding: 20, paddingBottom: 48, gap: 12 }, back: { fontSize: 16, fontWeight: '800', paddingVertical: 8 }, title: { fontSize: 32, fontWeight: '900' }, copy: { fontSize: 15, lineHeight: 22, marginBottom: 4 }, grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 }, card: { width: '48%', minHeight: 154, borderWidth: 1, borderRadius: 18, padding: 15, gap: 7 }, emoji: { fontSize: 28 }, cardTitle: { fontSize: 17, fontWeight: '900' }, cardCopy: { fontSize: 13, lineHeight: 18 } });
