<script setup lang="ts">
import { onMounted } from 'vue';
import { storeToRefs } from 'pinia';
import { useCamerasStore } from '../stores/cameras';
import CameraCard from './CameraCard.vue';

const store = useCamerasStore();
const { cameras, loading, error } = storeToRefs(store);

onMounted(() => {
  void store.fetchCameras();
});
</script>

<template>
  <n-spin :show="loading">
    <n-alert v-if="error" type="error" title="Failed to load cameras" :bordered="false">
      {{ error }}
    </n-alert>

    <n-empty v-else-if="cameras.length === 0" description="No cameras configured" />

    <n-grid v-else cols="1 s:2 l:3" x-gap="16" y-gap="16" responsive="screen">
      <n-gi v-for="camera in cameras" :key="camera.id">
        <CameraCard :camera="camera" />
      </n-gi>
    </n-grid>
  </n-spin>
</template>
