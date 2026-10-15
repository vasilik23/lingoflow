export const EAS_CLI_VERSION = '24.14.0';
export const API_ORIGIN = 'https://lingoflow-learn.vercel.app';
export const SUPABASE_ORIGIN = 'https://habcghygjaynknkcbirz.supabase.co';
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function exactOrigin(value, expected) {
  try {
    const url = new URL(value);
    return url.origin === expected && url.pathname === '/' && !url.search && !url.hash && !url.username && !url.password;
  } catch { return false; }
}

// Return fixed messages only. Environment values and command output are never
// part of the report, including malformed URLs, keys and authentication errors.
export function assessBuildReadiness({ app = {}, eas = {}, env = {}, platform, clean = false, authenticated = false }) {
  const checks = [];
  const add = (id, ok, message) => checks.push({ id, ok: ok === true, message });
  add('platform', ['ios', 'android'].includes(platform), 'Платформа должна быть ios или android.');
  add('cli', eas.cli?.version === EAS_CLI_VERSION, `Используйте EAS CLI ${EAS_CLI_VERSION}.`);
  add('committed-source', clean && eas.cli?.requireCommit === true, 'Перед сборкой зафиксируйте изменения; рабочее дерево должно быть чистым.');
  add('internal-profile', eas.build?.preview?.distribution === 'internal', 'Профиль preview должен использовать внутреннее распространение.');
  add('expo-project', typeof app.extra?.eas?.projectId === 'string' && uuid.test(app.extra.eas.projectId), 'Свяжите приложение с настоящим Expo-проектом: npm run eas -- init.');
  add('expo-session', authenticated, 'Подтвердите Expo-сессию: npm run eas -- login, затем build:check -- --check-session.');
  add('application-id', platform === 'ios' ? app.ios?.bundleIdentifier === 'com.lingoflow.mobile' : platform === 'android' && app.android?.package === 'com.lingoflow.mobile', 'Сохраните согласованный идентификатор com.lingoflow.mobile.');
  add('api-origin', exactOrigin(env.EXPO_PUBLIC_API_BASE_URL, API_ORIGIN), 'Задайте локальный публичный URL production LingoFlow API.');
  add('supabase-origin', exactOrigin(env.EXPO_PUBLIC_SUPABASE_URL, SUPABASE_ORIGIN), 'Задайте локальный публичный URL проекта Supabase LingoFlow.');
  add('publishable-key-format', typeof env.EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY === 'string' && /^sb_publishable_[A-Za-z0-9_-]{8,}$/.test(env.EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY) && !/placeholder|example|your_|ci_contract/i.test(env.EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY), 'Задайте publishable key допустимого формата; секретные и legacy JWT-ключи не принимаются.');
  return { platform, readyForBuildAttempt: checks.every((check) => check.ok), checks,
    signing: platform === 'ios'
      ? 'Подпись и UDID iPhone отдельно проверяет EAS при сборке; требуется доступ Apple Developer.'
      : 'Android keystore отдельно проверяет или создаёт EAS при сборке.',
    scope: 'Проверяются локальные условия и, по отдельному флагу, Expo-сессия. Доступность API, действительность ключа, удалённые EAS env и полномочия на подпись этим отчётом не подтверждаются.' };
}
