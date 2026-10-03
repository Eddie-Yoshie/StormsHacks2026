import type { Camera } from '../types/camera';

/**
 * Provider seam for the camera list. Today the list is static/env-driven;
 * when the backend camera-management API exists, swap the implementation
 * in createCameraProvider() — nothing else changes.
 */
export interface CameraProvider {
  listCameras(): Promise<Camera[]>;
}

export class StaticCameraProvider implements CameraProvider {
  private readonly cameras: Camera[];

  constructor(cameras: Camera[]) {
    this.cameras = cameras;
  }

  listCameras(): Promise<Camera[]> {
    return Promise.resolve(this.cameras);
  }
}

function defaultCameras(): Camera[] {
  const ids = (import.meta.env.VITE_CAMERA_IDS as string | undefined)
    ?.split(',')
    .map((id) => id.trim())
    .filter(Boolean);
  if (ids && ids.length > 0) {
    return ids.map((id) => ({ id, name: id }));
  }
  return [{ id: 'demo', name: 'Demo Camera', description: 'Default MediaMTX path' }];
}

export function createCameraProvider(): CameraProvider {
  // Later: return new BackendCameraProvider(import.meta.env.VITE_API_BASE_URL);
  return new StaticCameraProvider(defaultCameras());
}
