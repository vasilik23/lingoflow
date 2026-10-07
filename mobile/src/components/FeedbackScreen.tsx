import { useState } from 'react';
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import type { Session } from '@supabase/supabase-js';

import { sendFeedback, type FeedbackCategory } from '../lib/api';
import type { Colors } from '../theme';

const categories: { id: FeedbackCategory; label: string }[] = [
  { id: 'technical', label: 'Ошибка' }, { id: 'content', label: 'Материал' },
  { id: 'translation', label: 'Перевод' }, { id: 'interface', label: 'Интерфейс' }, { id: 'idea', label: 'Идея' },
];

export function FeedbackScreen({ session, colors, onClose }: { session: Session; colors: Colors; onClose: () => void }) {
  const [category, setCategory] = useState<FeedbackCategory>('technical');
  const [message, setMessage] = useState(''); const [busy, setBusy] = useState(false);
  const [error, setError] = useState(''); const [sent, setSent] = useState(false);

  async function submit() {
    const clean = message.trim();
    if (clean.length < 20) return setError('Добавьте немного деталей — минимум 20 символов.');
    setBusy(true); setError('');
    try { await sendFeedback(category, clean, session.access_token); setSent(true); }
    catch { setError('Не удалось отправить сообщение. Проверьте соединение и попробуйте снова.'); }
    finally { setBusy(false); }
  }

  if (sent) return <View style={styles.center}><Text style={styles.emoji}>💚</Text><Text style={[styles.title, { color: colors.text }]}>Спасибо!</Text><Text style={[styles.copy, { color: colors.muted }]}>Сообщение сохранено. Мы используем его только для улучшения LingoFlow.</Text><Button title="Вернуться в Сегодня" colors={colors} onPress={onClose} /></View>;

  return <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={{ flex: 1 }}><ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={styles.page}>
    <Pressable accessibilityRole="button" onPress={onClose}><Text style={[styles.back, { color: colors.primary }]}>‹ Сегодня</Text></Pressable>
    <Text style={[styles.title, { color: colors.text }]}>Обратная связь</Text>
    <Text style={[styles.copy, { color: colors.muted }]}>Не добавляйте пароль, токены, платёжные или другие чувствительные данные.</Text>
    <Text style={[styles.label, { color: colors.text }]}>Категория</Text>
    <View accessibilityRole="radiogroup" style={styles.categories}>{categories.map((item) => <Pressable key={item.id} accessibilityRole="radio" accessibilityState={{ checked: category === item.id }} onPress={() => setCategory(item.id)} style={[styles.chip, { borderColor: category === item.id ? colors.primary : colors.border, backgroundColor: category === item.id ? colors.surface : 'transparent' }]}><Text style={{ color: category === item.id ? colors.primary : colors.text, fontWeight: '700' }}>{item.label}</Text></Pressable>)}</View>
    <Text style={[styles.label, { color: colors.text }]}>Что произошло или что можно улучшить?</Text>
    <TextInput accessibilityLabel="Сообщение обратной связи" multiline maxLength={2000} textAlignVertical="top" value={message} onChangeText={setMessage} placeholder="Опишите шаги, ожидаемый и фактический результат…" placeholderTextColor={colors.muted} style={[styles.input, { color: colors.text, borderColor: colors.border, backgroundColor: colors.surface }]} />
    <Text style={[styles.counter, { color: colors.muted }]}>{message.length} / 2000</Text>
    {!!error && <Text accessibilityRole="alert" style={{ color: colors.danger }}>{error}</Text>}
    <Button title="Отправить" colors={colors} disabled={busy || message.trim().length < 20} onPress={submit} busy={busy} />
  </ScrollView></KeyboardAvoidingView>;
}

function Button({ title, colors, onPress, disabled = false, busy = false }: { title: string; colors: Colors; onPress: () => void; disabled?: boolean; busy?: boolean }) {
  return <Pressable accessibilityRole="button" disabled={disabled} onPress={onPress} style={({ pressed }) => [styles.button, { backgroundColor: colors.primary, opacity: disabled || pressed ? .55 : 1 }]}>{busy ? <ActivityIndicator color="#fff" /> : <Text style={styles.buttonText}>{title}</Text>}</Pressable>;
}

const styles = StyleSheet.create({
  page: { padding: 20, paddingBottom: 40, gap: 14 }, center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 28, gap: 14 }, back: { fontSize: 16, fontWeight: '800', paddingVertical: 8 }, title: { fontSize: 30, fontWeight: '900' }, copy: { fontSize: 15, lineHeight: 22 }, label: { fontSize: 15, fontWeight: '800', marginTop: 5 }, categories: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 }, chip: { borderWidth: 1, borderRadius: 999, paddingHorizontal: 14, paddingVertical: 10 }, input: { minHeight: 170, borderWidth: 1, borderRadius: 16, padding: 14, fontSize: 16, lineHeight: 23 }, counter: { textAlign: 'right', fontSize: 12 }, button: { minHeight: 50, borderRadius: 14, alignItems: 'center', justifyContent: 'center' }, buttonText: { color: '#fff', fontWeight: '900', fontSize: 16 }, emoji: { fontSize: 50 },
});
