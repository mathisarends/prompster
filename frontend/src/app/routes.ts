export const routes = {
  landing: "/",
  new: "/new",
  library: "/decks",
  settings: "/settings",
} as const;
export const chatPath = (id: string) => `/chat/${encodeURIComponent(id)}`;
export function sessionIdFromPath(path: string): string | null {
  const match = /^\/chat\/([^/]+)\/?$/.exec(path);
  if (!match) {
    return null;
  }
  try {
    return decodeURIComponent(match[1]);
  } catch {
    return null;
  }
}
