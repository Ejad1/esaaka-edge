// Local store-and-forward queue (IndexedDB). Everything stays on the device until the user chooses to share it.
import { openDB } from 'idb';

const dbp = openDB('esaaka-edge', 1, { upgrade(db) { db.createObjectStore('observations', { keyPath: 'id', autoIncrement: true }); } });

export async function addObservation(o) { return (await dbp).add('observations', { ...o, ts: Date.now(), status: 'pending' }); }
export async function listObservations() { return ((await (await dbp).getAll('observations')) || []).sort((a, b) => b.ts - a.ts); }
export async function markShared(id) { const db = await dbp, o = await db.get('observations', id); if (o) { o.status = 'shared'; o.sharedTs = Date.now(); await db.put('observations', o); } }
export async function removeObservation(id) { return (await dbp).delete('observations', id); }
export async function pendingCount() { return (await listObservations()).filter((o) => o.status === 'pending').length; }
