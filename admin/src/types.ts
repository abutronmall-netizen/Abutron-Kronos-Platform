export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface Customer {
  id: string;
  email: string;
  full_name: string;
  phone: string | null;
  role: string;
  is_active: boolean;
  broker_referral_verified: boolean;
  broker_referral_slug: string | null;
  created_at: string;
}

export interface AdminDashboard {
  customers: number;
  active_accounts: number;
  active_licenses: number;
  registered_devices: number;
  queued_notifications: number;
}

export interface TradingAccount {
  id: string;
  broker_login: string;
  server_name: string | null;
  currency: string;
  equity_usd: string;
  bot_tier: string;
  route_reason: string;
  status: string;
  last_synced_at: string | null;
}

export interface License {
  id: string;
  trading_account_id: string;
  product: string;
  status: string;
  starts_at: string | null;
  expires_at: string | null;
}

export interface Subscription {
  id: string;
  customer_id: string;
  license_id: string;
  plan_id: string;
  status: string;
  provider: string;
  provider_reference: string | null;
  amount_minor: number;
  currency: string;
  discount_percent: number;
  starts_at: string | null;
  renews_at: string | null;
  created_at: string;
}

export interface Payment {
  id: string;
  subscription_id: string;
  provider: string;
  provider_event_id: string;
  amount_minor: number;
  currency: string;
  status: string;
  paid_at: string | null;
}

export interface AuditEvent {
  id: string;
  actor_customer_id: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface Broker {
  id: string;
  slug: string;
  display_name: string;
  is_active: boolean;
}

export interface BillingPlan {
  id: string;
  code: string;
  display_name: string;
  product: string;
  currency: string;
  price_minor: number;
  broker_discount_percent: number;
  is_active: boolean;
}
