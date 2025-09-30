import { getDb } from './db'

const API = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000'

export async function syncNow(accessToken:string) {
  const db = getDb()
  const pending = await db.query('SELECT op_id, op_type, payload FROM pending_ops ORDER BY created_at ASC')
  if (pending.values?.length) {
    await fetch(`${API}/sync/push`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${accessToken}` },
      body: JSON.stringify({ ops: pending.values.map(v => ({ op_id:v.op_id, op:v.op_type, data: JSON.parse(v.payload) })) })
    })
    await db.run('DELETE FROM pending_ops') // MVP: assume success
  }
  const since = localStorage.getItem('last_sync') ?? new Date(0).toISOString()
  const res = await fetch(`${API}/sync/pull?since=${encodeURIComponent(since)}`, {
    headers: { 'Authorization': `Bearer ${accessToken}` }
  })
  const delta = await res.json()
  // TODO: upsert checkins & activities from delta into SQLite
  localStorage.setItem('last_sync', delta.server_time ?? new Date().toISOString())
}