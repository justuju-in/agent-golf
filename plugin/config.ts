export const DEFAULT_API_ORIGIN = "https://agent-golf.csbasics.in";

export function getApiOrigin(baseUrl: string | undefined): string {
  if (!baseUrl?.trim()) throw new Error("missing-origin");
  const url = new URL(baseUrl.trim());
  const loopback = url.hostname === "localhost" || url.hostname === "127.0.0.1" || url.hostname === "[::1]";
  if (
    url.username || url.password || url.search || url.hash || url.pathname !== "/" ||
    (url.protocol !== "https:" && !(url.protocol === "http:" && loopback))
  ) {
    throw new Error("invalid-origin");
  }
  return url.origin;
}

export function resolveApiOrigin(
  override?: string,
  environment: Record<string, string | undefined> = process.env,
): string {
  // Only an absent override falls back. An empty/invalid value must not silently
  // send credentials to production when the user intended another server.
  return getApiOrigin(override ?? environment.AGENT_GOLF_API_BASE_URL ?? DEFAULT_API_ORIGIN);
}
