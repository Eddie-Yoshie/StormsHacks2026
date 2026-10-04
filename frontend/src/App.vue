<script setup lang="ts">
import { computed, h, onMounted, ref } from 'vue';
import { storeToRefs } from 'pinia';
import { NButton, type FormInst } from 'naive-ui';
import { useCamerasStore } from './stores/cameras';
import AlertNotifier from './components/AlertNotifier.vue';
import CameraCard from './components/CameraCard.vue';

const store = useCamerasStore();
const { cameras, loading, error, activeCamera } = storeToRefs(store);

onMounted(() => {
  void store.fetchCameras();
});

const menuOptions = computed(() =>
  cameras.value.map(camera => ({
    key: camera.id,
    label: () =>
      h('div', { class: 'menu-row' }, [
        h('span', camera.name),
        h(
          NButton,
          {
            size: 'tiny',
            quaternary: true,
            type: 'error',
            onClick: async (e: MouseEvent) => {
              e.stopPropagation();
              removing.value = true;
              try {
                const res = await fetch(`${apiBaseUrl}/devices/${camera.name}`, {
                  method: 'DELETE',
                  headers: { 'Content-Type': 'application/json' },
                });
                if (!res.ok) {
                  const detail = await res.text();
                  throw new Error(`Failed to remove camera (${res.status}): ${detail}`);
                }
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

const apiBaseUrl: string = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

const formValue = ref({
  rtspURL: '',
  name: ''
})

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
    const res = await fetch(`${apiBaseUrl}/devices`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: formValue.value.name,
        rtsp_url: formValue.value.rtspURL,
      }),
    });
    if (!res.ok) {
      const detail = await res.text();
      throw new Error(`Failed to add camera (${res.status}): ${detail}`);
    }
    store.addCamera(formValue.value.name);
    formValue.value = { rtspURL: '', name: '' };
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
        </n-layout-sider>
        <n-layout-content style="padding: 24px">
          <n-spin :show="loading">
            <n-alert v-if="error" type="error" title="Failed to load cameras" :bordered="false">
              {{ error }}
            </n-alert>

            <div v-else>
              <CameraCard v-if="activeCamera" :key="activeCamera.id" :camera="activeCamera" style="max-width: 90%" />
              <n-empty v-else description="No cameras configured" />
            </div>

            <!-- <n-dropdown :options="options" @select="handleSelect">
              <n-button>My Menu</n-button>
            </n-dropdown> -->
          </n-spin>
        </n-layout-content>
        <n-layout-sider style="border-left: 1px solid rgb(239, 239, 245);" :native-scrollbar="false">
          <n-menu :value="activeCamera" :options="menuOptions"
            @update:value="(key: string) => store.selectCamera(key)" />
          <n-button @click="showModal = true">Add Camera</n-button>
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
      </n-layout>
    </n-layout>
  </n-config-provider>
</template>
