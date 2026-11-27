export class ApiError extends Error {}

async function send<T>(
  method: string,
  path: string,
  body?: unknown,
): Promise<T> {
  const response = await fetch(path, {
    method,
    headers: body === undefined ? {} : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    const error = (await response.json()) as { detail?: unknown };
    throw new ApiError(
      typeof error.detail === "string"
        ? error.detail
        : `The request failed (${String(response.status)}).`,
    );
  }
  return (await response.json()) as T;
}

export function getJson<T>(path: string): Promise<T> {
  return send<T>("GET", path);
}

export function postJson<T>(path: string, body?: unknown): Promise<T> {
  return send<T>("POST", path, body);
}

export async function getText(path: string): Promise<string> {
  const response = await fetch(path);
  if (!response.ok) {
    throw new ApiError(`The request failed (${String(response.status)}).`);
  }
  return response.text();
}

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Something went wrong.";
}
