<script setup lang="ts">
import { computed, h, onMounted, onUnmounted, ref } from 'vue';
import { storeToRefs } from 'pinia';
import { NButton, NTag, type FormInst } from 'naive-ui';
import { useCamerasStore } from './stores/cameras';
import { useEventsStore } from './stores/events';
import { addDevice, removeDevice } from './services/api';
import { kindLabel, useFallEvents } from './composables/useFallEvents';
import { DEFAULT_ACTIVE_FLAGS, DETECTOR_LABELS } from './types/camera';
import AlertNotifier from './components/AlertNotifier.vue';
import CameraCard from './components/CameraCard.vue';

const store = useCamerasStore();
const { cameras, loading, error, activeCamera } = storeToRefs(store);

const eventsStore = useEventsStore();
const { events, loading: eventsLoading, error: eventsError } = storeToRefs(eventsStore);

const { onAlert } = useFallEvents();

const formatTimestamp = (timestamp: string): string =>
  new Date(timestamp).toLocaleString();

// Live alerts refresh the history at once; the slower poll is only a fallback.
const unsubscribeAlerts = onAlert(() => void eventsStore.fetchEvents());

onMounted(() => {
  store.startPolling();
  eventsStore.startPolling(5000);
});

onUnmounted(() => {
  store.stopPolling();
  eventsStore.stopPolling();
  unsubscribeAlerts();
});

const menuOptions = computed(() =>
  cameras.value.map(camera => ({
    key: camera.id,
    label: () =>
      h('div', { class: 'menu-row' }, [
        h('span', { class: 'menu-row__name' }, [
          camera.name,
          camera.flags.some(Boolean)
            ? h(NTag, { size: 'tiny', type: 'error', round: true, style: 'margin-left: 6px' }, { default: () => '!' })
            : null,
        ]),
        h(
          NButton,
          {
            size: 'tiny',
            quaternary: true,
            type: 'error',
            onClick: async (e: MouseEvent) => {
              e.stopPropagation();
              removing.value = true;
              removeError.value = null;
              try {
                await removeDevice(camera.id);
                store.removeCamera(camera.id);
              } catch (err) {
                removeError.value = err instanceof Error ? err.message : String(err);
              } finally {
                removing.value = false;
              }
            }
          },
          { default: () => 'X' }
        )
      ])
  }))
);

const showModal = ref(false)
const formRef = ref<FormInst | null>(null)
const submitting = ref(false)
const submitError = ref<string | null>(null)
const removing = ref(false)
const removeError = ref<string | null>(null)

const emptyForm = () => ({
  rtspURL: '',
  name: '',
  activeFlags: [...DEFAULT_ACTIVE_FLAGS],
})

const formValue = ref(emptyForm())

const rules = {
  rtspURL: {
    required: true,
    message: 'Please input a RTSP URL',
    trigger: 'blur'
  },
  name: {
    required: true,
    message: 'Please input a name for the RTSP stream',
    trigger: 'blur'
  }
}

const handleSubmit = async (e: MouseEvent) => {
  e.preventDefault();
  submitError.value = null;
  try {
    await formRef.value?.validate();
  } catch {
    return; // validation errors are shown inline by n-form
  }
  submitting.value = true;
  try {
    const name = formValue.value.name.trim();
    await addDevice(name, formValue.value.rtspURL.trim(), formValue.value.activeFlags);
    await store.fetchCameras();
    store.selectCamera(name);
    formValue.value = emptyForm();
    showModal.value = false;
  } catch (err) {
    submitError.value = err instanceof Error ? err.message : String(err);
  } finally {
    submitting.value = false;
  }
}

// const options = [
//   {
//     label: 'Profile',
//     key: 'profile'
//   },
//   {
//     label: 'Edit Profile',
//     key: 'edit'
//   },
//   {
//     type: 'divider',
//     key: 'd1'
//   },
//   {
//     label: 'Logout',
//     key: 'logout'
//   }
// ]

</script>

<style scoped>
:deep(.menu-row) {
  display: flex;
  justify-content: space-between;
  width: 100%;
}

.event-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.event-row {
  padding: 8px 10px;
  border: 1px solid rgb(239, 239, 245);
  border-radius: 6px;
}

.event-row--selectable {
  cursor: pointer;
}

.event-row--selectable:hover {
  border-color: rgb(208, 48, 80);
}

