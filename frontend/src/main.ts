import { createApp } from 'vue';
import { createPinia } from 'pinia';
import {
  create,
  NAlert,
  NButton,
  NCard,
  NConfigProvider,
  NEmpty,
  NGi,
  NGrid,
  NH2,
  NH4,
  NLayout,
  NLayoutContent,
  NLayoutHeader,
  NSpace,
  NSpin,
  NTag,
  NDropdown,
  NLayoutSider,
  NMenu,
  NModal,
  NForm,
  NInput,
  NFormItem,
  NNotificationProvider,
} from 'naive-ui';
import App from './App.vue';

const naive = create({
  components: [
    NAlert,
    NButton,
    NCard,
    NConfigProvider,
    NEmpty,
    NGi,
    NGrid,
    NH2,
    NH4,
    NLayout,
    NLayoutContent,
    NLayoutHeader,
    NSpace,
    NSpin,
    NTag,
    NDropdown,
    NLayoutSider,
    NMenu,
    NModal,
    NForm,
    NInput,
    NFormItem,
    NNotificationProvider,
  ],
});

const app = createApp(App);
app.use(createPinia());
app.use(naive);
app.mount('#app');
