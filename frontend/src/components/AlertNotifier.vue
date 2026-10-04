<script setup lang="ts">
import { h, onBeforeUnmount, watch } from 'vue';
import { NButton, NSpace, useNotification, type NotificationReactive } from 'naive-ui';
import { describeAlert, useFallEvents, type FallEvent } from '../composables/useFallEvents';
import { useCamerasStore } from '../stores/cameras';

/**
 * Front-desk alerts: every fall / bathroom timeout pops a notification that stays until a nurse
 * acknowledges it, whichever camera is open. Renders nothing itself; must sit inside
 * <n-notification-provider>.
 */
const notification = useNotification();
const store = useCamerasStore();
const { falls, dismiss, onAlert } = useFallEvents();
const open = new Map<string, NotificationReactive>();

function close(cameraId: string): void {
  open.get(cameraId)?.destroy();
  open.delete(cameraId);
}

function show(event: FallEvent): void {
  close(event.camera_id); // newer alert for the same camera replaces the old one
  const camera = store.cameras.find((cam) => cam.id === event.camera_id);
  const text = describeAlert(event);
  const n = notification.create({
    type: text.type,
    title: `${text.title}: ${camera?.name ?? event.camera_id}`,
    content: text.detail,
    meta: new Date(event.ts * 1000).toLocaleTimeString(),
    duration: 0,
    keepAliveOnHover: true,
    action: () =>
      h(NSpace, { size: 'small' }, () => [
        h(NButton, { size: 'small', onClick: () => store.selectCamera(event.camera_id) }, () => 'View camera'),
        h(NButton, { size: 'small', type: 'error', onClick: () => dismiss(event.camera_id) }, () => 'Acknowledge'),
      ]),
    onClose: () => {
      dismiss(event.camera_id);
    },
  });
  open.set(event.camera_id, n);
}

const unsubscribe = onAlert(show);

// Dismissed from the camera card: drop the matching notification too.
watch(
  () => Object.keys(falls),
  (ids) => {
    for (const id of [...open.keys()]) {
      if (!ids.includes(id)) close(id);
    }
  },
);

onBeforeUnmount(unsubscribe);
</script>

<template>
  <span hidden />
</template>
