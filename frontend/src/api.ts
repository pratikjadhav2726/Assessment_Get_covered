import type { ScanResponse } from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

type ScanOptions = {
  debug?: boolean;
  signal?: AbortSignal;
};

export async function scanUrl(url: string, options: ScanOptions = {}): Promise<ScanResponse> {
  const params = new URLSearchParams();
  if (options.debug) {
    params.set("debug", "true");
  }

  const query = params.toString();
  const endpoint = `${API_BASE_URL}/api/scan${query ? `?${query}` : ""}`;

  const response = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
    signal: options.signal,
  });

  if (!response.ok) {
    const payload = await safeJson(response);
    const detail = payload?.detail ?? `Request failed with status ${response.status}`;
    throw new Error(typeof detail === "string" ? detail : "Request failed.");
  }

  return (await response.json()) as ScanResponse;
}

async function safeJson(response: Response): Promise<Record<string, unknown> | null> {
  try {
    return (await response.json()) as Record<string, unknown>;
  } catch {
    return null;
  }
}
