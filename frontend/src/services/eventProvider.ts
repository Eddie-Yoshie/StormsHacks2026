import type { Event } from '../types/event';

/**
 * Provider seam for the event list. Fetches events from the backend
 * events API and maps the snake_case response into the frontend Event shape.
 */
export interface EventProvider {
  listEvents(): Promise<Event[]>;
}

interface EventResponse {
  id: number;
  camera_id: string;
  timestamp: string;
  event_type: string;
}

export class BackendEventProvider implements EventProvider {
  private readonly baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  async listEvents(): Promise<Event[]> {
    const res = await fetch(`${this.baseUrl}/events`);
    if (!res.ok) {
      throw new Error(`Failed to load events (${res.status})`);
    }
    const data = (await res.json()) as EventResponse[];
    return data.map((event) => ({
      id: event.id,
      cameraId: event.camera_id,
      timestamp: event.timestamp,
      eventType: event.event_type,
    }));
  }
}

export function createEventProvider(): EventProvider {
  const baseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
  return new BackendEventProvider(baseUrl);
}
