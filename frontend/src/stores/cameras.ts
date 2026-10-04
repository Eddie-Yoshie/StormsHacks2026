import { defineStore } from 'pinia';
import { computed, ref } from 'vue';
import type { Camera } from '../types/camera';
import { createCameraProvider } from '../services/cameraProvider';
import { setActiveDevice } from '../services/api';
import { createPoller } from '../lib/poll';

export const useCamerasStore = defineStore('cameras', () => {
  const cameras = ref<Camera[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const activeCameraId = ref<string | null>(null);

  async function fetchCameras(): Promise<void> {
    try {
      const result = await createCameraProvider().listCameras();
      cameras.value = result.cameras;
      const ids = result.cameras.map((cam) => cam.id);
      if (activeCameraId.value === null || !ids.includes(activeCameraId.value)) {
        // Keep the user's pick across refreshes; otherwise follow the backend's active device.
        activeCameraId.value = ids.includes(result.activeDevice) ? result.activeDevice : (ids[0] ?? null);
      }
      error.value = null;
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e);
    } finally {
      loading.value = false;
    }
  }

  // Flags (noise, raised alerts) only reach the dashboard through /devices/state.
  const poller = createPoller(fetchCameras, 2000);

  function startPolling(): void {
    if (cameras.value.length === 0) {
      loading.value = true;
    }
    poller.start();
  }

  function selectCamera(id: string): void {
    activeCameraId.value = id;
    setActiveDevice(id).catch((e: unknown) => console.warn('Could not set active device', e));
  }

  function removeCamera(id: string): void {
    cameras.value = cameras.value.filter(cam => cam.id !== id);
    if (activeCameraId.value === id) {
      activeCameraId.value = cameras.value[0]?.id ?? null;
    }
  }

  function setCameraActiveFlags(id: string, activeFlags: boolean[]): void {
    const camera = cameras.value.find(cam => cam.id === id);
    if (camera) {
      camera.activeFlags = activeFlags;
    }
  }

  function setCameraNoiseEnabled(id: string, enabled: boolean): void {
    const camera = cameras.value.find(cam => cam.id === id);
    if (camera) {
      camera.noiseEnabled = enabled;
    }
  }

  const activeCamera = computed<Camera | null>(() => cameras.value.find(cam => cam.id === activeCameraId.value) ?? null);

  return {
    cameras,
    loading,
    error,
    fetchCameras,
    startPolling,
    stopPolling: poller.stop,
    selectCamera,
    removeCamera,
    setCameraActiveFlags,
    setCameraNoiseEnabled,
    activeCamera,
  };
});
