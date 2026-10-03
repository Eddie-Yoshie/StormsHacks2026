// Typed wrapper around MediaMTX's official WebRTC reader (public/vendor/mediamtx-reader.js,
// vendored from https://github.com/bluenviron/mediamtx/blob/main/internal/servers/webrtc/reader.js).
// The reader script defines the global `window.MediaMTXWebRTCReader`; this module
// loads it lazily and exposes a typed factory.

const READER_SRC = '/vendor/mediamtx-reader.js';

export interface MediaMTXReaderOptions {
  url: string;
  user?: string;
  pass?: string;
  token?: string;
  onError?: (err: string) => void;
  onTrack?: (evt: RTCTrackEvent) => void;
  onDataChannel?: (evt: RTCDataChannelEvent) => void;
}

export interface MediaMTXReaderHandle {
  close(): void;
}

declare global {
  interface Window {
    MediaMTXWebRTCReader?: new (options: MediaMTXReaderOptions) => MediaMTXReaderHandle;
  }
}

let scriptLoading: Promise<void> | null = null;

function loadReaderScript(): Promise<void> {
  if (window.MediaMTXWebRTCReader) {
    return Promise.resolve();
  }
  if (scriptLoading) {
    return scriptLoading;
  }
  scriptLoading = new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = READER_SRC;
    script.onload = () => resolve();
    script.onerror = () => {
      scriptLoading = null;
      reject(new Error(`failed to load ${READER_SRC}`));
    };
    document.head.appendChild(script);
  });
  return scriptLoading;
}

/** Create a WHEP reader bound to a MediaMTX stream. */
export async function createReader(options: MediaMTXReaderOptions): Promise<MediaMTXReaderHandle> {
  await loadReaderScript();
  const Reader = window.MediaMTXWebRTCReader;
  if (!Reader) {
    throw new Error('MediaMTXWebRTCReader is unavailable');
  }
  return new Reader(options);
}

/** Derive the WHEP endpoint URL for a camera path. */
export function whepUrl(baseUrl: string, cameraId: string): string {
  return `${baseUrl.replace(/\/+$/, '')}/${encodeURIComponent(cameraId)}/whep`;
}
