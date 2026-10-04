const LOOPBACK_HOSTS = new Set(['localhost', '127.0.0.1', '[::1]']);

/**
 * Resolve a service base URL for the browser.
 *
 * The dashboard and every service run on the same Docker host, but the page may be opened from
 * another device (e.g. a phone) using the host's LAN IP. In that case a configured loopback URL
 * such as http://localhost:8000 points at the phone itself, so swap in the hostname the page was
 * loaded from. Explicit non-loopback values (and localhost when opened locally) are kept as-is.
 */
export function resolveServiceUrl(configured: string | undefined, port: number): string {
  const fallback = `http://${window.location.hostname}:${port}`;
  if (!configured) return fallback;
  try {
    const url = new URL(configured);
    if (LOOPBACK_HOSTS.has(url.hostname) && !LOOPBACK_HOSTS.has(window.location.hostname)) {
      return `http://${window.location.hostname}:${url.port || port}`;
    }
    return configured;
  } catch {
    return configured;
  }
}
