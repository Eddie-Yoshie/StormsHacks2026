import { reactive } from 'vue';
import { ackAlert, apiBaseUrl as apiBase } from '../services/api';

export interface FallEvent {
  id: number;
  camera_id: string;
  /** Unix seconds when the vision worker detected the fall. */
  ts: number;
  confidence: 'high' | 'low';
  /** loud_noise comes from the backend's audio watcher rather than the vision worker. */
  kind: 'fall' | 'bathroom_timeout' | 'dead_check' | 'loud_noise';
  details: Record<string, unknown>;
}

export type AlertSeverity = 'error' | 'warning';

const KIND_LABELS: Record<string, { tag: string; type: AlertSeverity | 'info' }> = {
  fall: { tag: 'FALL', type: 'error' },
  dead_check: { tag: 'NO MOVEMENT', type: 'error' },
  bathroom_timeout: { tag: 'BATHROOM', type: 'warning' },
  loud_noise: { tag: 'LOUD NOISE', type: 'warning' },
};

/** Short tag and color for an event kind, for lists such as the event history. */
export function kindLabel(kind: string): { tag: string; type: 'error' | 'warning' | 'info' } {
  return KIND_LABELS[kind] ?? { tag: kind.toUpperCase(), type: 'info' };
}

/** Headline text for an alert, shared by the camera card and the front-desk notification. */
export function describeAlert(event: FallEvent): { tag: string; title: string; detail: string; type: AlertSeverity } {
  if (event.kind === 'bathroom_timeout') {
    const seconds = Number(event.details.present_s ?? 0);
    const duration = seconds < 90 ? `${Math.round(seconds)} s` : `${Math.round(seconds / 60)} min`;
    return { tag: 'BATHROOM', title: 'Bathroom timeout', detail: `In the bathroom for ${duration}, may need help getting up`, type: 'error' };
  }
  if (event.kind === 'dead_check') {
    const seconds = Number(event.details.still_s ?? 0);
    const duration = seconds < 90 ? `${Math.round(seconds)} s` : `${Math.round(seconds / 60)} min`;
    return { tag: 'NO MOVEMENT', title: 'No movement detected', detail: `Has not moved for ${duration}, may be unresponsive`, type: 'error' };
  }
  if (event.kind === 'loud_noise') {
    const level = Number(event.details.level_db ?? NaN);
    const detail = Number.isFinite(level) ? `Sound reached ${Math.round(level)} dBFS near the camera` : 'Loud sound near the camera';
    return { tag: 'LOUD NOISE', title: 'Loud noise', detail, type: 'warning' };
  }
  return {
    tag: 'FALL',
    title: 'Fall detected',
    detail: event.confidence === 'high' ? 'High confidence' : 'Low confidence (person left view)',
    type: 'error',
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
