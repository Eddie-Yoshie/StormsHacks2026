import { defineStore } from 'pinia';
import { ref } from 'vue';
import type { Event } from '../types/event';
import { createEventProvider } from '../services/eventProvider';

export const useEventsStore = defineStore('events', () => {
  const events = ref<Event[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);

  let pollTimer: ReturnType<typeof setTimeout> | null = null;
  let fetching = false;
  let stopped = true;
  let pollIntervalMs = 1000;

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

  async function poll(): Promise<void> {
    if (stopped) {
      return;
    }
    await fetchEvents();
    if (!stopped) {
      pollTimer = setTimeout(() => void poll(), pollIntervalMs);
    }
  }

  function startPolling(intervalMs = 1000): void {
    if (!stopped) {
      return;
    }
    stopped = false;
    pollIntervalMs = intervalMs;
    loading.value = true;
    void poll();
  }

  function stopPolling(): void {
    stopped = true;
    if (pollTimer !== null) {
      clearTimeout(pollTimer);
      pollTimer = null;
    }
  }

  return { events, loading, error, fetchEvents, startPolling, stopPolling };
});
