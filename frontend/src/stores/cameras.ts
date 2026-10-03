import { defineStore } from 'pinia';
import { ref } from 'vue';
import type { Camera } from '../types/camera';
import { createCameraProvider } from '../services/cameraProvider';

export const useCamerasStore = defineStore('cameras', () => {
  const cameras = ref<Camera[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function fetchCameras(): Promise<void> {
    loading.value = true;
    error.value = null;
    try {
      cameras.value = await createCameraProvider().listCameras();
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e);
    } finally {
      loading.value = false;
    }
  }

  return { cameras, loading, error, fetchCameras };
});
