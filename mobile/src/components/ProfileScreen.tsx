import { useEffect, useState } from 'react';
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Switch, Text, TextInput, View } from 'react-native';
import type { Session } from '@supabase/supabase-js';

import { loadLearnerProfile, loadReminderPreferences, updateLearnerProfile, updateReminderPreferences, type LearnerProfile } from '../lib/api';
import { supabase } from '../lib/supabase';
import type { Colors } from '../theme';

const levels = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'];

export function ProfileScreen({ session, colors, onClose }: { session: Session; colors: Colors; onClose: () => void }) {
  const [profile, setProfile] = useState<LearnerProfile | null>(null);
  const [goal, setGoal] = useState('');
  const [reminderEnabled, setReminderEnabled] = useState(false);
  const [reminderTime, setReminderTime] = useState('19:00');
  const [deliveryActive, setDeliveryActive] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    let mounted = true;
    Promise.all([loadLearnerProfile(session.access_token), loadReminderPreferences(session.access_token)])
      .then(([nextProfile, reminder]) => {
        if (!mounted) return;
        setProfile(nextProfile); setGoal(String(nextProfile.daily_goal_minutes));
        setReminderEnabled(reminder.preferences.daily_reminder_enabled);
        setReminderTime(reminder.preferences.reminder_time);
        setDeliveryActive(reminder.delivery_active);
      })
      .catch(() => { if (mounted) setError('Не удалось загрузить профиль. Проверьте соединение.'); })
      .finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, [session.access_token]);

  async function save() {
    if (!profile) return;
    const dailyGoal = Number(goal);
    if (!profile.display_name.trim() || profile.display_name.trim().length > 80) return setError('Имя должно содержать от 1 до 80 символов.');
    if (![10, 15, 30].includes(dailyGoal)) return setError('Выберите цель 10, 15 или 30 минут.');
    if (!/^(?:[01]\d|2[0-3]):[0-5]\d$/.test(reminderTime)) return setError('Введите время в формате ЧЧ:ММ, например 19:00.');
    setSaving(true); setError(''); setMessage('');
    let profileSaved = false;
    try {
      const savedProfile = await updateLearnerProfile({ ...profile, display_name: profile.display_name.trim(), daily_goal_minutes: dailyGoal }, session.access_token);
      profileSaved = true;
      const reminder = await updateReminderPreferences({ daily_reminder_enabled: reminderEnabled, reminder_time: reminderTime }, session.access_token);
      setProfile(savedProfile); setGoal(String(savedProfile.daily_goal_minutes)); setDeliveryActive(reminder.delivery_active);
      setMessage('Настройки сохранены.');
    } catch { setError(profileSaved ? 'Профиль сохранён, но настройку напоминаний обновить не удалось.' : 'Не удалось сохранить настройки. Попробуйте снова.'); }
    finally { setSaving(false); }
  }

  if (loading) return <View style={styles.center}><ActivityIndicator size="large" color={colors.primary} /><Text style={{ color: colors.muted }}>Загружаем профиль…</Text></View>;
  return <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={{ flex: 1 }}><ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={styles.page}>
    <Pressable accessibilityRole="button" onPress={onClose}><Text style={[styles.back, { color: colors.primary }]}>‹ Сегодня</Text></Pressable>
    <Text style={[styles.title, { color: colors.text }]}>Профиль</Text>
    {!!error && <Text accessibilityRole="alert" style={{ color: colors.danger }}>{error}</Text>}
    {profile && <>
      <Text style={[styles.label, { color: colors.text }]}>Имя</Text>
      <TextInput accessibilityLabel="Имя" maxLength={80} value={profile.display_name} onChangeText={(display_name) => setProfile({ ...profile, display_name })} style={[styles.input, { color: colors.text, borderColor: colors.border, backgroundColor: colors.surface }]} />
      <Text style={[styles.label, { color: colors.text }]}>Уровень обучения</Text>
      <View accessibilityRole="radiogroup" style={styles.levels}>{levels.map((level) => <Pressable key={level} accessibilityRole="radio" accessibilityState={{ checked: profile.level === level }} onPress={() => setProfile({ ...profile, level })} style={[styles.chip, { borderColor: profile.level === level ? colors.primary : colors.border, backgroundColor: profile.level === level ? colors.surface : 'transparent' }]}><Text style={{ color: profile.level === level ? colors.primary : colors.text, fontWeight: '800' }}>{level}</Text></Pressable>)}</View>
      <Text style={[styles.label, { color: colors.text }]}>Цель на день</Text>
      <View accessibilityRole="radiogroup" style={styles.levels}>{[10, 15, 30].map((minutes) => <Pressable key={minutes} accessibilityRole="radio" accessibilityState={{ checked: goal === String(minutes), disabled: saving }} disabled={saving} onPress={() => setGoal(String(minutes))} style={[styles.chip, { borderColor: goal === String(minutes) ? colors.primary : colors.border }]}><Text style={{ color: colors.text, fontWeight: '800' }}>{minutes} минут</Text></Pressable>)}</View>
      <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
        <View style={styles.switchRow}><View style={styles.switchCopy}><Text style={[styles.cardTitle, { color: colors.text }]}>{deliveryActive ? 'Напоминания' : 'Будущие напоминания'}</Text><Text style={[styles.copy, { color: colors.muted }]}>Предпочтение: ежедневно, часовой пояс Europe/Warsaw</Text></View><Switch accessibilityLabel="Сохранить предпочтение ежедневных напоминаний" value={reminderEnabled} onValueChange={setReminderEnabled} trackColor={{ true: colors.primary }} /></View>
        <Text style={[styles.label, { color: colors.text }]}>Время</Text>
        <TextInput accessibilityLabel="Время напоминания" editable={reminderEnabled} value={reminderTime} onChangeText={setReminderTime} placeholder="19:00" placeholderTextColor={colors.muted} maxLength={5} style={[styles.input, styles.shortInput, { color: colors.text, borderColor: colors.border, backgroundColor: colors.background, opacity: reminderEnabled ? 1 : .55 }]} />
        <Text style={[styles.notice, { color: colors.muted }]}>{deliveryActive ? 'Доставка напоминаний активна.' : 'Настройка сохраняется, но отправка push-уведомлений пока не подключена.'}</Text>
      </View>
      {!!message && <Text accessibilityRole="alert" style={{ color: colors.primary, fontWeight: '800' }}>{message}</Text>}
      <Pressable accessibilityRole="button" disabled={saving} onPress={save} style={({ pressed }) => [styles.button, { backgroundColor: colors.primary, opacity: saving || pressed ? .55 : 1 }]}>{saving ? <ActivityIndicator color="#fff" /> : <Text style={styles.buttonText}>Сохранить</Text>}</Pressable>
      <Pressable accessibilityRole="button" onPress={() => supabase.auth.signOut()} style={[styles.signOut, { borderColor: colors.danger }]}><Text style={{ color: colors.danger, fontWeight: '900' }}>Выйти из аккаунта</Text></Pressable>
    </>}
  </ScrollView></KeyboardAvoidingView>;
}

