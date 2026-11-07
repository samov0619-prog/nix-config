// Keep one active write and a dirty bit, not a promise/string per queued snapshot.
// Callers share the drain promise, which resolves once the latest state is saved.
export function coalescedWriter(write: () => Promise<void>) {
  let pending: Promise<void> | undefined;
  let dirty = false;
  return () => {
    dirty = true;
    pending ??= Promise.resolve().then(async () => {
      try {
        while (dirty) {
          dirty = false;
          await write();
        }
      } finally {
        pending = undefined;
      }
    });
    return pending;
  };
}
