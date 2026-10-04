<script setup lang="ts">
import { computed, ref, useTemplateRef } from 'vue';
import { useCameraStream, type StreamStatus } from '../composables/useCameraStream';
import { describeAlert, useFallEvents } from '../composables/useFallEvents';
import { useCamerasStore } from '../stores/cameras';
import { setActiveFlags } from '../services/api';
import {
  BATHROOM_ACTIVE,
  DEAD_ACTIVE,
  DETECTOR_LABELS,
  FALL_ACTIVE,
  FIRST_VISION_FLAG,
  NOISE_FLAG,
  type Camera,
} from '../types/camera';

const props = defineProps<{ camera: Camera }>();
const store = useCamerasStore();

const baseUrl: string = import.meta.env.VITE_MEDIAMTX_BASE_URL ?? 'http://localhost:8889';

const videoEl = useTemplateRef<HTMLVideoElement>('video');
const muted = ref(true);
const { status, errorMessage, reconnect } = useCameraStream(props.camera.id, videoEl, baseUrl);
const { falls, dismiss } = useFallEvents();
const fall = computed(() => falls[props.camera.id]);
const fallTime = computed(() => (fall.value ? new Date(fall.value.ts * 1000).toLocaleTimeString() : ''));
const alertText = computed(() => (fall.value ? describeAlert(fall.value) : null));

/** Raised flags from /devices/state; noise only ever shows up here. */
const flagBadges = computed(() => {
  const flags = props.camera.flags;
  const badges: { label: string; type: 'error' | 'warning' }[] = [];
  if (flags[NOISE_FLAG]) badges.push({ label: 'Loud noise', type: 'warning' });
  if (flags[FIRST_VISION_FLAG + FALL_ACTIVE]) badges.push({ label: 'Fall', type: 'error' });
  if (flags[FIRST_VISION_FLAG + DEAD_ACTIVE]) badges.push({ label: 'No movement', type: 'error' });
  if (flags[FIRST_VISION_FLAG + BATHROOM_ACTIVE]) badges.push({ label: 'Bathroom', type: 'warning' });
  return badges;
});

// Detector toggles recreate the vision container, so they stay locked until the backend answers.
// The pending value is held locally so a state poll mid-request doesn't flip the switch back.
const pendingDetectors = ref<boolean[] | null>(null);
const savingDetectors = computed(() => pendingDetectors.value !== null);
const detectors = computed(() => pendingDetectors.value ?? props.camera.activeFlags);
const detectorError = ref<string | null>(null);

async function toggleDetector(index: number, on: boolean): Promise<void> {
  const next = [...props.camera.activeFlags];
  next[index] = on;
  pendingDetectors.value = next;
  detectorError.value = null;
  try {
    await setActiveFlags(props.camera.id, next);
    store.setCameraActiveFlags(props.camera.id, next);
  } catch (e) {
    detectorError.value = e instanceof Error ? e.message : String(e);
  } finally {
    pendingDetectors.value = null;
  }
}

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
      <!-- n-alert has no action slot, so the button lives in the body. -->
      <div class="alert-row">
        <span>{{ fallTime }} · {{ alertText.detail }}</span>
        <n-button size="small" @click="dismiss(camera.id)">Dismiss</n-button>
      </div>
    </n-alert>

    <n-alert v-else-if="flagBadges.length" type="warning" :bordered="false" class="fall-alert">
      <div class="alert-row">
        <n-space size="small" align="center">
          <n-tag v-for="badge in flagBadges" :key="badge.label" :type="badge.type" size="small">{{ badge.label }}</n-tag>
        </n-space>
        <n-button size="small" @click="dismiss(camera.id)">Acknowledge</n-button>
      </div>
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

    <div class="detectors">
      <span class="detectors__label">Detectors</span>
      <n-space size="medium" align="center">
        <label v-for="(label, i) in DETECTOR_LABELS" :key="label" class="detector">
          <n-switch size="small" :value="detectors[i]" :disabled="savingDetectors"
            @update:value="(on: boolean) => toggleDetector(i, on)" />
          {{ label }}
        </label>
        <n-spin v-if="savingDetectors" size="small" />
      </n-space>
    </div>
    <n-alert v-if="detectorError" type="error" size="small" class="error" :bordered="false" closable
      @close="detectorError = null">
      {{ detectorError }}
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

.alert-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.error {
  margin-top: 8px;
}

.detectors {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
}

.detectors__label {
  font-weight: 500;
}

.detector {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}
</style>
