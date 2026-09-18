import type {
  AdminDashboard,
  BillingPlan,
  Broker,
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
  audit: () => request<AuditEvent[]>("/admin/audit-events"),
  brokers: () => request<Broker[]>("/brokers"),
  billingPlans: () => request<BillingPlan[]>("/billing/plans"),
  createBroker: (payload: {slug:string;display_name:string;adapter_key:string;api_base_url?:string|null}) =>
    request<Broker>("/admin/brokers", {method:"POST", body:JSON.stringify(payload)}),
  verifyReferral: (customerId:string, verified:boolean, broker_slug?:string|null) =>
    request<Customer>(`/admin/customers/${customerId}/referral`, {method:"PUT", body:JSON.stringify({verified,broker_slug:verified?broker_slug:null})}),
  queueNotification: (payload:{customer_id:string;title:string;body:string;data?:Record<string,unknown>}) =>
    request("/admin/notifications", {method:"POST", body:JSON.stringify({...payload,data:payload.data??{}})}),
  createBillingPlan: (payload:{code:string;display_name:string;product:string;currency:string;price_minor:number;broker_discount_percent:number}) =>
    request<BillingPlan>("/admin/billing/plans", {method:"POST", body:JSON.stringify(payload)}),
  confirmSubscriptionPayment: (subscriptionId:string, reference?:string) =>
    request<Payment>(`/admin/subscriptions/${subscriptionId}/confirm-payment`, {method:"POST", body:JSON.stringify({provider:"manual-admin",reference:reference||null})}),
  updateLicense: (licenseId: string, status: string) =>
    request<License>(`/admin/licenses/${licenseId}`, {
      method: "PUT",
      body: JSON.stringify({ status })
    })
};
