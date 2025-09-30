# GoodToday (Ionic + Vue + Capacitor)

Mobile-first well-being tracker with quick daily check-ins, micro-activities, offline-first SQLite, and gentle notifications.

## Stack
- **Frontend:** Ionic + Vue 3 + Vite + Capacitor
- **Local DB:** @capacitor-community/sqlite
- **Notifications:** @capacitor/local-notifications
- **Backend (planned):** FastAPI + PostgreSQL (endpoints: /checkins, /activities, /sync, /insights)

## Prerequisites
- Node LTS (use `nvm use --lts`)
- Xcode (iOS) / Android Studio (Android)
- Capacitor CLI via `npx` (no global install required)

## First-time Setup

```bash
# install deps
npm i

# add plugins (already in package.json if you followed scaffold)
npm i @capacitor-community/sqlite @capacitor/local-notifications @capacitor/app @capacitor/device

# build web assets & sync to native
npm run build
npx cap sync

# open native projects
npx cap open ios
npx cap open android