<script setup lang="ts">
import { computed, h, onMounted, ref } from 'vue';
import { storeToRefs } from 'pinia';
import { NButton } from 'naive-ui';
import { useCamerasStore } from './stores/cameras';
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
            onClick: (e: MouseEvent) => {
              e.stopPropagation();
              store.removeCamera(camera.id);
            }
          },
          { default: () => 'X' }
        )
      ])
  }))
);

const showModal = ref(false)
const formRef = ref(null)

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

const handleSubmit = (e: MouseEvent) => {
  e.preventDefault();
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
    <n-layout style="min-height: 100vh">
      <n-layout-header bordered style="padding: 12px 24px">
        <n-h2 style="margin: 0">Stream Monitor</n-h2>
      </n-layout-header>
      <n-layout position="absolute" style="top: 64px; bottom: 0" has-sider>
        <n-layout-sider :native-scrollbar="false" bordered>
          <n-menu :value="activeCamera" :options="menuOptions"
            @update:value="(key: string) => store.selectCamera(key)" />
        </n-layout-sider>
        <n-layout-content style="padding: 24px">
          <n-spin :show="loading">
            <n-alert v-if="error" type="error" title="Failed to load cameras" :bordered="false">
              {{ error }}
            </n-alert>

            <div v-else>
              <CameraCard v-if="activeCamera" :camera="activeCamera" style="max-width: 90%" />
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
            <n-card style="width: 600px" title="Add New User" :bordered="false" size="huge" role="dialog"
              aria-modal="true">
              <n-form ref="formRef" :model="formValue" :rules="rules">
                <n-form-item label="RTSP URL" path="rtspURL">
                  <n-input v-model:value="formValue.rtspURL" placeholder="Input RTSP URL" />
                </n-form-item>
                <n-form-item label="Name" path="name">
                  <n-input v-model:value="formValue.name" placeholder="Input name" />
                </n-form-item>
              </n-form>

              <template #footer>
                <n-space justify="end">
                  <n-button @click="showModal = false">Cancel</n-button>
                  <n-button type="primary" @click="handleSubmit">Submit</n-button>
                </n-space>
              </template>
            </n-card>
          </n-modal>
        </n-layout-sider>
      </n-layout>
    </n-layout>
  </n-config-provider>
</template>