.event-row__time {
  font-size: 12px;
  color: rgb(118, 124, 130);
}

.event-row__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: 4px;
}
</style>

<template>
  <n-config-provider>
    <n-notification-provider placement="top-right" :max="10">
      <AlertNotifier />
    </n-notification-provider>
    <n-layout style="min-height: 100vh">
      <n-layout-header bordered style="padding: 12px 24px">
        <n-h2 style="margin: 0">Stream Monitor</n-h2>
      </n-layout-header>
      <n-layout position="absolute" style="top: 64px; bottom: 0" has-sider>
        <n-layout-sider :native-scrollbar="false" bordered>
          <n-menu :value="activeCamera?.id" :options="menuOptions"
            @update:value="(key: string) => store.selectCamera(key)" />
          <n-button @click="showModal = true" style="margin-left: 24px;">Add Camera</n-button>
          <n-alert v-if="removeError" type="error" :bordered="false" closable style="margin: 12px"
            @close="removeError = null">
            {{ removeError }}
          </n-alert>
          <n-modal v-model:show="showModal">
            <n-card style="width: 600px" title="Add Camera" :bordered="false" size="huge" role="dialog"
              aria-modal="true">
              <n-form ref="formRef" :model="formValue" :rules="rules">
                <n-form-item label="RTSP URL" path="rtspURL">
                  <n-input v-model:value="formValue.rtspURL" placeholder="Input RTSP URL" />
                </n-form-item>
                <n-form-item label="Name" path="name">
                  <n-input v-model:value="formValue.name" placeholder="Input name" />
                </n-form-item>
                <n-form-item label="Detectors">
                  <n-space>
                    <n-checkbox v-for="(label, i) in DETECTOR_LABELS" :key="label"
                      v-model:checked="formValue.activeFlags[i]">{{ label }}</n-checkbox>
                  </n-space>
                </n-form-item>
              </n-form>

              <n-alert v-if="submitError" type="error" :bordered="false" style="margin-top: 12px">
                {{ submitError }}
              </n-alert>

              <template #footer>
                <n-space justify="end">
                  <n-button @click="showModal = false">Cancel</n-button>
                  <n-button type="primary" :loading="submitting" @click="handleSubmit">Submit</n-button>
                </n-space>
              </template>
            </n-card>
          </n-modal>
        </n-layout-sider>
        <n-layout-content style="padding: 24px">
          <n-spin :show="loading">
            <n-alert v-if="error && cameras.length === 0" type="error" title="Failed to load cameras" :bordered="false">
              {{ error }}
            </n-alert>

            <div v-else>
              <!-- Keep the stream up through a failed refresh; just say the backend is unreachable. -->
              <n-alert v-if="error" type="warning" :bordered="false" style="margin-bottom: 12px; max-width: 90%">
                Lost contact with the backend: {{ error }}
              </n-alert>
              <CameraCard v-if="activeCamera" :key="activeCamera.id" :camera="activeCamera" style="max-width: 90%" />
              <n-empty v-else description="No cameras configured" />
            </div>

            <!-- <n-dropdown :options="options" @select="handleSelect">
              <n-button>My Menu</n-button>
            </n-dropdown> -->
          </n-spin>
        </n-layout-content>
        <n-layout-sider style="border-left: 1px solid rgb(239, 239, 245);" :native-scrollbar="false" content-style="padding: 16px;">
          <n-h4 style="margin: 0 0 12px">Events</n-h4>
          <n-spin :show="eventsLoading">
            <n-alert v-if="eventsError" type="error" :bordered="false">
              {{ eventsError }}
            </n-alert>
            <n-empty v-else-if="events.length === 0" description="No events" />
            <div v-else class="event-list">
              <div v-for="event in events" :key="event.id" class="event-row"
                :class="{ 'event-row--selectable': cameras.some(cam => cam.id === event.cameraId) }"
                @click="cameras.some(cam => cam.id === event.cameraId) && store.selectCamera(event.cameraId)">
                <div class="event-row__time">{{ formatTimestamp(event.timestamp) }}</div>
                <div class="event-row__meta">
                  <span>{{ event.cameraId }}</span>
                  <n-tag size="small" :type="kindLabel(event.eventType).type">{{ kindLabel(event.eventType).tag }}</n-tag>
                </div>
              </div>
            </div>
          </n-spin>
        </n-layout-sider>
      </n-layout>
    </n-layout>
  </n-config-provider>
</template>
