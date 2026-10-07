import { useState } from 'react';
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { supabase } from '../lib/supabase';
import type { Colors } from '../theme';

export function LoginScreen({ colors, booting }: { colors: Colors; booting: boolean }) {
  const [email, setEmail] = useState(''); const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false); const [error, setError] = useState('');
  async function signIn() {
    if (!email.trim() || !password) return setError('Введите email и пароль.');
    setSubmitting(true); setError('');
    const { error: authError } = await supabase.auth.signInWithPassword({ email: email.trim(), password });
    if (authError) setError('Не удалось войти. Проверьте данные и соединение.');
    setSubmitting(false);
  }
  return <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={styles.center}>
    <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
      <Text style={[styles.brand, { color: colors.primary }]}>LingoFlow</Text>
      <Text style={[styles.title, { color: colors.text }]}>Продолжим польский?</Text>
      <Text style={[styles.copy, { color: colors.muted }]}>Первый мобильный клиент: вход и персональный план на сегодня.</Text>
      <Text style={[styles.label, { color: colors.text }]}>Email</Text>
      <TextInput accessibilityLabel="Email" autoCapitalize="none" autoComplete="email" keyboardType="email-address" value={email} onChangeText={setEmail} style={[styles.input, { color: colors.text, borderColor: colors.border }]} />
      <Text style={[styles.label, { color: colors.text }]}>Пароль</Text>
      <TextInput accessibilityLabel="Пароль" autoCapitalize="none" autoComplete="current-password" secureTextEntry value={password} onChangeText={setPassword} onSubmitEditing={signIn} style={[styles.input, { color: colors.text, borderColor: colors.border }]} />
      {!!error && <Text accessibilityRole="alert" style={[styles.error, { color: colors.danger }]}>{error}</Text>}
      <Pressable accessibilityRole="button" disabled={booting || submitting} onPress={signIn} style={({ pressed }) => [styles.button, { backgroundColor: colors.primary, opacity: pressed || booting || submitting ? 0.65 : 1 }]}>
        {booting || submitting ? <ActivityIndicator color="#fff" /> : <Text style={styles.buttonText}>Войти</Text>}
      </Pressable>
      <Text style={[styles.note, { color: colors.muted }]}>Сессия хранится в защищённом хранилище устройства. Service-role ключ приложению не нужен.</Text>
    </View>
  </KeyboardAvoidingView>;
}

const styles = StyleSheet.create({
  center: { flex: 1, justifyContent: 'center', padding: 20 }, card: { borderWidth: 1, borderRadius: 24, padding: 24, gap: 10 }, brand: { fontSize: 16, fontWeight: '800' },
  title: { fontSize: 30, fontWeight: '800', marginTop: 4 }, copy: { fontSize: 16, lineHeight: 23, marginBottom: 12 }, label: { fontSize: 14, fontWeight: '700', marginTop: 4 },
  input: { borderWidth: 1, borderRadius: 12, minHeight: 48, paddingHorizontal: 14, fontSize: 16 }, error: { lineHeight: 20 },
  button: { minHeight: 50, borderRadius: 14, alignItems: 'center', justifyContent: 'center', marginTop: 8 }, buttonText: { color: '#fff', fontSize: 16, fontWeight: '800' }, note: { fontSize: 12, lineHeight: 18, marginTop: 8 },
});
