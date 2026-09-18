# Abutron Mobile 2.44

One React Native / Expo codebase for Android and iOS, connected to the Abutron Platform API.

## Included

- Registration and login.
- Encrypted access-token storage with Expo SecureStore.
- Customer/account/license bootstrap.
- Current account equity and assigned Flipper / Scalper / Master tier.
- Notification inbox and read state.
- Android/iOS device registration and optional Expo push token registration.
- Pull-to-refresh and profile/logout.

## Setup

1. Install Node.js 22.13+ and Git.
2. Install EAS CLI: `npm install -g eas-cli`.
3. Copy `.env.example` to `.env` and set `EXPO_PUBLIC_ABUTRON_API_URL` to the public HTTPS origin serving the admin/API gateway.
4. Run `powershell -ExecutionPolicy Bypass -File .\SETUP.ps1`.
5. Run `eas login` then `eas init` and put the generated EAS project ID into `app.json`.
6. Android preview: `eas build -p android --profile preview`.
7. Android production AAB: `eas build -p android --profile production`.
8. iOS production IPA: `eas build -p ios --profile production` (Apple signing is still required).

Keep production on the validated Expo SDK 57 baseline until the next SDK is promoted and retested.
