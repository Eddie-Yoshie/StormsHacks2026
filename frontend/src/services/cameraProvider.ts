import type { Camera } from '../types/camera';

/**
 * Provider seam for the camera list. Today the list is static/env-driven;
 * when the backend camera-management API exists, swap the implementation
 * in createCameraProvider() — nothing else changes.
 */
export interface CameraProvider {
  listCameras(): Promise<Camera[]>;
}


interface StateResponse {
  state: {
    active_device: string;
    device_list: Record<string, unknown>;
  };
}

export class BackendCameraProvider implements CameraProvider {
  private readonly baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  async listCameras(): Promise<Camera[]> {
    const res = await fetch(`${this.baseUrl}/devices/state`);
    if (!res.ok) {
      throw new Error(`Failed to load cameras (${res.status})`);
    }
    const data = (await res.json()) as StateResponse;
    return Object.keys(data.state.device_list).map((id) => ({ id, name: id }));
  }
}

export function createCameraProvider(): CameraProvider {
  const baseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
  return new BackendCameraProvider(baseUrl);
}