const styles = StyleSheet.create({
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', gap: 12 }, page: { padding: 20, paddingBottom: 44, gap: 13 }, back: { fontSize: 16, fontWeight: '800', paddingVertical: 8 }, title: { fontSize: 32, fontWeight: '900' }, label: { fontSize: 15, fontWeight: '800', marginTop: 4 }, input: { minHeight: 50, borderWidth: 1, borderRadius: 14, paddingHorizontal: 14, fontSize: 16 }, shortInput: { width: 116 }, levels: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 }, chip: { minWidth: 49, alignItems: 'center', borderWidth: 1, borderRadius: 999, paddingHorizontal: 13, paddingVertical: 10 }, card: { borderWidth: 1, borderRadius: 18, padding: 16, gap: 12, marginTop: 6 }, switchRow: { flexDirection: 'row', alignItems: 'center', gap: 12 }, switchCopy: { flex: 1, gap: 3 }, cardTitle: { fontSize: 17, fontWeight: '800' }, copy: { fontSize: 14, lineHeight: 20 }, notice: { fontSize: 12, lineHeight: 18 }, button: { minHeight: 52, borderRadius: 14, alignItems: 'center', justifyContent: 'center', marginTop: 4 }, buttonText: { color: '#fff', fontSize: 16, fontWeight: '900' }, signOut: { minHeight: 50, borderWidth: 1, borderRadius: 14, alignItems: 'center', justifyContent: 'center', marginTop: 4 },
});
