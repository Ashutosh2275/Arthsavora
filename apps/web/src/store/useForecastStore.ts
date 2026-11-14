import { create } from 'zustand';
import type {
  BudgetExhaustionResponse,
  CashFlowForecastResponse,
  CategoryForecastResponse,
  EvaluationResponse,
  ExpenseForecastResponse,
  ForecastGenerateRequest,
  GoalTrajectoryResponse,
  IncomeForecastResponse,
  ScenarioCreateRequest,
  ScenarioResponse,
} from '@arthsavora/contracts';
import api from '@/lib/axios';

interface ForecastState {
  cashFlowForecast: CashFlowForecastResponse | null;
  incomeForecast: IncomeForecastResponse | null;
  expenseForecast: ExpenseForecastResponse | null;
  categoryForecast: CategoryForecastResponse | null;
  budgetExhaustion: BudgetExhaustionResponse | null;
  goalTrajectories: GoalTrajectoryResponse | null;
  scenarios: ScenarioResponse[];
  evaluations: EvaluationResponse[];
  selectedHorizon: number;
  isLoading: boolean;
  error: string | null;

  setSelectedHorizon: (horizon: number) => void;
  fetchForecastOverview: (horizon?: number) => Promise<void>;
  generateForecast: (payload: ForecastGenerateRequest) => Promise<void>;
  fetchBudgetExhaustion: () => Promise<void>;
  fetchGoalTrajectories: () => Promise<void>;
  fetchScenarios: () => Promise<void>;
  createScenario: (payload: ScenarioCreateRequest) => Promise<ScenarioResponse>;
  deleteScenario: (scenarioId: string) => Promise<void>;
  fetchEvaluations: () => Promise<void>;
}

export const useForecastStore = create<ForecastState>((set, get) => ({
  cashFlowForecast: null,
  incomeForecast: null,
  expenseForecast: null,
  categoryForecast: null,
  budgetExhaustion: null,
  goalTrajectories: null,
  scenarios: [],
  evaluations: [],
  selectedHorizon: 30,
  isLoading: false,
  error: null,

  setSelectedHorizon: (horizon: number) => {
    set({ selectedHorizon: horizon });
  },

  fetchForecastOverview: async (horizon?: number) => {
    const h = horizon ?? get().selectedHorizon;
    set({ isLoading: true, error: null });
    try {
      const [cfRes, incRes, expRes, catRes] = await Promise.all([
        api.get<{ data: CashFlowForecastResponse }>(`/v1/forecasts/cash-flow?horizon_days=${h}`),
        api.get<{ data: IncomeForecastResponse }>(`/v1/forecasts/income?horizon_days=${h}`),
        api.get<{ data: ExpenseForecastResponse }>(`/v1/forecasts/expenses?horizon_days=${h}`),
        api.get<{ data: CategoryForecastResponse }>(`/v1/forecasts/categories?horizon_days=${h}`),
      ]);

      set({
        cashFlowForecast: cfRes.data?.data,
        incomeForecast: incRes.data?.data,
        expenseForecast: expRes.data?.data,
        categoryForecast: catRes.data?.data,
        selectedHorizon: h,
        isLoading: false,
      });
    } catch (err: any) {
      set({
        error: err.response?.data?.message || err.message || 'Failed to fetch financial forecast',
        isLoading: false,
      });
    }
  },

  generateForecast: async (payload: ForecastGenerateRequest) => {
    set({ isLoading: true, error: null });
    try {
      const res = await api.post<{ data: CashFlowForecastResponse }>(
        '/v1/forecasts/generate',
        payload
      );
      set({
        cashFlowForecast: res.data?.data,
        selectedHorizon: payload.horizon_days ?? 30,
        isLoading: false,
      });
      await Promise.all([
        get().fetchForecastOverview(payload.horizon_days ?? 30),
        get().fetchEvaluations(),
      ]);
    } catch (err: any) {
      set({
        error: err.response?.data?.message || err.message || 'Failed to generate financial forecast',
        isLoading: false,
      });
    }
  },

  fetchBudgetExhaustion: async () => {
    try {
      const res = await api.get<{ data: BudgetExhaustionResponse }>(
        '/v1/forecasts/budget-exhaustion'
      );
      set({ budgetExhaustion: res.data?.data });
    } catch (err: any) {
      console.error('Failed to fetch budget exhaustion estimates:', err);
    }
  },

  fetchGoalTrajectories: async () => {
    try {
      const res = await api.get<{ data: GoalTrajectoryResponse }>(
        '/v1/forecasts/goals'
      );
      set({ goalTrajectories: res.data?.data });
    } catch (err: any) {
      console.error('Failed to fetch goal trajectories:', err);
    }
  },

  fetchScenarios: async () => {
    try {
      const res = await api.get<{ data: ScenarioResponse[] }>(
        '/v1/forecasts/scenarios'
      );
      set({ scenarios: res.data?.data || [] });
    } catch (err: any) {
      console.error('Failed to fetch scenarios:', err);
    }
  },

  createScenario: async (payload: ScenarioCreateRequest) => {
    set({ isLoading: true, error: null });
    try {
      const res = await api.post<{ data: ScenarioResponse }>(
        '/v1/forecasts/scenarios',
        payload
      );
      const newScen = res.data?.data;
      set((state) => ({
        scenarios: [newScen, ...state.scenarios],
        isLoading: false,
      }));
      return newScen;
    } catch (err: any) {
      set({
        error: err.response?.data?.message || err.message || 'Failed to create scenario',
        isLoading: false,
      });
      throw err;
    }
  },

  deleteScenario: async (scenarioId: string) => {
    try {
      await api.delete(`/v1/forecasts/scenarios/${scenarioId}`);
      set((state) => ({
        scenarios: state.scenarios.filter((s) => s.id !== scenarioId),
      }));
    } catch (err: any) {
      console.error('Failed to delete scenario:', err);
    }
  },

  fetchEvaluations: async () => {
    try {
      const res = await api.get<{ data: EvaluationResponse[] }>(
        '/v1/forecasts/evaluations'
      );
      set({ evaluations: res.data?.data || [] });
    } catch (err: any) {
      console.error('Failed to fetch evaluations:', err);
    }
  },
}));
