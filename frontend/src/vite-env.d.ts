/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_MEDIAMTX_BASE_URL?: string;
  readonly VITE_CAMERA_IDS?: string;
  readonly VITE_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
