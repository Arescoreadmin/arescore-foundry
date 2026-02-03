"use server";

const UI_API_BASE = process.env.NEXT_PUBLIC_UI_API_BASE ?? "http://localhost:8090";
const DEFAULT_TENANT_ID = process.env.NEXT_PUBLIC_TENANT_ID ?? "11111111-1111-1111-1111-111111111111";

type FetchOptions = {
  scopes: string[];
  method?: "GET" | "POST";
};

export async function fetchUi<T>(path: string, options: FetchOptions): Promise<T> {
  const response = await fetch(`${UI_API_BASE}${path}`, {
    method: options.method ?? "GET",
    headers: {
      "X-Tenant-ID": DEFAULT_TENANT_ID,
      "X-Scopes": options.scopes.join(" "),
      "X-Subject": "ui-demo",
      "X-Request-ID": "ui-demo-request",
    },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`UI API request failed: ${response.status}`);
  }

  return (await response.json()) as T;
}
