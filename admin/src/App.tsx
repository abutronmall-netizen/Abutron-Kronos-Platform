import { FormEvent, useCallback, useEffect, useState } from "react";

import { adminApi, clearToken, getToken, login } from "./api";
import Operations from "./Operations";
import type {
  AdminDashboard,
  AuditEvent,
  BillingPlan,
  Broker,
  Customer,
  License,
  Payment,
  Subscription,
  TradingAccount
} from "./types";

type View = "overview" | "customers" | "accounts" | "licenses" | "billing" | "operations" | "audit";

const EMPTY_DASHBOARD: AdminDashboard = {
  customers: 0,
  active_accounts: 0,
  active_licenses: 0,
  registered_devices: 0,
  queued_notifications: 0
};

function formatDate(value: string | null): string {
  if (!value) return "—";
  return new Intl.DateTimeFormat("en-ZA", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value));
}

function money(amountMinor: number, currency: string): string {
  return new Intl.NumberFormat("en-ZA", {
    style: "currency",
    currency
  }).format(amountMinor / 100);
}

function Badge({ value }: { value: string | boolean }) {
  const text = typeof value === "boolean" ? (value ? "Yes" : "No") : value;
  const normalized = String(text).toLowerCase();
  const tone =
    normalized.includes("active") || normalized === "yes" || normalized.includes("paid")
      ? "good"
      : normalized.includes("pending") || normalized.includes("queued")
        ? "warn"
        : normalized.includes("suspend") ||
            normalized.includes("fail") ||
            normalized.includes("revoke")
          ? "bad"
          : "neutral";

  return <span className={`badge badge-${tone}`}>{text}</span>;
}

