import React, { useEffect, useState } from 'react';
import {
  TrendingUp,
  TrendingDown,
  Layers,
  Sliders,
  HelpCircle,
  Trash2,
  RefreshCw,
  Target,
  PieChart,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Modal } from '@/components/ui/modal';
import { Badge } from '@/components/ui/badge';
import { Alert } from '@/components/ui/alert';
import { FinancialAmount } from '@/components/ui/financial-amount';
import { EmptyState } from '@/components/feedback/EmptyState';
import { useForecastStore } from '@/store/useForecastStore';

export const Forecast: React.FC = () => {
  const {
    cashFlowForecast,
    incomeForecast,
    expenseForecast,
    categoryForecast,
    budgetExhaustion,
    goalTrajectories,
    scenarios,
    evaluations,
    selectedHorizon,
    isLoading,
    error,
    setSelectedHorizon,
    fetchForecastOverview,
    generateForecast,
    fetchBudgetExhaustion,
    fetchGoalTrajectories,
    fetchScenarios,
    createScenario,
    deleteScenario,
    fetchEvaluations,
  } = useForecastStore();

  const [activeTab, setActiveTab] = useState<'cash_flow' | 'income_expense' | 'budgets_goals' | 'scenarios'>('cash_flow');
  const [isScenarioModalOpen, setIsScenarioModalOpen] = useState(false);
  const [isGenerateModalOpen, setIsGenerateModalOpen] = useState(false);

  // Scenario form state
  const [scenarioName, setScenarioName] = useState('');
  const [scenarioType, setScenarioType] = useState('custom');
  const [incomeChangePct, setIncomeChangePct] = useState('0');
  const [expenseChangePct, setExpenseChangePct] = useState('0');
  const [oneTimeExpense, setOneTimeExpense] = useState('0');
  const [oneTimeDesc, setOneTimeDesc] = useState('');

  // Generation options
  const [prefModel, setPrefModel] = useState<string>('auto');
  const [confLevel, setConfLevel] = useState('0.80');

  useEffect(() => {
    fetchForecastOverview(selectedHorizon);
    fetchBudgetExhaustion();
    fetchGoalTrajectories();
    fetchScenarios();
    fetchEvaluations();
  }, [selectedHorizon]);

  const handleHorizonChange = (horizon: number) => {
    setSelectedHorizon(horizon);
    fetchForecastOverview(horizon);
  };

  const handleRunForecast = async () => {
    await generateForecast({
      horizon_days: selectedHorizon,
      preferred_model: prefModel === 'auto' ? null : prefModel,
      confidence_level: parseFloat(confLevel) || 0.80,
    });
    setIsGenerateModalOpen(false);
  };

  const handleCreateScenario = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!scenarioName.trim()) return;

    const oneTimeOutflows = [];
    const oneTimePaise = Math.round((parseFloat(oneTimeExpense) || 0) * 100);
    if (oneTimePaise > 0) {
      oneTimeOutflows.push({
        date: new Date().toISOString().split('T')[0],
        amount_paise: oneTimePaise,
        description: oneTimeDesc || 'One-time hypothetical expense',
      });
    }

    await createScenario({
      name: scenarioName,
      scenario_type: scenarioType,
      horizon_days: selectedHorizon,
      income_change_pct: parseFloat(incomeChangePct) || 0,
      expense_change_pct: parseFloat(expenseChangePct) || 0,
      one_time_outflows: oneTimeOutflows,
    });

    setIsScenarioModalOpen(false);
    setScenarioName('');
    setIncomeChangePct('0');
    setExpenseChangePct('0');
    setOneTimeExpense('0');
    setOneTimeDesc('');
  };

  const bestEval = evaluations.find((e) => e.is_best_model);

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
              Financial Forecasting & Predictive Intelligence
            </h1>
            <Badge variant="brand" className="bg-emerald-50 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-400">
              Confidence Interval: {(parseFloat(confLevel) * 100).toFixed(0)}%
            </Badge>
          </div>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Forward-looking cash flow projections, budget exhaustion estimates, and deterministic what-if scenario simulations.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Horizon Switcher */}
          <div className="inline-flex rounded-lg border border-slate-200 bg-white p-1 text-xs font-medium dark:border-slate-800 dark:bg-slate-900">
            {[7, 30, 90, 180, 365].map((h) => (
              <button
                key={h}
                type="button"
                onClick={() => handleHorizonChange(h)}
                className={`rounded-md px-3 py-1.5 transition-colors ${
                  selectedHorizon === h
                    ? 'bg-indigo-600 text-white'
                    : 'text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white'
                }`}
              >
                {h <= 90 ? `${h}D` : h === 180 ? '6M' : '1Y'}
              </button>
            ))}
          </div>

          <Button variant="outline" size="sm" onClick={() => setIsGenerateModalOpen(true)}>
            <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
            Regenerate
          </Button>

          <Button size="sm" onClick={() => setIsScenarioModalOpen(true)}>
            <Sliders className="mr-1.5 h-3.5 w-3.5" />
            New Scenario
          </Button>
        </div>
      </div>

      {error && <Alert variant="error">{error}</Alert>}

      {/* Model Transparency Disclaimer */}
      <div className="flex items-center justify-between rounded-lg border border-indigo-100 bg-indigo-50/50 p-3 text-xs text-indigo-900 dark:border-indigo-900/30 dark:bg-indigo-950/20 dark:text-indigo-300">
        <div className="flex items-center gap-2">
          <HelpCircle className="h-4 w-4 shrink-0 text-indigo-600 dark:text-indigo-400" />
          <span>
            <strong>Informational Projection:</strong> Forecasts are mathematical estimates based on historical trends and confirmed recurring commitments. They never alter actual accounting records.
          </span>
        </div>
        {bestEval && (
          <span className="font-medium text-indigo-700 dark:text-indigo-400">
            Selected Model: <code className="font-semibold">{bestEval.model_name}</code> (WAPE: {(bestEval.wape * 100).toFixed(1)}%)
          </span>
        )}
      </div>

      {/* KPI Overview Cards */}
      {cashFlowForecast && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <span className="text-xs font-medium text-slate-500">Starting Liquid Balance</span>
            <div className="mt-1">
              <FinancialAmount
                amount={Number(cashFlowForecast.starting_balance)}
                currency={cashFlowForecast.currency}
                className="text-xl font-bold text-slate-900 dark:text-white"
              />
            </div>
            <span className="text-[11px] text-slate-400">Verified bank & cash accounts</span>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <span className="text-xs font-medium text-slate-500">Projected Ending Balance</span>
            <div className="mt-1">
              <FinancialAmount
                amount={Number(cashFlowForecast.projected_ending_balance)}
                currency={cashFlowForecast.currency}
                className={`text-xl font-bold ${
                  Number(cashFlowForecast.projected_ending_balance) >= 0 ? 'text-emerald-600' : 'text-rose-600'
                }`}
              />
            </div>
            <span className="text-[11px] text-slate-400">At day {selectedHorizon} horizon</span>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <span className="text-xs font-medium text-slate-500">Expected Inflows</span>
            <div className="mt-1">
              <FinancialAmount
                amount={Number(cashFlowForecast.total_projected_inflow)}
                currency={cashFlowForecast.currency}
                className="text-xl font-bold text-emerald-600"
              />
            </div>
            <span className="text-[11px] text-slate-400">Scheduled + estimated income</span>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <span className="text-xs font-medium text-slate-500">Expected Outflows</span>
            <div className="mt-1">
              <FinancialAmount
                amount={Number(cashFlowForecast.total_projected_outflow)}
                currency={cashFlowForecast.currency}
                className="text-xl font-bold text-rose-600"
              />
            </div>
            <span className="text-[11px] text-slate-400">Commitments + discretionary</span>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <span className="text-xs font-medium text-slate-500">Net Cash Flow Outlook</span>
            <div className="mt-1">
              <FinancialAmount
                amount={Number(cashFlowForecast.net_cash_flow)}
                currency={cashFlowForecast.currency}
                className={`text-xl font-bold ${
                  Number(cashFlowForecast.net_cash_flow) >= 0 ? 'text-emerald-600' : 'text-rose-600'
                }`}
              />
            </div>
            <span className="text-[11px] text-slate-400">Total net surplus / deficit</span>
          </div>
        </div>
      )}

      {/* Tabs Navigation */}
      <div className="flex border-b border-slate-200 dark:border-slate-800">
        <button
          type="button"
          onClick={() => setActiveTab('cash_flow')}
          className={`flex items-center gap-2 border-b-2 px-4 py-2.5 text-sm font-medium transition-colors ${
            activeTab === 'cash_flow'
              ? 'border-indigo-600 text-indigo-600 dark:border-indigo-400 dark:text-indigo-400'
              : 'border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-700 dark:text-slate-400'
          }`}
        >
          <Layers className="h-4 w-4" />
          Cash Flow & Balance Timeline
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('income_expense')}
          className={`flex items-center gap-2 border-b-2 px-4 py-2.5 text-sm font-medium transition-colors ${
            activeTab === 'income_expense'
              ? 'border-indigo-600 text-indigo-600 dark:border-indigo-400 dark:text-indigo-400'
              : 'border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-700 dark:text-slate-400'
          }`}
        >
          <PieChart className="h-4 w-4" />
          Income & Category Breakdown
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('budgets_goals')}
          className={`flex items-center gap-2 border-b-2 px-4 py-2.5 text-sm font-medium transition-colors ${
            activeTab === 'budgets_goals'
              ? 'border-indigo-600 text-indigo-600 dark:border-indigo-400 dark:text-indigo-400'
              : 'border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-700 dark:text-slate-400'
          }`}
        >
          <Target className="h-4 w-4" />
          Budget Exhaustion & Goals
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('scenarios')}
          className={`flex items-center gap-2 border-b-2 px-4 py-2.5 text-sm font-medium transition-colors ${
            activeTab === 'scenarios'
              ? 'border-indigo-600 text-indigo-600 dark:border-indigo-400 dark:text-indigo-400'
              : 'border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-700 dark:text-slate-400'
          }`}
        >
          <Sliders className="h-4 w-4" />
          What-If Scenarios ({scenarios.length})
        </button>
      </div>

      {/* Tab 1: Cash Flow & Balance Timeline */}
      {activeTab === 'cash_flow' && cashFlowForecast && (
        <div className="space-y-4">
          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <div className="border-b border-slate-200 px-6 py-4 dark:border-slate-800">
              <h2 className="text-base font-semibold text-slate-900 dark:text-white">
                Forward Cash-Flow Progression ({cashFlowForecast.timeline.length} Days)
              </h2>
              <p className="text-xs text-slate-500">
                Daily projected balance incorporating scheduled commitments and discretionary trends with uncertainty bands.
              </p>
            </div>

            <div className="max-h-[500px] overflow-y-auto">
              <table className="w-full text-left text-xs text-slate-600 dark:text-slate-400">
                <thead className="sticky top-0 bg-slate-50 text-[11px] font-semibold uppercase tracking-wider text-slate-500 dark:bg-slate-800 dark:text-slate-400">
                  <tr>
                    <th className="px-6 py-3">Date</th>
                    <th className="px-6 py-3">Inflow</th>
                    <th className="px-6 py-3">Outflow</th>
                    <th className="px-6 py-3">Net Flow</th>
                    <th className="px-6 py-3">Projected Balance</th>
                    <th className="px-6 py-3">Confidence Band (Lower – Upper)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                  {cashFlowForecast.timeline.map((pt, idx) => (
                    <tr key={idx} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/50">
                      <td className="whitespace-nowrap px-6 py-3 font-medium text-slate-900 dark:text-white">
                        {new Date(pt.date).toLocaleDateString('en-IN', {
                          month: 'short',
                          day: 'numeric',
                          weekday: 'short',
                        })}
                      </td>
                      <td className="whitespace-nowrap px-6 py-3 text-emerald-600">
                        <FinancialAmount amount={Number(pt.inflow_paise) / 100} currency="INR" />
                        {pt.inflow_recurring_paise > 0 && (
                          <span className="ml-1 text-[10px] text-emerald-500">(Sched)</span>
                        )}
                      </td>
                      <td className="whitespace-nowrap px-6 py-3 text-rose-600">
                        <FinancialAmount amount={Number(pt.outflow_paise) / 100} currency="INR" />
                        {pt.outflow_recurring_paise > 0 && (
                          <span className="ml-1 text-[10px] text-rose-500">(Sched)</span>
                        )}
                      </td>
                      <td className="whitespace-nowrap px-6 py-3 font-medium">
                        <span className={pt.net_cash_flow_paise >= 0 ? 'text-emerald-600' : 'text-rose-600'}>
                          <FinancialAmount amount={Number(pt.net_cash_flow_paise) / 100} currency="INR" />
                        </span>
                      </td>
                      <td className="whitespace-nowrap px-6 py-3 font-bold text-slate-900 dark:text-white">
                        <FinancialAmount amount={Number(pt.projected_balance_paise) / 100} currency="INR" />
                      </td>
                      <td className="whitespace-nowrap px-6 py-3 text-[11px] text-slate-500">
                        <FinancialAmount amount={Number(pt.lower_balance_paise) / 100} currency="INR" />
                        {' – '}
                        <FinancialAmount amount={Number(pt.upper_balance_paise) / 100} currency="INR" />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Income & Category Breakdown */}
      {activeTab === 'income_expense' && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Income Breakdown */}
          {incomeForecast && (
            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
              <h2 className="text-base font-semibold text-slate-900 dark:text-white">Income Projection Signals</h2>
              <div className="mt-4 grid grid-cols-2 gap-4">
                <div className="rounded-lg bg-emerald-50/50 p-3 dark:bg-emerald-950/20">
                  <span className="text-xs text-emerald-800 dark:text-emerald-300">Scheduled Inflows</span>
                  <div className="mt-1 font-bold text-emerald-700 dark:text-emerald-400">
                    <FinancialAmount amount={Number(incomeForecast.scheduled_income)} currency="INR" />
                  </div>
                  <span className="text-[10px] text-slate-400">Confirmed recurring salaries/draws</span>
                </div>
                <div className="rounded-lg bg-slate-50 p-3 dark:bg-slate-800">
                  <span className="text-xs text-slate-600 dark:text-slate-400">Discretionary / Variable</span>
                  <div className="mt-1 font-bold text-slate-800 dark:text-slate-200">
                    <FinancialAmount amount={Number(incomeForecast.estimated_discretionary_income)} currency="INR" />
                  </div>
                  <span className="text-[10px] text-slate-400">Historical freelance & transfers</span>
                </div>
              </div>
            </div>
          )}

          {/* Expense Breakdown */}
          {expenseForecast && (
            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
              <h2 className="text-base font-semibold text-slate-900 dark:text-white">Expense Projection Signals</h2>
              <div className="mt-4 grid grid-cols-2 gap-4">
                <div className="rounded-lg bg-rose-50/50 p-3 dark:bg-rose-950/20">
                  <span className="text-xs text-rose-800 dark:text-rose-300">Scheduled Commitments</span>
                  <div className="mt-1 font-bold text-rose-700 dark:text-rose-400">
                    <FinancialAmount amount={Number(expenseForecast.scheduled_commitments)} currency="INR" />
                  </div>
                  <span className="text-[10px] text-slate-400">Rent, EMI, Utilities, Subscriptions</span>
                </div>
                <div className="rounded-lg bg-slate-50 p-3 dark:bg-slate-800">
                  <span className="text-xs text-slate-600 dark:text-slate-400">Discretionary Spend</span>
                  <div className="mt-1 font-bold text-slate-800 dark:text-slate-200">
                    <FinancialAmount amount={Number(expenseForecast.discretionary_expense)} currency="INR" />
                  </div>
                  <span className="text-[10px] text-slate-400">Model predicted variable spend</span>
                </div>
              </div>
            </div>
          )}

          {/* Category Projections Table */}
          {categoryForecast && (
            <div className="col-span-1 rounded-xl border border-slate-200 bg-white shadow-sm lg:col-span-2 dark:border-slate-800 dark:bg-slate-900">
              <div className="border-b border-slate-200 px-6 py-4 dark:border-slate-800">
                <h2 className="text-base font-semibold text-slate-900 dark:text-white">Category-Wise Spending Forecasts</h2>
                <p className="text-xs text-slate-500">
                  Extrapolated category demand based on 90-day transaction trends and seasonal pacing.
                </p>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-slate-600 dark:text-slate-400">
                  <thead className="bg-slate-50 text-[11px] font-semibold uppercase text-slate-500 dark:bg-slate-800">
                    <tr>
                      <th className="px-6 py-3">Category</th>
                      <th className="px-6 py-3">Projected Spend</th>
                      <th className="px-6 py-3">Estimated Range</th>
                      <th className="px-6 py-3">Historical Monthly Avg</th>
                      <th className="px-6 py-3">Trend Direction</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                    {categoryForecast.categories.map((c, idx) => (
                      <tr key={idx} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/50">
                        <td className="px-6 py-3 font-medium text-slate-900 dark:text-white">
                          {c.category_name}
                        </td>
                        <td className="px-6 py-3 font-semibold text-slate-900 dark:text-white">
                          <FinancialAmount amount={Number(c.projected_amount)} currency="INR" />
                        </td>
                        <td className="px-6 py-3 text-slate-500">
                          <FinancialAmount amount={Number(c.lower_amount)} currency="INR" />
                          {' – '}
                          <FinancialAmount amount={Number(c.upper_amount)} currency="INR" />
                        </td>
                        <td className="px-6 py-3 text-slate-500">
                          <FinancialAmount amount={Number(c.historical_monthly_average)} currency="INR" />
                        </td>
                        <td className="px-6 py-3">
                          {c.trend_direction === 'increasing' ? (
                            <Badge variant="expense" className="flex w-fit items-center gap-1">
                              <TrendingUp className="h-3 w-3" /> Increasing
                            </Badge>
                          ) : c.trend_direction === 'decreasing' ? (
                            <Badge variant="income" className="flex w-fit items-center gap-1">
                              <TrendingDown className="h-3 w-3" /> Decreasing
                            </Badge>
                          ) : (
                            <Badge variant="neutral" className="flex w-fit items-center gap-1">
                              Stable
                            </Badge>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Budget Exhaustion & Goals */}
      {activeTab === 'budgets_goals' && (
        <div className="space-y-6">
          {/* Budget Exhaustion Section */}
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <h2 className="text-base font-semibold text-slate-900 dark:text-white">Budget Exhaustion Estimates</h2>
            <p className="text-xs text-slate-500">
              Pacing analysis projecting whether category and period spending caps will be breached before the cycle ends.
            </p>

            {budgetExhaustion && budgetExhaustion.estimates.length > 0 ? (
              <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {budgetExhaustion.estimates.map((est, idx) => (
                  <div
                    key={idx}
                    className={`rounded-xl border p-4 transition-all ${
                      est.status === 'already_exhausted'
                        ? 'border-rose-200 bg-rose-50/20 dark:border-rose-900/40'
                        : est.status === 'projected_exhaustion'
                        ? 'border-amber-200 bg-amber-50/20 dark:border-amber-900/40'
                        : 'border-slate-200 bg-slate-50/30 dark:border-slate-800'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-slate-900 dark:text-white">{est.budget_name}</span>
                      <Badge
                        variant={
                          est.status === 'already_exhausted'
                            ? 'expense'
                            : est.status === 'projected_exhaustion'
                            ? 'warning'
                            : 'income'
                        }
                      >
                        {est.status.replace('_', ' ')}
                      </Badge>
                    </div>

                    <div className="mt-2 text-xs text-slate-500">
                      Scope: <strong className="text-slate-700 dark:text-slate-300">{est.category_name}</strong>
                    </div>

                    <div className="mt-3 flex items-baseline justify-between text-xs">
                      <span>Spent: <FinancialAmount amount={Number(est.current_spend)} currency="INR" /></span>
                      <span className="text-slate-400">Cap: <FinancialAmount amount={Number(est.total_allocated)} currency="INR" /></span>
                    </div>

                    <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                      <div
                        className={`h-full ${
                          est.utilization_pct >= 100
                            ? 'bg-rose-500'
                            : est.utilization_pct >= 80
                            ? 'bg-amber-500'
                            : 'bg-emerald-500'
                        }`}
                        style={{ width: `${Math.min(100, est.utilization_pct)}%` }}
                      />
                    </div>

                    <div className="mt-3 border-t border-slate-100 pt-2 text-[11px] text-slate-500 dark:border-slate-800">
                      {est.estimated_exhaustion_date ? (
                        <span>
                          Projected breach: <strong className="text-slate-700 dark:text-slate-300">{est.estimated_exhaustion_date}</strong> ({est.days_to_exhaustion} days)
                        </span>
                      ) : (
                        <span className="text-emerald-600">Within allocated capacity</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="mt-4">
                <EmptyState
                  title="No Active Budgets"
                  description="Create a monthly or custom budget in Personal Budgeting to enable exhaustion pacing."
                />
              </div>
            )}
          </div>

          {/* Goal Trajectory Section */}
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <h2 className="text-base font-semibold text-slate-900 dark:text-white">Savings Goal Completion Trajectories</h2>
            <p className="text-xs text-slate-500">
              Trajectory modeling comparing required contribution velocity against actual savings rates.
            </p>

            {goalTrajectories && goalTrajectories.goals.length > 0 ? (
              <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {goalTrajectories.goals.map((g, idx) => (
                  <div key={idx} className="rounded-xl border border-slate-200 p-4 shadow-sm dark:border-slate-800">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-slate-900 dark:text-white">{g.goal_name}</span>
                      <Badge variant={g.is_on_track ? 'income' : 'warning'}>
                        {g.status.replace('_', ' ')}
                      </Badge>
                    </div>

                    <div className="mt-3 flex items-baseline justify-between text-xs">
                      <span>Saved: <FinancialAmount amount={Number(g.current_balance)} currency="INR" /></span>
                      <span className="text-slate-400">Target: <FinancialAmount amount={Number(g.target_amount)} currency="INR" /></span>
                    </div>

                    <div className="mt-2 text-xs text-slate-500">
                      Savings velocity: <strong className="text-slate-700 dark:text-slate-300"><FinancialAmount amount={Number(g.monthly_savings_pace)} currency="INR" />/mo</strong>
                    </div>

                    <div className="mt-3 border-t border-slate-100 pt-2 text-[11px] text-slate-500 dark:border-slate-800">
                      {g.projected_completion_date ? (
                        <span>Estimated completion: <strong>{g.projected_completion_date}</strong></span>
                      ) : (
                        <span className="text-rose-500">Requires regular contributions to estimate completion</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="mt-4">
                <EmptyState
                  title="No Active Financial Goals"
                  description="Set up savings goals in the Goals module to view velocity projections."
                />
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 4: What-If Scenarios */}
      {activeTab === 'scenarios' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-semibold text-slate-900 dark:text-white">Deterministic What-If Scenarios</h2>
              <p className="text-xs text-slate-500">
                Explore hypothetical changes (salary adjustments, rent increases, one-time expenses) without altering actual financial records.
              </p>
            </div>
            <Button size="sm" onClick={() => setIsScenarioModalOpen(true)}>
              <Sliders className="mr-1.5 h-3.5 w-3.5" />
              Build Scenario
            </Button>
          </div>

          {scenarios.length > 0 ? (
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              {scenarios.map((s) => (
                <div key={s.id} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="font-semibold text-slate-900 dark:text-white">{s.name}</h3>
                      <Badge variant="neutral" className="mt-1 text-[10px]">
                        {s.scenario_type.toUpperCase()} ({s.horizon_days} Days)
                      </Badge>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => deleteScenario(s.id)}
                      className="text-slate-400 hover:text-rose-600"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>

                  {s.description && (
                    <p className="mt-2 text-xs text-slate-500">{s.description}</p>
                  )}

                  <div className="mt-4 grid grid-cols-2 gap-3 rounded-lg bg-slate-50 p-3 text-xs dark:bg-slate-800">
                    <div>
                      <span className="text-slate-400">Income Adj:</span>
                      <span className="ml-1 font-semibold text-slate-700 dark:text-slate-300">
                        {s.assumptions.income_change_pct > 0 ? `+${s.assumptions.income_change_pct}%` : `${s.assumptions.income_change_pct}%`}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-400">Expense Adj:</span>
                      <span className="ml-1 font-semibold text-slate-700 dark:text-slate-300">
                        {s.assumptions.expense_change_pct > 0 ? `+${s.assumptions.expense_change_pct}%` : `${s.assumptions.expense_change_pct}%`}
                      </span>
                    </div>
                  </div>

                  <div className="mt-4 border-t border-slate-100 pt-3 dark:border-slate-800">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-slate-500">Projected Ending Balance:</span>
                      <span className="font-bold text-slate-900 dark:text-white">
                        <FinancialAmount amount={Number(s.results.scenario_projected_balance_paise) / 100} currency="INR" />
                      </span>
                    </div>
                    <div className="mt-1 flex items-center justify-between text-xs">
                      <span className="text-slate-500">Delta from Baseline:</span>
                      <span className={`font-bold ${s.results.delta_balance_paise >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                        {s.results.delta_balance_paise > 0 ? '+' : ''}
                        <FinancialAmount amount={Number(s.results.delta_balance_paise) / 100} currency="INR" />
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              title="No Saved Scenarios"
              description="Build a hypothetical scenario to model how unexpected expenses or pay increases affect your ending balance."
            />
          )}
        </div>
      )}

      {/* New Scenario Modal */}
      <Modal
        isOpen={isScenarioModalOpen}
        onClose={() => setIsScenarioModalOpen(false)}
        title="Build Financial What-If Scenario"
      >
        <form onSubmit={handleCreateScenario} className="space-y-4">
          <div>
            <label className="text-xs font-medium text-slate-700 dark:text-slate-300">Scenario Name</label>
            <Input
              value={scenarioName}
              onChange={(e) => setScenarioName(e.target.value)}
              placeholder="e.g. 10% Salary Hike & New Gym Membership"
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-slate-700 dark:text-slate-300">Scenario Type</label>
              <select
                value={scenarioType}
                onChange={(e) => setScenarioType(e.target.value)}
                className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-xs dark:border-slate-700 dark:bg-slate-900 dark:text-white"
              >
                <option value="custom">Custom</option>
                <option value="optimistic">Optimistic</option>
                <option value="conservative">Conservative</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-slate-700 dark:text-slate-300">Income Adjustment (%)</label>
              <Input
                type="number"
                value={incomeChangePct}
                onChange={(e) => setIncomeChangePct(e.target.value)}
                placeholder="e.g. 10 or -5"
              />
            </div>
          </div>

          <div>
            <label className="text-xs font-medium text-slate-700 dark:text-slate-300">Discretionary Expense Adjustment (%)</label>
            <Input
              type="number"
              value={expenseChangePct}
              onChange={(e) => setExpenseChangePct(e.target.value)}
              placeholder="e.g. -15 or 10"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-slate-700 dark:text-slate-300">One-Time Expense (₹)</label>
              <Input
                type="number"
                value={oneTimeExpense}
                onChange={(e) => setOneTimeExpense(e.target.value)}
                placeholder="e.g. 25000"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-700 dark:text-slate-300">Expense Label</label>
              <Input
                value={oneTimeDesc}
                onChange={(e) => setOneTimeDesc(e.target.value)}
                placeholder="e.g. Laptop repair"
              />
            </div>
          </div>

          <div className="flex justify-end gap-2 border-t border-slate-100 pt-4 dark:border-slate-800">
            <Button variant="outline" type="button" onClick={() => setIsScenarioModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit">Run Simulation</Button>
          </div>
        </form>
      </Modal>

      {/* Regenerate Forecast Modal */}
      <Modal
        isOpen={isGenerateModalOpen}
        onClose={() => setIsGenerateModalOpen(false)}
        title="Configure & Regenerate Forecast"
      >
        <div className="space-y-4">
          <div>
            <label className="text-xs font-medium text-slate-700 dark:text-slate-300">Forecasting Model</label>
            <select
              value={prefModel}
              onChange={(e) => setPrefModel(e.target.value)}
              className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-xs dark:border-slate-700 dark:bg-slate-900 dark:text-white"
            >
              <option value="auto">Auto-Select Best (Walk-Forward WAPE)</option>
              <option value="holt_winters">Holt-Winters (Trend + Day-of-Week Seasonality)</option>
              <option value="moving_average">Simple Moving Average (7-Day)</option>
              <option value="exponential_smoothing">Exponential Smoothing (SES)</option>
              <option value="linear_trend">Damped Linear Regression</option>
              <option value="historical_mean">Historical Mean Baseline</option>
            </select>
          </div>

          <div>
            <label className="text-xs font-medium text-slate-700 dark:text-slate-300">Confidence Interval Width</label>
            <select
              value={confLevel}
              onChange={(e) => setConfLevel(e.target.value)}
              className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-xs dark:border-slate-700 dark:bg-slate-900 dark:text-white"
            >
              <option value="0.80">80% Confidence Interval (Standard)</option>
              <option value="0.95">95% Confidence Interval (Conservative)</option>
            </select>
          </div>

          <div className="flex justify-end gap-2 border-t border-slate-100 pt-4 dark:border-slate-800">
            <Button variant="outline" type="button" onClick={() => setIsGenerateModalOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleRunForecast}>Generate</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
