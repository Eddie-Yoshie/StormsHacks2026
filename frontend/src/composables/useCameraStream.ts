import { onBeforeUnmount, onMounted, ref, type Ref } from 'vue';
import { createReader, whepUrl, type MediaMTXReaderHandle } from '../lib/mediamtx';

export type StreamStatus = 'idle' | 'connecting' | 'live' | 'error';

/**
 * Binds a MediaMTX WHEP stream to a <video> element.
 * The underlying reader reconnects automatically on failure; this composable
 * only surfaces status and handles teardown on unmount.
 */
export function useCameraStream(
  cameraId: string,
  videoEl: Ref<HTMLVideoElement | null>,
  baseUrl: string,
) {
  const status = ref<StreamStatus>('idle');
  const errorMessage = ref<string | null>(null);
  let reader: MediaMTXReaderHandle | null = null;
  let destroyed = false;

  async function connect(): Promise<void> {
    if (destroyed) {
      return;
    }
    status.value = 'connecting';
    errorMessage.value = null;
    try {
      reader = await createReader({
        url: whepUrl(baseUrl, cameraId),
        onTrack: (evt) => {
          if (videoEl.value) {
            videoEl.value.srcObject = evt.streams[0];
          }
          status.value = 'live';
        },
        onError: (err) => {
          // The reader retries internally; just surface the state.
          status.value = 'error';
          errorMessage.value = err;
        },
      });
    } catch (e) {
      status.value = 'error';
      errorMessage.value = e instanceof Error ? e.message : String(e);
    }
  }

  function reconnect(): void {
    reader?.close();
    reader = null;
    if (videoEl.value) {
      videoEl.value.srcObject = null;
    }
    void connect();
  }

  onMounted(() => {
    void connect();
  });

  onBeforeUnmount(() => {
    destroyed = true;
    reader?.close();
    reader = null;
  });

  return { status, errorMessage, reconnect };
}
