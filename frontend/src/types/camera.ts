export interface Camera {
  /** MediaMTX path name — also used to derive the WHEP URL. */
  id: string;
  /** Human-readable display name. */
  name: string;
  description?: string;
  /** Raised alert flags, indexed by NOISE_FLAG / FIRST_VISION_FLAG + *_ACTIVE. */
  flags: boolean[];
  /** Which detectors the camera's vision container runs, indexed by *_ACTIVE. */
  activeFlags: boolean[];
}

// Mirrors vision/flags.py and backend/routes/devices.py.
export const FALL_ACTIVE = 0;
export const DEAD_ACTIVE = 1;
export const BATHROOM_ACTIVE = 2;
export const DEFAULT_ACTIVE_FLAGS: readonly boolean[] = [true, true, false];
export const DETECTOR_LABELS = ['Fall', 'No movement', 'Bathroom'] as const;

export const NOISE_FLAG = 0;
export const FIRST_VISION_FLAG = 1;
