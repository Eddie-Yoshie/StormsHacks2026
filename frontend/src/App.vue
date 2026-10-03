<script setup lang="ts">
import CameraGrid from './components/CameraGrid.vue';
</script>

<template>
  <n-config-provider>
    <n-layout style="min-height: 100vh">
      <n-layout-header bordered style="padding: 12px 24px">
        <n-h2 style="margin: 0">Stream Monitor</n-h2>
      </n-layout-header>
      <n-layout-content style="padding: 24px">
        <CameraGrid />
      </n-layout-content>
    </n-layout>
  </n-config-provider>
</template>
