"use client";

import { useEffect, useMemo, useState } from "react";

type DashboardMetrics = {
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  gross_profit: number;
  gross_loss: number;
  net_profit: number;
  average_win: number;
  average_loss: number;
  profit_factor: number;
  expectancy: number;
  balance: number;
  equity: number;
  daily_pnl: number;
  max_drawdown: number;
  max_drawdown_pct: number;
};

type TradeRow = {
  id: number;
  symbol: string;
  side: string;
  net_profit: number;
  strategy_id: string;
  entry_time: string | null;
  r_multiple: number | string;
};

type DashboardResponse = {
  account: { id: number; name: string; currency: string };
  metrics: DashboardMetrics;
  equity_curve: number[];
  trades: TradeRow[];
};

type RiskRuleConfig = {
  initial_balance: number;
  profit_target: number;
  daily_loss_limit: number;
  max_loss: number;
  max_drawdown: number;
  minimum_trading_days: number;
  consistency_requirement: number;
  position_size_limit: number;
  news_restriction: boolean;
  weekend_restriction: boolean;
};

type RiskCheck = {
  key: string;
  label: string;
  status: string;
  actual?: number;
  limit?: number;
  target?: number;
  detail?: string;
};

type RiskResponse = {
  account_id: number;
  rules: RiskRuleConfig | null;
  assessment: {
    status: string;
    daily_net_profit: number;
    total_net_profit: number;
    current_balance: number;
    maximum_drawdown: number;
    checks: RiskCheck[];
  };
};

type StrategyMetrics = {
  strategy_id: string;
  total_trades: number;
  win_rate: number;
  net_profit: number;
  profit_factor: number;
};

type AnalystInsight = {
  key: string;
  severity: string;
  title: string;
  detail: string;
};

type AnalystReport = {
  method: string;
  confidence: string;
  summary: string;
  risk_status: string;
  metrics: {
    total_trades: number;
    win_rate: number;
    net_profit: number;
    expectancy: number;
    profit_factor: number | null;
  };
  insights: AnalystInsight[];
  disclaimer: string;
};

type SyncLogRow = {
  id: number;
  started_at: string;
  ended_at: string | null;
  trades_fetched: number;
  inserted: number;
  updated: number;
  status: string;
};

type AccountOption = {
  id: number;
  name: string;
  currency: string;
  account_type: string;
};

const emptyRiskRules: RiskRuleConfig = {
  initial_balance: 0,
  profit_target: 0,
  daily_loss_limit: 0,
  max_loss: 0,
  max_drawdown: 0,
  minimum_trading_days: 0,
  consistency_requirement: 0,
  position_size_limit: 0,
  news_restriction: false,
  weekend_restriction: false,
};

type RiskNumericKey = {
  [Key in keyof RiskRuleConfig]: RiskRuleConfig[Key] extends number ? Key : never;
}[keyof RiskRuleConfig];

const riskNumericFields: { key: RiskNumericKey; label: string; unit: string; step: string; max?: number }[] = [
  { key: "daily_loss_limit", label: "Daily loss limit", unit: "currency", step: "0.01" },
  { key: "max_loss", label: "Maximum total loss", unit: "currency", step: "0.01" },
  { key: "max_drawdown", label: "Maximum drawdown", unit: "currency", step: "0.01" },
  { key: "profit_target", label: "Profit target", unit: "currency", step: "0.01" },
  { key: "minimum_trading_days", label: "Minimum trading days", unit: "days", step: "1" },
  { key: "consistency_requirement", label: "Maximum best-day share", unit: "%", step: "1", max: 100 },
  { key: "position_size_limit", label: "Maximum position size", unit: "lots", step: "0.01" },
];

const insightStyles: Record<string, string> = {
  critical: "text-rose-300",
  warning: "text-amber-300",
  caution: "text-amber-200",
  positive: "text-emerald-300",
  neutral: "text-slate-300",
};

const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function fetchAccounts(token: string): Promise<AccountOption[]> {
  const response = await fetch(`${apiBase}/api/accounts`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    throw new Error("Unable to load trading accounts");
  }
  return response.json();
}

