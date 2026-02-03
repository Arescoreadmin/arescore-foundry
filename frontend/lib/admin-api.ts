"use server";

const ADMIN_API_BASE = process.env.NEXT_PUBLIC_ADMIN_API_BASE ?? "http://localhost:8091";
const DEFAULT_TENANT_ID = process.env.NEXT_PUBLIC_TENANT_ID ?? "11111111-1111-1111-1111-111111111111";

type FetchOptions = {
  scopes: string[];
  method?: "GET" | "POST";
  body?: object;
};

export async function fetchAdmin<T>(path: string, options: FetchOptions): Promise<T> {
  const response = await fetch(`${ADMIN_API_BASE}${path}`, {
    method: options.method ?? "GET",
    headers: {
      "Content-Type": "application/json",
      "X-Tenant-ID": DEFAULT_TENANT_ID,
      "X-Scopes": options.scopes.join(" "),
      "X-Subject": "admin-demo",
      "X-Request-ID": "admin-demo-request",
      "X-CSRF-Token": "admin-demo-csrf",
    },
    body: options.body ? JSON.stringify(options.body) : undefined,
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Admin API request failed: ${response.status}`);
  }

  return (await response.json()) as T;
}
