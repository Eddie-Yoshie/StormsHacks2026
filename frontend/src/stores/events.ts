import { defineStore } from 'pinia';
import { ref } from 'vue';
import type { Event } from '../types/event';
import { createEventProvider } from '../services/eventProvider';
import { createPoller } from '../lib/poll';

export const useEventsStore = defineStore('events', () => {
  const events = ref<Event[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);

  let fetching = false;
  let poller: ReturnType<typeof createPoller> | null = null;

  async function fetchEvents(): Promise<void> {
    if (fetching) {
      return;
    }
    fetching = true;
    try {
      const result = await createEventProvider().listEvents();
      events.value = [...result].sort((a, b) => b.id - a.id);
      error.value = null;
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e);
    } finally {
      fetching = false;
      loading.value = false;
    }
  }

  function startPolling(intervalMs = 1000): void {
    if (poller !== null) {
      return;
    }
    loading.value = true;
    poller = createPoller(fetchEvents, intervalMs);
    poller.start();
  }

  function stopPolling(): void {
    poller?.stop();
    poller = null;
  }

  return { events, loading, error, fetchEvents, startPolling, stopPolling };
});