export default function App() {
  const [authenticated, setAuthenticated] = useState(Boolean(getToken()));
  const [view, setView] = useState<View>("overview");
  const [dashboard, setDashboard] = useState<AdminDashboard>(EMPTY_DASHBOARD);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [accounts, setAccounts] = useState<TradingAccount[]>([]);
  const [licenses, setLicenses] = useState<License[]>([]);
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [audit, setAudit] = useState<AuditEvent[]>([]);
  const [brokers, setBrokers] = useState<Broker[]>([]);
  const [plans, setPlans] = useState<BillingPlan[]>([]);
  const [busy, setBusy] = useState(authenticated);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const me = await adminApi.me();
      if (me.role !== "admin") {
        throw new Error("Administrator role required.");
      }

      const [nextDashboard, nextCustomers, nextAccounts, nextLicenses, nextSubscriptions, nextPayments, nextAudit, nextBrokers, nextPlans] =
        await Promise.all([
          adminApi.dashboard(),
          adminApi.customers(),
          adminApi.accounts(),
          adminApi.licenses(),
          adminApi.subscriptions(),
          adminApi.payments(),
          adminApi.audit(),
          adminApi.brokers(),
          adminApi.billingPlans()
        ]);

      setDashboard(nextDashboard);
      setCustomers(nextCustomers);
      setAccounts(nextAccounts);
      setLicenses(nextLicenses);
      setSubscriptions(nextSubscriptions);
      setPayments(nextPayments);
      setAudit(nextAudit);
      setBrokers(nextBrokers);
      setPlans(nextPlans);
      setAuthenticated(true);
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "Unable to load admin data.";
      setError(message);
      if (!getToken()) setAuthenticated(false);
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    if (authenticated) void load();
  }, [authenticated, load]);

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError(null);

    try {
      await login(String(form.get("email") ?? ""), String(form.get("password") ?? ""));
      setAuthenticated(true);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Login failed.");
      setBusy(false);
    }
  }

  function logout() {
    clearToken();
    setAuthenticated(false);
    setDashboard(EMPTY_DASHBOARD);
  }

  async function changeLicenseStatus(id: string, status: string) {
    setBusy(true);
    setError(null);
    try {
      await adminApi.updateLicense(id, status);
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to update license.");
      setBusy(false);
    }
  }

  async function confirmPayment(id: string) {
    setBusy(true);
    setError(null);
    try {
      await adminApi.confirmSubscriptionPayment(id);
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to confirm payment.");
      setBusy(false);
    }
  }

  if (!authenticated) {
    return (
      <main className="login-shell">
        <section className="login-panel">
          <div className="brand-mark">A</div>
          <p className="eyebrow">ABUTRON CONTROL PLANE</p>
          <h1>Administrator sign in</h1>
          <p className="muted">
            Secure access to customers, trading accounts, licensing, billing and audit activity.
          </p>
          <form onSubmit={handleLogin}>
            <label>
              Email
              <input name="email" type="email" autoComplete="username" required />
            </label>
            <label>
              Password
              <input name="password" type="password" autoComplete="current-password" required />
            </label>
            {error && <div className="error-box">{error}</div>}
            <button className="primary-button" type="submit" disabled={busy}>
              {busy ? "Signing in…" : "Sign in"}
            </button>
          </form>
        </section>
      </main>
    );
  }

  const nav: Array<[View, string]> = [
    ["overview", "Overview"],
    ["customers", "Customers"],
    ["accounts", "Trading accounts"],
    ["licenses", "Licenses"],
    ["billing", "Billing"],
    ["operations", "Operations"],
    ["audit", "Audit trail"]
  ];

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div>
          <div className="sidebar-brand">
            <div className="brand-mark small">A</div>
            <div>
              <strong>Abutron</strong>
              <span>Admin v2.44</span>
            </div>
          </div>
          <nav>
            {nav.map(([key, label]) => (
              <button
                className={view === key ? "nav-button active" : "nav-button"}
                key={key}
                onClick={() => setView(key)}
              >
                {label}
              </button>
            ))}
          </nav>
        </div>
        <button className="logout-button" onClick={logout}>Sign out</button>
      </aside>

      <main className="content">
        <header className="topbar">
          <div>
            <p className="eyebrow">PRODUCTION CONTROL</p>
            <h1>{nav.find(([key]) => key === view)?.[1]}</h1>
          </div>
          <div className="topbar-actions">
            <span className={busy ? "live-dot busy" : "live-dot"} />
            <span>{busy ? "Syncing" : "Live"}</span>
            <button className="secondary-button" onClick={() => void load()} disabled={busy}>
              Refresh
            </button>
          </div>
        </header>

        {error && <div className="error-box inline">{error}</div>}

        {view === "overview" && (
          <>
            <section className="stat-grid">
              <article className="stat-card"><span>Customers</span><strong>{dashboard.customers}</strong></article>
              <article className="stat-card"><span>Active accounts</span><strong>{dashboard.active_accounts}</strong></article>
              <article className="stat-card"><span>Active licenses</span><strong>{dashboard.active_licenses}</strong></article>
              <article className="stat-card"><span>Registered devices</span><strong>{dashboard.registered_devices}</strong></article>
              <article className="stat-card"><span>Queued notifications</span><strong>{dashboard.queued_notifications}</strong></article>
            </section>
            <section className="panel">
              <div className="panel-heading"><div><p className="eyebrow">SYSTEM SNAPSHOT</p><h2>Control-plane status</h2></div></div>
              <div className="health-grid">
                <div><span>Authentication</span><Badge value="active" /></div>
                <div><span>Licensing</span><Badge value="active" /></div>
                <div><span>Billing records</span><strong>{subscriptions.length}</strong></div>
                <div><span>Payments</span><strong>{payments.length}</strong></div>
                <div><span>Audit events</span><strong>{audit.length}</strong></div>
              </div>
            </section>
          </>
        )}

        {view === "customers" && (
          <section className="panel table-panel">
            <div className="panel-heading"><h2>Customers</h2><span>{customers.length} records</span></div>
            <div className="table-scroll"><table><thead><tr><th>Name</th><th>Email</th><th>Phone</th><th>Referral</th><th>Created</th></tr></thead>
              <tbody>{customers.map((customer) => <tr key={customer.id}><td>{customer.full_name}</td><td>{customer.email}</td><td>{customer.phone ?? "—"}</td><td><Badge value={customer.broker_referral_verified} /></td><td>{formatDate(customer.created_at)}</td></tr>)}</tbody>
            </table></div>
          </section>
        )}

        {view === "accounts" && (
          <section className="panel table-panel">
            <div className="panel-heading"><h2>Trading accounts</h2><span>{accounts.length} records</span></div>
            <div className="table-scroll"><table><thead><tr><th>Login</th><th>Server</th><th>Equity</th><th>Bot</th><th>Status</th><th>Last sync</th></tr></thead>
              <tbody>{accounts.map((account) => <tr key={account.id}><td>{account.broker_login}</td><td>{account.server_name ?? "—"}</td><td>{account.equity_usd} {account.currency}</td><td>{account.bot_tier}</td><td><Badge value={account.status} /></td><td>{formatDate(account.last_synced_at)}</td></tr>)}</tbody>
            </table></div>
          </section>
        )}

        {view === "licenses" && (
          <section className="panel table-panel">
            <div className="panel-heading"><h2>Licenses</h2><span>{licenses.length} records</span></div>
            <div className="table-scroll"><table><thead><tr><th>Product</th><th>Status</th><th>Starts</th><th>Expires</th><th>Control</th></tr></thead>
              <tbody>{licenses.map((license) => <tr key={license.id}><td>{license.product}</td><td><Badge value={license.status} /></td><td>{formatDate(license.starts_at)}</td><td>{formatDate(license.expires_at)}</td><td className="actions-cell">
                <button className="table-button" disabled={busy || license.status === "active"} onClick={() => void changeLicenseStatus(license.id, "active")}>Activate</button>
                <button className="table-button danger" disabled={busy || license.status === "suspended"} onClick={() => void changeLicenseStatus(license.id, "suspended")}>Suspend</button>
              </td></tr>)}</tbody>
            </table></div>
          </section>
        )}

        {view === "billing" && (
          <div className="stack">
            <section className="panel table-panel">
              <div className="panel-heading"><h2>Subscriptions</h2><span>{subscriptions.length} records</span></div>
              <div className="table-scroll"><table><thead><tr><th>Provider</th><th>Status</th><th>Amount</th><th>Discount</th><th>Created</th><th>Control</th></tr></thead>
                <tbody>{subscriptions.map((subscription) => <tr key={subscription.id}><td>{subscription.provider}</td><td><Badge value={subscription.status} /></td><td>{money(subscription.amount_minor, subscription.currency)}</td><td>{subscription.discount_percent}%</td><td>{formatDate(subscription.created_at)}</td><td><button className="table-button" disabled={busy || subscription.status !== "pending"} onClick={() => void confirmPayment(subscription.id)}>Mark paid</button></td></tr>)}</tbody>
              </table></div>
            </section>
            <section className="panel table-panel">
              <div className="panel-heading"><h2>Payments</h2><span>{payments.length} records</span></div>
              <div className="table-scroll"><table><thead><tr><th>Provider</th><th>Event</th><th>Status</th><th>Amount</th><th>Paid</th></tr></thead>
                <tbody>{payments.map((payment) => <tr key={payment.id}><td>{payment.provider}</td><td>{payment.provider_event_id}</td><td><Badge value={payment.status} /></td><td>{money(payment.amount_minor, payment.currency)}</td><td>{formatDate(payment.paid_at)}</td></tr>)}</tbody>
              </table></div>
            </section>
          </div>
        )}

        {view === "operations" && (
          <Operations customers={customers} brokers={brokers} plans={plans} onChanged={load} />
        )}

        {view === "audit" && (
          <section className="panel table-panel">
            <div className="panel-heading"><h2>Audit trail</h2><span>{audit.length} events</span></div>
            <div className="table-scroll"><table><thead><tr><th>Action</th><th>Entity</th><th>Entity ID</th><th>Actor</th><th>Timestamp</th></tr></thead>
              <tbody>{audit.map((event) => <tr key={event.id}><td>{event.action}</td><td>{event.entity_type}</td><td className="mono">{event.entity_id ?? "—"}</td><td className="mono">{event.actor_customer_id ?? "system"}</td><td>{formatDate(event.created_at)}</td></tr>)}</tbody>
            </table></div>
          </section>
        )}
      </main>
    </div>
  );
}
