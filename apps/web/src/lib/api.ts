import type { components } from "@citizen/api-client";
export type AssistantConfig = components["schemas"]["AssistantConfig"];
export type AdminView = components["schemas"]["AdminAssistantView"];
export type TurnView = components["schemas"]["TurnView"];
export type SessionView = components["schemas"]["SessionView"];
export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public status: number,
  ) {
    super(message);
  }
}
export async function api<T>(
  path: string,
  options: RequestInit = {},
  csrf?: string,
  token?: string,
): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    ...options,
    credentials: "same-origin",
    cache: "no-store",
    headers: {
      ...(options.body instanceof FormData
        ? {}
        : { "Content-Type": "application/json" }),
      ...(csrf ? { "X-CSRF-Token": csrf } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });
  const body = await response.json();
  if (!response.ok)
    throw new ApiError(
      body.error?.code ?? "REQUEST_FAILED",
      body.error?.message ?? "Không thể kết nối hệ thống.",
      response.status,
    );
  return body as T;
}
export function localDate(value: string): string {
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "Asia/Ho_Chi_Minh",
  }).format(new Date(value));
}
