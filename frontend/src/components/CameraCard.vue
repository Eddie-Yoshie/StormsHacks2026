<script setup lang="ts">
import { computed, ref, useTemplateRef } from 'vue';
import { useCameraStream, type StreamStatus } from '../composables/useCameraStream';
import { describeAlert, useFallEvents } from '../composables/useFallEvents';
import type { Camera } from '../types/camera';

const props = defineProps<{ camera: Camera }>();

const baseUrl: string = import.meta.env.VITE_MEDIAMTX_BASE_URL ?? 'http://localhost:8889';

const videoEl = useTemplateRef<HTMLVideoElement>('video');
const muted = ref(true);
const { status, errorMessage, reconnect } = useCameraStream(props.camera.id, videoEl, baseUrl);
const { falls, dismiss } = useFallEvents();
const fall = computed(() => falls[props.camera.id]);
const fallTime = computed(() => (fall.value ? new Date(fall.value.ts * 1000).toLocaleTimeString() : ''));
const alertText = computed(() => (fall.value ? describeAlert(fall.value) : null));

const statusMeta = computed<{ label: string; type: 'default' | 'info' | 'success' | 'error' }>(() => {
  switch (status.value as StreamStatus) {
    case 'connecting':
      return { label: 'Connecting', type: 'info' };
    case 'live':
      return { label: 'Live', type: 'success' };
    case 'error':
      return { label: 'Reconnecting', type: 'error' };
    default:
      return { label: 'Idle', type: 'default' };
  }
});

function toggleMute(): void {
  if (videoEl.value) {
    videoEl.value.muted = !videoEl.value.muted;
    muted.value = videoEl.value.muted;
  }
}

function fullscreen(): void {
  videoEl.value?.requestFullscreen();
}
</script>

<template>
  <n-card :title="camera.name" size="small" :class="{ falling: fall }">
    <template #header-extra>
      <n-space size="small">
        <n-tag v-if="alertText" type="error" size="small">{{ alertText.tag }}</n-tag>
        <n-tag :type="statusMeta.type" size="small" :bordered="false">{{ statusMeta.label }}</n-tag>
      </n-space>
    </template>

    <n-alert v-if="fall && alertText" type="error" :title="alertText.title" class="fall-alert">
      {{ fallTime }} · {{ alertText.detail }}
      <template #action>
        <n-button size="small" @click="dismiss(camera.id)">Dismiss</n-button>
      </template>
    </n-alert>

    <div class="video-wrap">
      <video ref="video" autoplay playsinline :muted="muted" />
      <div v-if="status === 'connecting'" class="overlay">
        <n-spin size="medium" />
      </div>
    </div>

    <n-alert v-if="errorMessage" type="warning" size="small" class="error" :bordered="false">
      {{ errorMessage }}
    </n-alert>

    <template #action>
      <n-space size="small">
        <n-button size="small" secondary @click="toggleMute">
          {{ muted ? 'Unmute' : 'Mute' }}
        </n-button>
        <n-button size="small" secondary @click="fullscreen">Fullscreen</n-button>
        <n-button size="small" secondary @click="reconnect">Reconnect</n-button>
      </n-space>
    </template>
  </n-card>
</template>

<style scoped>
.video-wrap {
  position: relative;
  aspect-ratio: 16 / 9;
  background: #000;
}

video {
  width: 100%;
  height: 100%;
  display: block;
}

.overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.falling {
  outline: 3px solid #d03050;
}

.fall-alert {
  margin-bottom: 8px;
}

.error {
  margin-top: 8px;
}
</style>
