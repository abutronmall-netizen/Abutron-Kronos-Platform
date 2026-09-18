import type {
  AdminDashboard,
  AuditEvent,
  Customer,
  License,
  Payment,
  Subscription,
  TokenResponse,
  TradingAccount
} from "./types";

const API_BASE = import.meta.env.VITE_ABUTRON_API_URL ?? "/api/v1";
const TOKEN_KEY = "abutron_admin_access_token";

export function getToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY);
}

export function clearToken(): void {
  sessionStorage.removeItem(TOKEN_KEY);
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");

  const token = getToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (response.status === 401) {
    clearToken();
  }

  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      detail = body.detail ?? detail;
    } catch {
      // Keep the status fallback when the response body is not JSON.
    }
    throw new Error(detail);
  }

  return (await response.json()) as T;
}

export async function login(email: string, password: string): Promise<void> {
  const token = await request<TokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password })
  });
  sessionStorage.setItem(TOKEN_KEY, token.access_token);

  const customer = await request<Customer>("/me");
  if (customer.role !== "admin") {
    clearToken();
    throw new Error("This account does not have administrator access.");
  }
}

export const adminApi = {
  me: () => request<Customer>("/me"),
  dashboard: () => request<AdminDashboard>("/admin/dashboard"),
  customers: () => request<Customer[]>("/admin/customers"),
  accounts: () => request<TradingAccount[]>("/admin/accounts"),
  licenses: () => request<License[]>("/admin/licenses"),
  subscriptions: () => request<Subscription[]>("/admin/subscriptions"),
  payments: () => request<Payment[]>("/admin/payments"),
  audit: () => request<AuditEvent[]>("/admin/audit-events")
};
