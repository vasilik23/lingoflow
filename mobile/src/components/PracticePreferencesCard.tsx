import { useEffect, useRef, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Switch, Text, View } from 'react-native';
import { loadPracticePreferences, updatePracticePreferences } from '../lib/api';
import type { Colors } from '../theme';

export function PracticePreferencesCard({ accessToken, colors }: { accessToken: string; colors: Colors }) {
  const [excluded, setExcluded] = useState(false);
  const [available, setAvailable] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);
  const generation = useRef(0);
  useEffect(() => {
    const current = ++generation.current;
    setLoading(true); setAvailable(false); setSaving(false); setMessage(''); setError('');
    void loadPracticePreferences(accessToken).then((result) => {
      if (generation.current !== current) return;
      setExcluded(result.preferences.exclude_remote_work); setAvailable(true);
    }).catch(() => {
      if (generation.current === current) setError('Темы не загружены. Повторите запрос, чтобы не перезаписать прежний выбор.');
    }).finally(() => { if (generation.current === current) setLoading(false); });
    return () => { generation.current++; };
  }, [accessToken, retry]);
  async function save() {
    if (!available || saving) return;
    const current = generation.current;
    setSaving(true); setError(''); setMessage('');
    try {
      const result = await updatePracticePreferences(excluded, accessToken);
      if (generation.current === current) {
        setExcluded(result.preferences.exclude_remote_work);
        setMessage('Темы сохранены для всех устройств.');
      }
    } catch { if (generation.current === current) setError('Не удалось синхронизировать темы. Попробуйте ещё раз.'); }
    finally { if (generation.current === current) setSaving(false); }
  }
  return <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
    <Text accessibilityRole="header" style={[styles.title, { color: colors.text }]}>Темы практики</Text>
    <Text style={[styles.copy, { color: colors.muted }]}>Новые варианты B1 и рекомендации B2 учитывают этот выбор на всех устройствах. Начатые задания не меняются.</Text>
    {loading ? <ActivityIndicator color={colors.primary} /> : available ? <View style={styles.row}>
      <Text style={[styles.label, { color: colors.text }]}>Не предлагать удалённую и гибридную работу</Text>
      <Switch accessibilityLabel="Не предлагать удалённую и гибридную работу" disabled={saving} value={excluded} onValueChange={(value) => { setExcluded(value); setMessage(''); }} trackColor={{ true: colors.primary }} />
    </View> : <Pressable accessibilityRole="button" onPress={() => setRetry((value) => value + 1)}><Text style={{ color: colors.primary }}>Повторить загрузку тем</Text></Pressable>}
    {!!error && <Text accessibilityRole="alert" style={{ color: colors.danger }}>{error}</Text>}
    {!!message && <Text accessibilityLiveRegion="polite" style={{ color: colors.primary }}>{message}</Text>}
    {available && <Pressable accessibilityRole="button" accessibilityState={{ disabled: saving }} disabled={saving} onPress={save} style={[styles.button, { borderColor: colors.primary, opacity: saving ? .5 : 1 }]}><Text style={{ color: colors.primary, fontWeight: '800' }}>{saving ? 'Сохраняем темы…' : 'Сохранить темы'}</Text></Pressable>}
  </View>;
}

const styles = StyleSheet.create({ card: { borderWidth: 1, borderRadius: 18, padding: 16, gap: 12 }, title: { fontSize: 17, fontWeight: '800' }, copy: { fontSize: 14, lineHeight: 20 }, row: { flexDirection: 'row', alignItems: 'center', gap: 12 }, label: { flex: 1, fontSize: 15, lineHeight: 21 }, button: { minHeight: 48, borderWidth: 1, borderRadius: 14, padding: 12, alignItems: 'center', justifyContent: 'center' } });
