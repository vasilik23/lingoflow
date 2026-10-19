import { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';
import type { Session } from '@supabase/supabase-js';

import { loadAchievements, type AchievementsData } from '../lib/api';
import type { Colors } from '../theme';

export function AchievementsScreen({ session, colors, onClose }: { session: Session; colors: Colors; onClose: () => void }) {
  const [data, setData] = useState<AchievementsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const refresh = useCallback(async () => {
    setLoading(true); setError('');
    try { setData(await loadAchievements(session.access_token)); }
    catch { setError('Не удалось загрузить достижения. Проверьте соединение.'); }
    finally { setLoading(false); }
  }, [session.access_token]);
  useEffect(() => { void refresh(); }, [refresh]);

  if (!data && loading) return <View style={styles.center}><ActivityIndicator size="large" color={colors.primary} /><Text style={{ color: colors.muted }}>Загружаем достижения…</Text></View>;
  return <ScrollView contentContainerStyle={styles.page} refreshControl={<RefreshControl refreshing={loading} onRefresh={refresh} tintColor={colors.primary} />}>
    <Pressable accessibilityRole="button" onPress={onClose}><Text style={[styles.back, { color: colors.primary }]}>‹ Сегодня</Text></Pressable>
    <Text style={[styles.title, { color: colors.text }]}>Достижения</Text>
    <Text style={[styles.copy, { color: colors.muted }]}>Прогресс рассчитывается по синхронизированным урокам, серии занятий и личному словарю — отдельные награды не начисляются вручную.</Text>
    {!!error && <View style={[styles.alert, { borderColor: colors.danger }]}><Text accessibilityRole="alert" style={{ color: colors.danger }}>{error}</Text><Pressable accessibilityRole="button" onPress={refresh}><Text style={[styles.retry, { color: colors.primary }]}>Повторить</Text></Pressable></View>}
    {data && <>
      <View accessible accessibilityLabel={`Открыто достижений: ${data.unlocked_count} из ${data.achievement_count}`} style={[styles.summary, { backgroundColor: colors.surface }]}><Text style={[styles.summaryLabel, { color: colors.muted }]}>Открыто</Text><Text style={[styles.summaryValue, { color: colors.text }]}>{data.unlocked_count} / {data.achievement_count}</Text></View>
      {data.achievements.map((item) => <View key={item.id} accessible accessibilityLabel={`${item.title}. ${item.description}. ${item.unlocked ? 'Открыто' : `Прогресс ${item.current} из ${item.target}`}`} style={[styles.card, { backgroundColor: colors.surface, borderColor: item.unlocked ? colors.success : colors.border }]}>
        <Text style={[styles.icon, { opacity: item.unlocked ? 1 : .55 }]}>{item.icon}</Text>
        <View style={styles.cardBody}><View style={styles.cardHeading}><Text style={[styles.cardTitle, { color: colors.text }]}>{item.title}</Text><Text style={[styles.state, { color: item.unlocked ? colors.success : colors.muted }]}>{item.unlocked ? 'Открыто' : `${item.current} / ${item.target}`}</Text></View><Text style={[styles.description, { color: colors.muted }]}>{item.description}</Text><View style={[styles.track, { backgroundColor: colors.border }]}><View style={[styles.fill, { backgroundColor: colors.primary, width: `${Math.max(0, Math.min(item.progress_percent, 100))}%` }]} /></View></View>
      </View>)}
    </>}
  </ScrollView>;
}

const styles = StyleSheet.create({
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', gap: 12 }, page: { padding: 20, paddingBottom: 44, gap: 14 }, back: { fontSize: 16, fontWeight: '800', paddingVertical: 8 }, title: { fontSize: 32, fontWeight: '900' }, copy: { fontSize: 15, lineHeight: 22 }, alert: { borderWidth: 1, borderRadius: 14, padding: 14, gap: 4 }, retry: { fontWeight: '800', paddingVertical: 8 }, summary: { borderRadius: 22, padding: 20 }, summaryLabel: { fontWeight: '700' }, summaryValue: { fontSize: 34, fontWeight: '900', marginTop: 4 }, card: { flexDirection: 'row', borderWidth: 1, borderRadius: 18, padding: 16, gap: 12 }, icon: { fontSize: 30 }, cardBody: { flex: 1, gap: 7 }, cardHeading: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }, cardTitle: { flex: 1, fontSize: 17, fontWeight: '800' }, state: { fontSize: 12, fontWeight: '900' }, description: { fontSize: 14, lineHeight: 20 }, track: { height: 7, borderRadius: 10, overflow: 'hidden' }, fill: { height: 7, borderRadius: 10 },
});
