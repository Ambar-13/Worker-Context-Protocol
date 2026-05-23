/**
 * Service worker bridge for offline evidence capture and background event
 * delivery.
 *
 * The contractor's phone is regularly in basements and stairwells with no
 * connectivity. Evidence captured offline lands in IndexedDB; the bridge
 * flushes the queue when navigator.onLine becomes true and the WebSocket
 * reconnects.
 */

const DB_NAME = "wcp-pwa";
const STORE_EVIDENCE = "evidence_queue";

export interface QueuedEvidence {
  id: string;
  claim_id: string;
  evidence: unknown;
  queued_at: string;
}

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORE_EVIDENCE)) {
        db.createObjectStore(STORE_EVIDENCE, { keyPath: "id" });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

export class ServiceWorkerBridge {
  async enqueue(item: QueuedEvidence): Promise<void> {
    const db = await openDb();
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(STORE_EVIDENCE, "readwrite");
      tx.objectStore(STORE_EVIDENCE).put(item);
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
    db.close();
  }

  async drain(
    handler: (item: QueuedEvidence) => Promise<void>,
  ): Promise<number> {
    const db = await openDb();
    const items: QueuedEvidence[] = await new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_EVIDENCE, "readonly");
      const req = tx.objectStore(STORE_EVIDENCE).getAll();
      req.onsuccess = () => resolve(req.result as QueuedEvidence[]);
      req.onerror = () => reject(req.error);
    });
    let drained = 0;
    for (const item of items) {
      try {
        await handler(item);
        await new Promise<void>((resolve, reject) => {
          const tx = db.transaction(STORE_EVIDENCE, "readwrite");
          tx.objectStore(STORE_EVIDENCE).delete(item.id);
          tx.oncomplete = () => resolve();
          tx.onerror = () => reject(tx.error);
        });
        drained++;
      } catch {
        // Leave in the queue for the next flush.
        break;
      }
    }
    db.close();
    return drained;
  }
}
