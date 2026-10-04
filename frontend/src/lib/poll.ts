/**
 * Calls `fn` every `intervalMs` until stopped. The next call is scheduled only after the
 * previous one settles, so slow requests never pile up.
 */
export function createPoller(fn: () => Promise<void>, intervalMs: number) {
  let timer: ReturnType<typeof setTimeout> | null = null;
  let stopped = true;

  async function tick(): Promise<void> {
    if (stopped) {
      return;
    }
    await fn();
    if (!stopped) {
      timer = setTimeout(() => void tick(), intervalMs);
    }
  }

  function start(): void {
    if (!stopped) {
      return;
    }
    stopped = false;
    void tick();
  }

  function stop(): void {
    stopped = true;
    if (timer !== null) {
      clearTimeout(timer);
      timer = null;
    }
  }

  return { start, stop };
}
