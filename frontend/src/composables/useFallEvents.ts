import { reactive } from 'vue';

export interface FallEvent {
  id: number;
  camera_id: string;
  /** Unix seconds when the vision worker detected the fall. */
  ts: number;
  confidence: 'high' | 'low';
  details: Record<string, unknown>;
}

const apiBase: string = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

/** Latest undismissed fall per camera id. Shared by every component using the composable. */
const falls = reactive<Record<string, FallEvent>>({});
let started = false;

function connect(): void {
  const url = `${apiBase.replace(/^http/, 'ws').replace(/\/+$/, '')}/vision/ws`;
  const socket = new WebSocket(url);
  socket.onmessage = (msg) => {
    const data = JSON.parse(msg.data as string) as { type: string; event: FallEvent };
    if (data.type === 'fall') {
      falls[data.event.camera_id] = data.event;
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

  function dismiss(cameraId: string): void {
    delete falls[cameraId];
  }

  return { falls, dismiss };
}
