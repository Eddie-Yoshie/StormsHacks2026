import { DEFAULT_ACTIVE_FLAGS, type Camera } from '../types/camera';
import { apiBaseUrl } from './api';

/**
 * Provider seam for the camera list, backed by the backend's /devices/state.
 */
export interface CameraList {
  cameras: Camera[];
  /** The backend's active device, or '' when there is none. */
  activeDevice: string;
}

export interface CameraProvider {
  listCameras(): Promise<CameraList>;
}

interface StateResponse {
  state: {
    active_device: string;
    device_list: Record<string, boolean[]>;
  };
  active_flags: Record<string, boolean[]>;
  noise_enabled: Record<string, boolean>;
}

export class BackendCameraProvider implements CameraProvider {
  private readonly baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  async listCameras(): Promise<CameraList> {
    const res = await fetch(`${this.baseUrl}/devices/state`);
    if (!res.ok) {
      throw new Error(`Failed to load cameras (${res.status})`);
    }
    const data = (await res.json()) as StateResponse;
    const cameras = Object.entries(data.state.device_list).map(([id, flags]) => ({
      id,
      name: id,
      flags,
      activeFlags: data.active_flags[id] ?? [...DEFAULT_ACTIVE_FLAGS],
      noiseEnabled: data.noise_enabled[id] ?? true,
    }));
    return { cameras, activeDevice: data.state.active_device };
  }
}

export function createCameraProvider(): CameraProvider {
  return new BackendCameraProvider(apiBaseUrl);
}
