/**
 * Local notifications helper.
 * Works on native (iOS/Android). On web, it no-ops safely.
 */
export async function scheduleDailyPrompts() {
  try {
    // Dynamic import so the app still builds even if the plugin isn't available on web.
    const { LocalNotifications } = await import('@capacitor/local-notifications')

    await LocalNotifications.requestPermissions()
    await LocalNotifications.schedule({
      notifications: [
        {
          id: 730,
          title: 'Good morning',
          body: 'Today has been good, how about you? Log a quick check-in.',
          schedule: { repeats: true, on: { hour: 7, minute: 30 } } // 7:30 AM local
        },
        {
          id: 2030,
          title: 'Evening reflection',
          body: 'Wrap the day with a 1-minute reflection.',
          schedule: { repeats: true, on: { hour: 20, minute: 30 } } // 8:30 PM local
        }
      ]
    })
  } catch (err) {
    // Likely running in web where the plugin isn't available, or not installed yet.
    // Fail silently to keep dev workflow smooth.
    console.warn('[notify] LocalNotifications unavailable; skipping schedule.', err)
  }
}