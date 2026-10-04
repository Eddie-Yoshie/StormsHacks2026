/** Mutating calls to the backend. Reads go through the providers in this folder. */

import { resolveServiceUrl } from './urls';

export const apiBaseUrl: string = resolveServiceUrl(import.meta.env.VITE_API_BASE_URL, 8000);

async function send(method: string, path: string, body?: unknown): Promise<Response> {
  const res = await fetch(`${apiBaseUrl}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`${method} ${path} failed (${res.status}): ${detail}`);
  }
  return res;
}

const devicePath = (name: string): string => `/devices/${encodeURIComponent(name)}`;

export async function addDevice(name: string, rtspUrl: string, activeFlags: boolean[], noiseEnabled: boolean): Promise<void> {
  await send('POST', '/devices', { name, rtsp_url: rtspUrl, active_flags: activeFlags, noise_enabled: noiseEnabled });
}

export async function removeDevice(name: string): Promise<void> {
  await send('DELETE', devicePath(name));
}

export async function setActiveDevice(name: string): Promise<void> {
  await send('PUT', '/devices/active', { name });
}

/** Recreates the camera's vision container, so this can take several seconds. */
export async function setActiveFlags(name: string, activeFlags: boolean[]): Promise<void> {
  await send('PUT', `${devicePath(name)}/active-flags`, { active_flags: activeFlags });
}

export async function setNoiseEnabled(name: string, enabled: boolean): Promise<void> {
  await send('PUT', `${devicePath(name)}/noise`, { enabled });
}

/** Clear the camera's flags and dismiss its alert on every dashboard. */
export async function ackAlert(cameraId: string): Promise<void> {
  await send('POST', `/vision/alerts/${encodeURIComponent(cameraId)}/ack`);
}
