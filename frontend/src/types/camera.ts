export interface Camera {
  /** MediaMTX path name — also used to derive the WHEP URL. */
  id: string;
  /** Human-readable display name. */
  name: string;
  description?: string;
}
