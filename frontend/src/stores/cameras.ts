import { defineStore } from 'pinia';
import { computed, ref } from 'vue';
import type { Camera } from '../types/camera';
import { createCameraProvider } from '../services/cameraProvider';

export const useCamerasStore = defineStore('cameras', () => {
  const cameras = ref<Camera[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const activeCameraId = ref<string | null>(null);

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

  function selectCamera(id: string): void {
    activeCameraId.value = id;
  }

  function removeCamera(id: string): void {
    cameras.value = cameras.value.filter(cam => cam.id !== id);
    if (activeCameraId.value === id) {
      activeCameraId.value = null;
    }
  }

  function addCamera(name: string): void {
    const id = name.trim();
    if (!id || cameras.value.some(cam => cam.id === id)) {
      return;
    }
    cameras.value = [...cameras.value, { id, name: id }];
  }

  const activeCamera = computed<Camera | null>(() => cameras.value.find(cam => cam.id === activeCameraId.value) ?? null);

  return { cameras, loading, error, fetchCameras, selectCamera, removeCamera, addCamera, activeCamera };
});
