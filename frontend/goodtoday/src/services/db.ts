import { CapacitorSQLite, SQLiteDBConnection } from '@capacitor-community/sqlite'

let db: SQLiteDBConnection | null = null;

export async function initDb() {
  const ret = await CapacitorSQLite.createConnection({
    database: 'goodtoday',
    version: 1,
    encrypted: false,
    mode: 'no-encryption'
  })
  db = ret
  await db.open()
  // Schema: note the UNIQUE index on date so ON CONFLICT(date) works in repo.ts
  await db.execute(`
    CREATE TABLE IF NOT EXISTS mood_checkins (
      id INTEGER PRIMARY KEY,
      date TEXT NOT NULL,
      mood INTEGER NOT NULL,
      energy INTEGER NOT NULL,
      note TEXT,
      last_modified TEXT NOT NULL
    );
    CREATE UNIQUE INDEX IF NOT EXISTS idx_checkins_date ON mood_checkins(date);

    CREATE TABLE IF NOT EXISTS activities (
      id INTEGER PRIMARY KEY,
      type TEXT NOT NULL,
      minutes INTEGER NOT NULL,
      intensity INTEGER,
      note TEXT,
      occurred_at TEXT NOT NULL,
      source TEXT,
      source_id TEXT,
      last_modified TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_acts_occ ON activities(occurred_at);

    CREATE TABLE IF NOT EXISTS pending_ops (
      op_id TEXT PRIMARY KEY,
      op_type TEXT NOT NULL,
      payload TEXT NOT NULL,
      created_at TEXT NOT NULL
    );
  `)
}

export function getDb(): SQLiteDBConnection {
  if (!db) throw new Error('DB not initialized')
  return db
}