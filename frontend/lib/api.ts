import type { DemoSnapshot } from "./types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  details: unknown;

  constructor(status: number, message: string, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

function detailText(details: unknown, fallback: string) {
  if (!Array.isArray(details) || details.length === 0) return fallback;
  return details
    .map((item) => {
      if (!item || typeof item !== "object") return String(item);
      const record = item as { loc?: unknown[]; msg?: string };
      const loc = Array.isArray(record.loc)
        ? record.loc.filter((part) => part !== "body").join(".")
        : "";
      return loc && record.msg ? `${loc}: ${record.msg}` : record.msg || fallback;
    })
    .join(" ");
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers || {}),
      },
    });
  } catch {
    throw new ApiError(
      0,
      `Could not reach the API at ${API_URL}. Start the backend, or load the labeled demo snapshot.`,
    );
  }
  const text = await response.text();
  let body: { error?: { message?: string; details?: unknown } } | null = null;
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = null;
    }
  }
  if (!response.ok) {
    const message = body?.error?.message || `Request failed (${response.status}).`;
    throw new ApiError(response.status, detailText(body?.error?.details, message), body?.error?.details);
  }
  return body as T;
}

let demoRequest: Promise<DemoSnapshot> | null = null;

export function loadDemoSnapshot() {
  if (!demoRequest) {
    demoRequest = fetch("/demo-snapshot.json")
      .then(async (response) => {
        if (!response.ok) {
          throw new ApiError(response.status, "The demo snapshot file is missing from the frontend.");
        }
        return (await response.json()) as DemoSnapshot;
      })
      .catch((error) => {
        demoRequest = null;
        throw error;
      });
  }
  return demoRequest;
}
