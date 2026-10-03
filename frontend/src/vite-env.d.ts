/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_MEDIAMTX_BASE_URL?: string;
  readonly VITE_CAMERA_IDS?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
