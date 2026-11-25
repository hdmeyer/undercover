import { vi } from "vitest";

export type Route = () => Response;

export const json =
  (body: unknown, status = 200): Route =>
  () =>
    new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    });

export const text =
  (body: string): Route =>
  () =>
    new Response(body);

/** Stub fetch. Keys are "METHOD path" or just "path" (GET). Each call gets a fresh response. */
export function stubFetch(routes: Partial<Record<string, Route>>) {
  const mock = vi.fn((path: string, init?: RequestInit) => {
    const key = `${init?.method ?? "GET"} ${path}`;
    const route = routes[key] ?? routes[path];
    if (route === undefined) {
      return Promise.reject(new Error(`No stub for ${key}`));
    }
    return Promise.resolve(route());
  });
  vi.stubGlobal("fetch", mock);
  return mock;
}