async function loadTradingData(token: string, accountId: number) {
  const headers = { Authorization: `Bearer ${token}` };
  const dashboardResponse = await fetch(`${apiBase}/api/analytics/dashboard?account_id=${accountId}`, { headers });
  if (!dashboardResponse.ok) {
    throw new Error("Dashboard data request failed");
  }
  const dashboard: DashboardResponse = await dashboardResponse.json();
  const [riskResponse, strategyResponse, analystResponse, syncHistoryResponse] = await Promise.all([
    fetch(`${apiBase}/api/accounts/${dashboard.account.id}/risk`, { headers }),
    fetch(`${apiBase}/api/analytics/strategies?account_id=${dashboard.account.id}`, { headers }),
    fetch(`${apiBase}/api/analytics/analyst?account_id=${dashboard.account.id}`, { headers }),
    fetch(`${apiBase}/api/accounts/${dashboard.account.id}/sync-logs`, { headers }),
  ]);
  if (!riskResponse.ok || !strategyResponse.ok || !analystResponse.ok || !syncHistoryResponse.ok) {
    throw new Error("Account analytics request failed");
  }
  const risk: RiskResponse = await riskResponse.json();
  const strategyData: { strategies: StrategyMetrics[] } = await strategyResponse.json();
  const analyst: AnalystReport = await analystResponse.json();
  const syncLogs: SyncLogRow[] = await syncHistoryResponse.json();
  return { dashboard, risk, strategies: strategyData.strategies, analyst, syncLogs };
}

function formatMoney(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(value);
}

function formatRiskCheck(check: RiskCheck, currency: string) {
  if (check.status === "disabled") return "Disabled";
  if (check.status === "not_evaluable") return "Not evaluable";
  if (check.key === "minimum_trading_days") return `${check.actual ?? 0} / ${check.limit ?? 0} days · ${check.status.replace("_", " ")}`;
  if (check.key === "consistency") return `${(check.actual ?? 0).toFixed(1)}% / ${check.limit ?? 0}% max · ${check.status.replace("_", " ")}`;
  if (check.key === "position_size") return `${(check.actual ?? 0).toFixed(2)} / ${check.limit ?? 0} lots · ${check.status.replace("_", " ")}`;
  if (check.key === "profit_target") return `${formatMoney(check.actual ?? 0)} / ${formatMoney(check.target ?? 0)} · ${check.status.replace("_", " ")}`;
  return `${formatMoney(check.actual ?? 0)} / ${formatMoney(check.limit ?? 0)} ${currency} · ${check.status.replace("_", " ")}`;
}

