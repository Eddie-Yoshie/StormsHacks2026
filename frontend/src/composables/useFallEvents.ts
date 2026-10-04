import { reactive } from 'vue';
import { ackAlert, apiBaseUrl as apiBase } from '../services/api';

export interface FallEvent {
  id: number;
  camera_id: string;
  /** Unix seconds when the vision worker detected the fall. */
  ts: number;
  confidence: 'high' | 'low';
  kind: 'fall' | 'bathroom_timeout' | 'dead_check';
  details: Record<string, unknown>;
}

const KIND_LABELS: Record<string, { tag: string; type: 'error' | 'warning' | 'info' }> = {
  fall: { tag: 'FALL', type: 'error' },
  dead_check: { tag: 'NO MOVEMENT', type: 'error' },
  bathroom_timeout: { tag: 'BATHROOM', type: 'warning' },
};

/** Short tag and color for an event kind, for lists such as the event history. */
export function kindLabel(kind: string): { tag: string; type: 'error' | 'warning' | 'info' } {
  return KIND_LABELS[kind] ?? { tag: kind.toUpperCase(), type: 'info' };
}

/** Headline text for an alert, shared by the camera card and the front-desk notification. */
export function describeAlert(event: FallEvent): { tag: string; title: string; detail: string } {
  if (event.kind === 'bathroom_timeout') {
    const seconds = Number(event.details.present_s ?? 0);
    const duration = seconds < 90 ? `${Math.round(seconds)} s` : `${Math.round(seconds / 60)} min`;
    return { tag: 'BATHROOM', title: 'Bathroom timeout', detail: `In the bathroom for ${duration}, may need help getting up` };
  }
  if (event.kind === 'dead_check') {
    const seconds = Number(event.details.still_s ?? 0);
    const duration = seconds < 90 ? `${Math.round(seconds)} s` : `${Math.round(seconds / 60)} min`;
    return { tag: 'NO MOVEMENT', title: 'No movement detected', detail: `Has not moved for ${duration}, may be unresponsive` };
  }
  return {
    tag: 'FALL',
    title: 'Fall detected',
    detail: event.confidence === 'high' ? 'High confidence' : 'Low confidence (person left view)',
  };
}

/** Latest undismissed fall per camera id. Shared by every component using the composable. */
const falls = reactive<Record<string, FallEvent>>({});
const listeners = new Set<(event: FallEvent) => void>();
let started = false;

function connect(): void {
  const url = `${apiBase.replace(/^http/, 'ws').replace(/\/+$/, '')}/vision/ws`;
  const socket = new WebSocket(url);
  socket.onmessage = (msg) => {
    const data = JSON.parse(msg.data as string) as
      | { type: 'fall'; event: FallEvent }
      | { type: 'ack'; camera_id: string };
    if (data.type === 'fall') {
      falls[data.event.camera_id] = data.event;
      listeners.forEach((fn) => fn(data.event));
    } else if (data.type === 'ack') {
      // Acknowledged on this or another dashboard.
      delete falls[data.camera_id];
    }
  };
  socket.onclose = () => {
    // Backend restarted or unreachable: keep retrying so alerts resume on their own.
    setTimeout(connect, 2000);
  };
}

/** Live fall alerts pushed by the backend over one shared WebSocket. */
export function useFallEvents() {
  if (!started) {
    started = true;
    connect();
  }

  /** Acknowledge the camera's alert: hide it here right away and clear it on the backend for every dashboard. */
  function dismiss(cameraId: string): void {
    delete falls[cameraId];
    ackAlert(cameraId).catch((e: unknown) => console.warn('Could not acknowledge alert', e));
  }

  /** Call fn for every new alert as it arrives; returns an unsubscribe function. */
  function onAlert(fn: (event: FallEvent) => void): () => void {
    listeners.add(fn);
    return () => listeners.delete(fn);
  }

  return { falls, dismiss, onAlert };
}
