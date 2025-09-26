import { getDb } from './db'

export async function upsertCheckin(c:{date:string;mood:number;energy:number;note?:string}) {
  const now = new Date().toISOString()
  const db = getDb()
  await db.run(
    `INSERT INTO mood_checkins(date,mood,energy,note,last_modified) VALUES (?,?,?,?,?)
     ON CONFLICT(date) DO UPDATE SET mood=excluded.mood, energy=excluded.energy, note=excluded.note, last_modified=excluded.last_modified`,
    [c.date, c.mood, c.energy, c.note ?? null, now]
  )
}

export async function createActivity(a:{type:string;minutes:number;occurred_at:string;intensity?:number;note?:string}) {
  const now = new Date().toISOString()
  const db = getDb()
  await db.run(
    `INSERT INTO activities(type,minutes,intensity,note,occurred_at,source,source_id,last_modified)
     VALUES (?,?,?,?,?,'manual',NULL,?)`,
    [a.type, a.minutes, a.intensity ?? null, a.note ?? null, a.occurred_at, now]
  )
}

export async function enqueueOp(op_type:string, payload:unknown) {
  const db = getDb()
  const op_id = (globalThis.crypto?.randomUUID?.() ?? Math.random().toString(36).slice(2)) as string
  await db.run(
    `INSERT INTO pending_ops(op_id,op_type,payload,created_at) VALUES (?,?,?,?)`,
    [op_id, op_type, JSON.stringify(payload), new Date().toISOString()]
  )
}