function formatPercent(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

function formatSignedMoney(value: number) {
  return `${value >= 0 ? "+" : "-"}${formatMoney(Math.abs(value))}`;
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("en-US", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export default function Home() {
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [risk, setRisk] = useState<RiskResponse | null>(null);
  const [riskDraft, setRiskDraft] = useState<RiskRuleConfig>(emptyRiskRules);
  const [strategies, setStrategies] = useState<StrategyMetrics[]>([]);
  const [analyst, setAnalyst] = useState<AnalystReport | null>(null);
  const [syncLogs, setSyncLogs] = useState<SyncLogRow[]>([]);
  const [accounts, setAccounts] = useState<AccountOption[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<number | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [authError, setAuthError] = useState<string | null>(null);
  const [authBusy, setAuthBusy] = useState(false);
  const [accountName, setAccountName] = useState("");
  const [initialBalance, setInitialBalance] = useState("10000");
  const [currency, setCurrency] = useState("USD");
  const [accountError, setAccountError] = useState<string | null>(null);
  const [accountBusy, setAccountBusy] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [importMessage, setImportMessage] = useState<string | null>(null);
  const [riskMessage, setRiskMessage] = useState<string | null>(null);
  const [importing, setImporting] = useState(false);
  const [savingRisk, setSavingRisk] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  function applyTradingData(data: Awaited<ReturnType<typeof loadTradingData>>) {
    setDashboard(data.dashboard);
    setRisk(data.risk);
    setRiskDraft(data.risk.rules ?? emptyRiskRules);
    setStrategies(data.strategies);
    setAnalyst(data.analyst);
    setSyncLogs(data.syncLogs);
  }

  async function startSession(authToken: string, preferredAccountId?: number) {
    const accountOptions = await fetchAccounts(authToken);
    setToken(authToken);
    setAccounts(accountOptions);
    localStorage.setItem("trading-token", authToken);

    if (!accountOptions.length) {
      setDashboard(null);
      setSelectedAccountId(null);
      return;
    }

    const activeAccount = accountOptions.find((account) => account.id === preferredAccountId) ?? accountOptions[0];
    setSelectedAccountId(activeAccount.id);
    applyTradingData(await loadTradingData(authToken, activeAccount.id));
  }

  useEffect(() => {
    const savedToken = localStorage.getItem("trading-token");
    if (!savedToken) {
      queueMicrotask(() => setLoading(false));
      return;
    }
    const sessionToken: string = savedToken;

    async function restoreSession() {
      try {
        const accountOptions = await fetchAccounts(sessionToken);
        setToken(sessionToken);
        setAccounts(accountOptions);
        if (accountOptions.length) {
          const activeAccount = accountOptions[0];
          setSelectedAccountId(activeAccount.id);
          applyTradingData(await loadTradingData(sessionToken, activeAccount.id));
        }
      } catch {
        localStorage.removeItem("trading-token");
        setAuthError("Your session expired. Please sign in again.");
      } finally {
        setLoading(false);
      }
    }

    restoreSession();
  }, []);

  async function handleAuthSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAuthBusy(true);
    setAuthError(null);
    try {
      const response = await fetch(`${apiBase}/api/auth/${authMode}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(typeof payload.detail === "string" ? payload.detail : "Authentication failed.");
      }
      await startSession(payload.access_token as string);
    } catch (authFailure) {
      setAuthError(authFailure instanceof Error ? authFailure.message : "Authentication failed.");
    } finally {
      setAuthBusy(false);
      setLoading(false);
    }
  }

  async function handleAccountCreate(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) {
      return;
    }
    setAccountBusy(true);
    setAccountError(null);
    try {
      const balance = Number(initialBalance);
      const response = await fetch(`${apiBase}/api/accounts`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({
          name: accountName,
          broker: "Manual",
          initial_balance: balance,
          current_balance: balance,
          currency,
          account_type: "manual",
          connection_type: "csv",
        }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(typeof payload.detail === "string" ? payload.detail : "Account could not be created.");
      }
      await startSession(token, payload.id as number);
    } catch (accountFailure) {
      setAccountError(accountFailure instanceof Error ? accountFailure.message : "Account could not be created.");
    } finally {
      setAccountBusy(false);
    }
  }

  async function handleAccountChange(accountId: number) {
    if (!token) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await startSession(token, accountId);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Account data could not be loaded.");
    } finally {
      setLoading(false);
    }
  }

  function handleSignOut() {
    localStorage.removeItem("trading-token");
    setToken(null);
    setAccounts([]);
    setSelectedAccountId(null);
    setDashboard(null);
  }

  async function handleCsvImport(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token || !dashboard || !selectedFile) {
      setImportMessage("Choose a CSV file to import.");
      return;
    }

    setImporting(true);
    setImportMessage(null);
    try {
      const formData = new FormData();
      formData.append("account_id", String(dashboard.account.id));
      formData.append("file", selectedFile);
      const response = await fetch(`${apiBase}/api/trades/import-csv`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      if (!response.ok) {
        throw new Error("CSV import failed. Check the file and try again.");
      }
      const result: { inserted: number; updated: number } = await response.json();
      const data = await loadTradingData(token, dashboard.account.id);
      applyTradingData(data);
      setSelectedFile(null);
      setImportMessage(`${result.inserted} new trades, ${result.updated} updated.`);
    } catch (importError) {
      setImportMessage(importError instanceof Error ? importError.message : "CSV import failed.");
    } finally {
      setImporting(false);
    }
  }

  async function handleRiskSave(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token || !dashboard) {
      return;
    }

    setSavingRisk(true);
    setRiskMessage(null);
    try {
      const response = await fetch(`${apiBase}/api/accounts/${dashboard.account.id}/risk-rules`, {
        method: "PUT",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify(riskDraft),
      });
      if (!response.ok) {
        throw new Error("Risk limits could not be saved.");
      }
      const data = await loadTradingData(token, dashboard.account.id);
      applyTradingData(data);
      setRiskMessage("Risk limits saved.");
    } catch (saveError) {
      setRiskMessage(saveError instanceof Error ? saveError.message : "Risk limits could not be saved.");
    } finally {
      setSavingRisk(false);
    }
  }

  const chartPoints = useMemo(() => {
    const values = dashboard?.equity_curve ?? [];
    if (!values.length) {
      return "0,0";
    }

    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min || 1;

    return values
      .map((value, index) => {
        const x = (index / Math.max(values.length - 1, 1)) * 100;
        const y = 100 - ((value - min) / range) * 100;
        return `${x},${y}`;
      })
      .join(" ");
  }, [dashboard]);

  const metrics = dashboard?.metrics ?? {
    total_trades: 0,
    winning_trades: 0,
    losing_trades: 0,
    win_rate: 0,
    gross_profit: 0,
    gross_loss: 0,
    net_profit: 0,
    average_win: 0,
    average_loss: 0,
    profit_factor: 0,
    expectancy: 0,
    balance: 0,
    equity: 0,
    daily_pnl: 0,
    max_drawdown: 0,
    max_drawdown_pct: 0,
  };

  const cards = [
    { label: "Balance", value: formatMoney(metrics.balance), tone: "neutral" },
    { label: "Equity", value: formatMoney(metrics.equity), tone: "positive" },
    { label: "Net P&L", value: formatSignedMoney(metrics.net_profit), tone: metrics.net_profit >= 0 ? "positive" : "negative" },
    { label: "Win Rate", value: formatPercent(metrics.win_rate), tone: "neutral" },
    { label: "Profit Factor", value: metrics.profit_factor.toFixed(2), tone: "neutral" },
    { label: "Expectancy", value: formatSignedMoney(metrics.expectancy), tone: metrics.expectancy >= 0 ? "positive" : "negative" },
    { label: "Max Drawdown", value: `${formatMoney(metrics.max_drawdown)} (${formatPercent(metrics.max_drawdown_pct)})`, tone: "negative" },
    { label: "Total Trades", value: String(metrics.total_trades), tone: "neutral" },
  ];

  if (loading) {
    return (
      <main className="grid min-h-screen place-items-center bg-slate-950 px-4 text-slate-300">
        <p>Restoring your trading workspace...</p>
      </main>
    );
  }

  if (!token) {
    return (
      <main className="grid min-h-screen place-items-center bg-slate-950 px-4 py-10 text-slate-100">
        <section className="w-full max-w-md border-y border-slate-800 py-8">
          <p className="text-xs uppercase tracking-[0.2em] text-emerald-300">Trading Intelligence</p>
          <h1 className="mt-2 text-2xl font-semibold text-white">{authMode === "login" ? "Welcome back" : "Create your workspace"}</h1>
          <div className="mt-6 grid grid-cols-2 border-b border-slate-800" role="tablist" aria-label="Authentication mode">
            {(["login", "register"] as const).map((mode) => (
              <button
                aria-selected={authMode === mode}
                className={`border-b-2 px-3 py-3 text-sm font-medium capitalize ${authMode === mode ? "border-emerald-400 text-white" : "border-transparent text-slate-500 hover:text-slate-300"}`}
                key={mode}
                onClick={() => { setAuthMode(mode); setAuthError(null); }}
                role="tab"
                type="button"
              >
                {mode}
              </button>
            ))}
          </div>
          <form className="mt-6 space-y-4" onSubmit={handleAuthSubmit}>
            <label className="block space-y-1.5 text-sm text-slate-300" htmlFor="auth-email">
              <span>Email</span>
              <input autoComplete="email" className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2.5 text-white outline-none focus:border-emerald-400" id="auth-email" onChange={(event) => setEmail(event.target.value)} required type="email" value={email} />
            </label>
            <label className="block space-y-1.5 text-sm text-slate-300" htmlFor="auth-password">
              <span>Password</span>
              <input autoComplete={authMode === "login" ? "current-password" : "new-password"} className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2.5 text-white outline-none focus:border-emerald-400" id="auth-password" minLength={8} onChange={(event) => setPassword(event.target.value)} required type="password" value={password} />
            </label>
            {authError && <p className="text-sm text-rose-300" role="alert">{authError}</p>}
            <button className="w-full rounded-lg bg-emerald-400 px-4 py-2.5 text-sm font-semibold text-slate-950 disabled:opacity-50" disabled={authBusy} type="submit">
              {authBusy ? "Please wait..." : authMode === "login" ? "Sign in" : "Create account"}
            </button>
          </form>
        </section>
      </main>
    );
  }

  if (!accounts.length) {
    return (
      <main className="grid min-h-screen place-items-center bg-slate-950 px-4 py-10 text-slate-100">
        <section className="w-full max-w-lg border-y border-slate-800 py-8">
          <p className="text-xs uppercase tracking-[0.2em] text-emerald-300">Workspace setup</p>
          <h1 className="mt-2 text-2xl font-semibold text-white">Add your first trading account</h1>
          <form className="mt-6 grid gap-4 sm:grid-cols-2" onSubmit={handleAccountCreate}>
            <label className="space-y-1.5 text-sm text-slate-300 sm:col-span-2" htmlFor="new-account-name">
              <span>Account name</span>
              <input className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2.5 text-white outline-none focus:border-emerald-400" id="new-account-name" onChange={(event) => setAccountName(event.target.value)} required value={accountName} />
            </label>
            <label className="space-y-1.5 text-sm text-slate-300" htmlFor="new-account-balance">
              <span>Starting balance</span>
              <input className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2.5 text-white outline-none focus:border-emerald-400" id="new-account-balance" min="0" onChange={(event) => setInitialBalance(event.target.value)} required step="0.01" type="number" value={initialBalance} />
            </label>
            <label className="space-y-1.5 text-sm text-slate-300" htmlFor="new-account-currency">
              <span>Currency</span>
              <select className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2.5 text-white outline-none focus:border-emerald-400" id="new-account-currency" onChange={(event) => setCurrency(event.target.value)} value={currency}>
                {["USD", "EUR", "GBP", "CAD", "AUD", "JPY"].map((option) => <option key={option}>{option}</option>)}
              </select>
            </label>
            {accountError && <p className="text-sm text-rose-300 sm:col-span-2" role="alert">{accountError}</p>}
            <button className="rounded-lg bg-emerald-400 px-4 py-2.5 text-sm font-semibold text-slate-950 disabled:opacity-50 sm:col-span-2" disabled={accountBusy || !accountName.trim()} type="submit">
              {accountBusy ? "Creating..." : "Create trading account"}
            </button>
          </form>
          <button className="mt-4 text-sm text-slate-400 hover:text-white" onClick={handleSignOut} type="button">Sign out</button>
        </section>
      </main>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto flex w-full max-w-[1600px] gap-6 px-4 py-6 lg:px-6">
        <aside className="hidden w-72 shrink-0 rounded-2xl border border-slate-800 bg-slate-900/70 p-5 lg:block">
          <div className="mb-8 flex items-center justify-between">
            <div>
              <p className="text-[10px] uppercase tracking-[0.28em] text-slate-400">Trading</p>
              <h1 className="mt-1 text-xl font-semibold">Intelligence</h1>
            </div>
            <div className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-1 text-[10px] font-medium text-emerald-300">
              LIVE
            </div>
          </div>

          <nav className="space-y-2 text-sm">
            {[
              "Dashboard",
              "Accounts",
              "Trades",
              "Analytics",
              "Risk",
              "Strategies",
              "AI Analyst",
              "Settings",
            ].map((item, index) => (
              <button
                key={item}
                className={`flex w-full items-center justify-between rounded-xl px-3 py-2.5 text-left transition ${index === 0 ? "bg-slate-800 text-white" : "text-slate-300 hover:bg-slate-800/80"}`}
              >
                <span>{item}</span>
                <span className="text-xs text-slate-500">0{index + 1}</span>
              </button>
            ))}
          </nav>
        </aside>

        <main className="min-w-0 flex-1">
          <header className="mb-6 flex flex-col gap-4 rounded-2xl border border-slate-800 bg-slate-900/70 p-4 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.22em] text-slate-400">Overview</p>
              <h2 className="mt-1 text-2xl font-semibold text-white">
                {dashboard?.account?.name ?? "Demo account"}
              </h2>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <label className="sr-only" htmlFor="account-selector">Trading account</label>
              <select
                className="max-w-56 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 outline-none focus:border-emerald-400"
                id="account-selector"
                onChange={(event) => void handleAccountChange(Number(event.target.value))}
                value={selectedAccountId ?? ""}
              >
                {accounts.map((account) => <option key={account.id} value={account.id}>{account.name} · {account.currency}</option>)}
              </select>
              <div className="rounded-xl border border-slate-700 bg-slate-950/70 px-3 py-2 text-sm text-slate-300">
                30D
              </div>
              <button className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-300 hover:border-rose-400 hover:text-white" onClick={handleSignOut} type="button">
                Sign out
              </button>
            </div>
          </header>

          {loading ? (
            <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-8 text-slate-300">
              Loading dashboard data...
            </div>
          ) : error ? (
            <div className="rounded-2xl border border-red-900/60 bg-red-500/10 p-8 text-red-200">
              {error}
            </div>
          ) : (
            <>
              <section className="mb-6 flex flex-col gap-3 rounded-2xl border border-slate-800 bg-slate-900/70 p-4 md:flex-row md:items-end md:justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-white">Import trades</h3>
                  <p className="mt-1 text-xs text-slate-400">CSV files update this account without duplicating existing trades.</p>
                </div>
                <form className="flex w-full flex-col gap-2 sm:flex-row md:w-auto" onSubmit={handleCsvImport}>
                  <input
                    aria-label="CSV trade file"
                    accept=".csv,text/csv"
                    className="min-w-0 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 file:mr-3 file:border-0 file:bg-transparent file:text-emerald-300 sm:w-72"
                    onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
                    type="file"
                  />
                  <button
                    className="rounded-lg bg-emerald-400 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-emerald-300 disabled:cursor-not-allowed disabled:opacity-50"
                    disabled={importing || !selectedFile}
                    type="submit"
                  >
                    {importing ? "Importing..." : "Import CSV"}
                  </button>
                </form>
                {importMessage && <p className="text-xs text-slate-300" role="status">{importMessage}</p>}
              </section>

              <section aria-labelledby="sync-history-heading" className="mb-6 border-b border-slate-800 pb-4">
                <div className="mb-3 flex items-center justify-between gap-3">
                  <h3 className="text-sm font-semibold text-white" id="sync-history-heading">Recent sync activity</h3>
                  <span className="text-xs text-slate-500">{syncLogs.length} recorded</span>
                </div>
                {syncLogs.length ? (
                  <div className="divide-y divide-slate-800">
                    {syncLogs.slice(0, 5).map((sync) => (
                      <div className="flex flex-col gap-1 py-2 text-xs sm:flex-row sm:items-center sm:justify-between" key={sync.id}>
                        <span className="text-slate-400">{formatDateTime(sync.started_at)}</span>
                        <span className="text-slate-300">
                          {sync.trades_fetched} fetched · {sync.inserted} inserted · {sync.updated} updated
                        </span>
                        <span className={`font-medium uppercase ${sync.status === "success" ? "text-emerald-300" : sync.status === "failed" ? "text-rose-300" : "text-amber-300"}`}>
                          {sync.status}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-slate-500">No trade syncs have been recorded yet.</p>
                )}
              </section>

              <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                {cards.map((card) => (
                  <div key={card.label} className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
                    <div className="mb-2 text-xs uppercase tracking-[0.22em] text-slate-400">{card.label}</div>
                    <div
                      className={`text-2xl font-semibold ${
                        card.tone === "positive"
                          ? "text-emerald-400"
                          : card.tone === "negative"
                            ? "text-rose-400"
                            : "text-white"
                      }`}
                    >
                      {card.value}
                    </div>
                  </div>
                ))}
              </section>

              <section className="mt-6 grid gap-6 xl:grid-cols-[1.7fr_0.9fr]">
                <div className="min-w-0 rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
                  <div className="mb-4 flex items-center justify-between">
                    <h3 className="text-lg font-semibold">Equity curve</h3>
                    <span className="text-xs uppercase tracking-[0.2em] text-slate-400">Balance / drawdown</span>
                  </div>
                  <svg viewBox="0 0 100 100" className="h-64 w-full overflow-visible rounded-xl bg-slate-950/60 p-2">
                    <defs>
                      <linearGradient id="equityFill" x1="0" x2="0" y1="0" y2="1">
                        <stop offset="0%" stopColor="#34d399" stopOpacity="0.35" />
                        <stop offset="100%" stopColor="#34d399" stopOpacity="0" />
                      </linearGradient>
                    </defs>
                    <polyline
                      fill="none"
                      stroke="#34d399"
                      strokeWidth="1.5"
                      points={chartPoints}
                    />
                    <polyline
                      fill="none"
                      stroke="#f87171"
                      strokeWidth="1"
                      points={chartPoints}
                      opacity="0.3"
                    />
                  </svg>
                </div>

                <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
                  <div className="mb-4 text-lg font-semibold">Recent trades</div>
                  <div className="space-y-3">
                    {(dashboard?.trades ?? []).slice(0, 5).map((trade) => (
                      <div key={trade.id} className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-950/60 px-3 py-2">
                        <div>
                          <div className="font-medium text-white">{trade.symbol}</div>
                          <div className="text-xs text-slate-400">{trade.strategy_id}</div>
                        </div>
                        <div className="text-right">
                          <div className={trade.net_profit >= 0 ? "text-emerald-400" : "text-rose-400"}>
                            {formatSignedMoney(trade.net_profit)}
                          </div>
                          <div className="text-xs text-slate-400">R {String(trade.r_multiple)}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </section>

              <section className="mt-6 grid min-w-0 gap-6 xl:grid-cols-2">
                <div className="min-w-0 rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
                  <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <h3 className="text-lg font-semibold">Risk limits</h3>
                      <p className="mt-1 text-xs text-slate-400">Zero disables a loss or drawdown limit.</p>
                    </div>
                    <span className={`rounded-md px-2 py-1 text-xs font-semibold uppercase ${risk?.assessment.status === "breached" ? "bg-rose-500/15 text-rose-300" : risk?.assessment.status === "review_required" ? "bg-amber-500/15 text-amber-200" : "bg-emerald-500/15 text-emerald-300"}`}>
                      {risk?.rules ? risk.assessment.status.replace("_", " ") : "No limits"}
                    </span>
                  </div>
                  <form className="grid gap-3 sm:grid-cols-2" onSubmit={handleRiskSave}>
                    {riskNumericFields.map(({ key, label, unit, step, max }) => (
                      <label className="space-y-1 text-xs text-slate-400" htmlFor={key} key={key}>
                        <span>{label} ({unit === "currency" ? dashboard?.account.currency ?? "USD" : unit})</span>
                        <input
                          className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-emerald-400"
                          id={key}
                          min="0"
                          max={max}
                          onChange={(event) => setRiskDraft((current) => ({ ...current, [key]: Number(event.target.value) }))}
                          step={step}
                          type="number"
                          value={riskDraft[key]}
                        />
                      </label>
                    ))}
                    <div className="grid gap-3 border-t border-slate-800 pt-3 sm:col-span-2 sm:grid-cols-2">
                      <label className="flex items-center gap-3 text-sm text-slate-300" htmlFor="news-restriction">
                        <input checked={riskDraft.news_restriction} className="size-4 accent-emerald-400" id="news-restriction" onChange={(event) => setRiskDraft((current) => ({ ...current, news_restriction: event.target.checked }))} type="checkbox" />
                        Restrict trading around news
                      </label>
                      <label className="flex items-center gap-3 text-sm text-slate-300" htmlFor="weekend-restriction">
                        <input checked={riskDraft.weekend_restriction} className="size-4 accent-emerald-400" id="weekend-restriction" onChange={(event) => setRiskDraft((current) => ({ ...current, weekend_restriction: event.target.checked }))} type="checkbox" />
                        Restrict weekend exposure
                      </label>
                    </div>
                    <div className="flex items-end justify-between gap-3 sm:col-span-2">
                      <p className="text-xs text-slate-400" role="status">{riskMessage ?? (risk ? `Today ${formatSignedMoney(risk.assessment.daily_net_profit)} · Total ${formatSignedMoney(risk.assessment.total_net_profit)}` : "")}</p>
                      <button
                        className="rounded-lg border border-slate-700 px-4 py-2 text-sm font-medium text-white transition hover:border-emerald-400 disabled:opacity-50"
                        disabled={savingRisk}
                        type="submit"
                      >
                        {savingRisk ? "Saving..." : "Save limits"}
                      </button>
                    </div>
                  </form>
                  <div className="mt-4 divide-y divide-slate-800 border-t border-slate-800">
                    {(risk?.assessment.checks ?? []).map((check) => (
                      <div className="py-2 text-sm" key={check.key}>
                        <div className="flex items-center justify-between gap-3">
                          <span className="text-slate-300">{check.label}</span>
                          <span className={check.status === "breached" ? "text-rose-300" : check.status === "not_evaluable" ? "text-amber-200" : check.status === "met" || check.status === "within_limit" ? "text-emerald-300" : "text-slate-400"}>
                            {formatRiskCheck(check, dashboard?.account.currency ?? "USD")}
                          </span>
                        </div>
                        {check.detail && <p className="mt-1 text-xs text-amber-100/70">{check.detail}</p>}
                      </div>
                    ))}
                  </div>
                </div>

                <div className="min-w-0 rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
                  <div className="mb-4 flex items-center justify-between">
                    <div>
                      <h3 className="text-lg font-semibold">Strategy performance</h3>
                      <p className="mt-1 text-xs text-slate-400">Ranked by net profit</p>
                    </div>
                    <span className="text-xs text-slate-400">{strategies.length} strategies</span>
                  </div>
                  {strategies.length ? (
                    <div className="overflow-x-auto">
                      <table className="w-full min-w-[420px] text-left text-sm">
                        <thead className="border-b border-slate-800 text-xs uppercase text-slate-500">
                          <tr>
                            <th className="pb-2 font-medium">Strategy</th>
                            <th className="pb-2 text-right font-medium">Trades</th>
                            <th className="pb-2 text-right font-medium">Win rate</th>
                            <th className="pb-2 text-right font-medium">Net P&amp;L</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800">
                          {strategies.map((strategy) => (
                            <tr key={strategy.strategy_id}>
                              <td className="py-3 font-medium text-white">{strategy.strategy_id}</td>
                              <td className="py-3 text-right text-slate-300">{strategy.total_trades}</td>
                              <td className="py-3 text-right text-slate-300">{formatPercent(strategy.win_rate)}</td>
                              <td className={`py-3 text-right ${strategy.net_profit >= 0 ? "text-emerald-300" : "text-rose-300"}`}>
                                {formatSignedMoney(strategy.net_profit)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <p className="border-t border-slate-800 py-6 text-sm text-slate-400">No tagged trades yet.</p>
                  )}
                </div>
              </section>

              <section aria-labelledby="analyst-heading" className="mt-8 border-t border-slate-800 pt-6">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-xs uppercase tracking-[0.18em] text-emerald-300">Rules-based analysis</p>
                    <h3 className="mt-1 text-lg font-semibold text-white" id="analyst-heading">AI Trading Analyst</h3>
                  </div>
                  <span className="rounded-md border border-slate-700 px-2 py-1 text-xs text-slate-300">
                    {analyst?.confidence ?? "loading"} confidence
                  </span>
                </div>
                <p className="mt-4 max-w-4xl text-sm leading-6 text-slate-200">
                  {analyst?.summary ?? "Preparing an analysis from this account's closed trades."}
                </p>

                {analyst && (
                  <>
                    <dl className="mt-5 grid grid-cols-2 gap-y-4 border-y border-slate-800 py-4 sm:grid-cols-3 lg:grid-cols-5">
                      <div>
                        <dt className="text-xs text-slate-500">Closed trades</dt>
                        <dd className="mt-1 text-sm font-medium text-white">{analyst.metrics.total_trades}</dd>
                      </div>
                      <div>
                        <dt className="text-xs text-slate-500">Win rate</dt>
                        <dd className="mt-1 text-sm font-medium text-white">{formatPercent(analyst.metrics.win_rate)}</dd>
                      </div>
                      <div>
                        <dt className="text-xs text-slate-500">Net P&amp;L</dt>
                        <dd className={`mt-1 text-sm font-medium ${analyst.metrics.net_profit >= 0 ? "text-emerald-300" : "text-rose-300"}`}>
                          {formatSignedMoney(analyst.metrics.net_profit)}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-xs text-slate-500">Expectancy</dt>
                        <dd className="mt-1 text-sm font-medium text-white">{formatSignedMoney(analyst.metrics.expectancy)}</dd>
                      </div>
                      <div>
                        <dt className="text-xs text-slate-500">Profit factor</dt>
                        <dd className="mt-1 text-sm font-medium text-white">
                          {analyst.metrics.profit_factor === null ? "N/A" : analyst.metrics.profit_factor.toFixed(2)}
                        </dd>
                      </div>
                    </dl>

                    <div className="divide-y divide-slate-800">
                      {analyst.insights.map((insight) => (
                        <article className="py-4" key={insight.key}>
                          <h4 className={`text-sm font-semibold ${insightStyles[insight.severity] ?? insightStyles.neutral}`}>
                            {insight.title}
                          </h4>
                          <p className="mt-1 text-sm leading-5 text-slate-400">{insight.detail}</p>
                        </article>
                      ))}
                    </div>
                    <p className="mt-3 text-xs text-slate-500">{analyst.disclaimer}</p>
                  </>
                )}
              </section>
            </>
          )}
        </main>
      </div>
    </div>
  );
}
