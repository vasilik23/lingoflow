# Mobile closed beta runbook

The repository contains an Expo/React Native vertical slice for iOS and
Android. `preview` produces an internally distributed, production-like build;
`production` is reserved for store binaries. Neither profile enables an
authenticated offline content cache.

## One-time Expo setup

An Expo account and an EAS project are external prerequisites. From `mobile/`:

```bash
npx eas-cli@latest login
npx eas-cli@latest init
npx eas-cli@latest env:create preview --name EXPO_PUBLIC_API_BASE_URL --value https://lingoflow-learn.vercel.app --visibility plaintext
npx eas-cli@latest env:create preview --name EXPO_PUBLIC_SUPABASE_URL --value https://YOUR_PROJECT.supabase.co --visibility plaintext
npx eas-cli@latest env:create preview --name EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY --value YOUR_PUBLIC_PUBLISHABLE_KEY --visibility plaintext
```

Only the Supabase publishable key is allowed in `EXPO_PUBLIC_*`. Never add a
`service_role`, database password, signing credential, or private API token.
Repeat the three public variables for the `production` EAS environment before
a store build.

## Installable beta builds

```bash
npm ci
npm run verify
npx eas-cli@latest build --platform android --profile preview
npx eas-cli@latest device:create
npx eas-cli@latest build --platform ios --profile preview
```

Android internal distribution produces an installable APK. iOS internal
distribution requires an Apple Developer account, a registered test device,
and an ad hoc provisioning profile; EAS may manage signing credentials. The
`preview-simulator` profile is available when no physical iOS device is ready.

## Device acceptance gate

Test one current Android device and one current iPhone:

1. clean install and email/password login;
2. Today loads without exposing a token or secret in visible errors;
3. start a lesson, finish at least one step, terminate the app, relaunch and
   resume at the same step and score;
4. finish the lesson, confirm the completion after pull-to-refresh, then log
   out and confirm Today is no longer reachable;
5. repeat once with a temporary network interruption; no result may be shown
   as saved until the server confirms it;
6. verify system dark/light themes, large text, VoiceOver/TalkBack labels and
   absence of horizontal clipping.

Record build IDs, OS/device versions, tester, date and failures. A successful
Metro export is necessary but does not replace this physical-device gate.
