import { create } from 'zustand';
import type { Dataset, Driver, DashboardState } from '../data/types';
import { loadDataset } from '../data/loader';
import { predictGoals, type ProposedGoal } from '../agent/tools';
import { runAgent, type ChosenGoal, type Shock } from '../agent/supervisor';
import type { Answer } from '../agent/ask';

export type Screen =
  | 'onboarding'
  | 'discovery'
  | 'dashboard'
  | 'goal'
  | 'route'
  | 'unlocks'
  | 'reasoning'
  | 'architecture'
  | 'ask';

interface ChatMsg {
  role: 'me' | 'ai';
  text: string;
  source?: string;
}

interface SarthiState {
  ds: Dataset | null;
  loading: boolean;
  error: string | null;

  screen: Screen;
  tab: 'dashboard' | 'route' | 'unlocks' | 'ask';
  driver: Driver | null;

  proposed: ProposedGoal[];
  chosen: ChosenGoal[];
  state: DashboardState | null;
  replanning: boolean;
  focusGoalId: string | null;

  chat: ChatMsg[];

  init: () => Promise<void>;
  pickDriver: (id: string) => void;
  confirmGoals: (chosen: ChosenGoal[]) => void;
  go: (screen: Screen) => void;
  setTab: (tab: SarthiState['tab']) => void;
  openGoal: (goalId: string) => void;
  replan: (shock: Shock) => Promise<void>;
  pushChat: (m: ChatMsg) => void;
}

export const useSarthi = create<SarthiState>((set, get) => ({
  ds: null,
  loading: true,
  error: null,
  screen: 'onboarding',
  tab: 'dashboard',
  driver: null,
  proposed: [],
  chosen: [],
  state: null,
  replanning: false,
  focusGoalId: null,
  chat: [
    {
      role: 'ai',
      text: 'Ask me about your runway, income, spending, goals or the CPF decision. Every answer traces to your data.',
      source: 'supervisor',
    },
  ],

  init: async () => {
    try {
      const ds = await loadDataset();
      set({ ds, loading: false });
    } catch (e) {
      set({ loading: false, error: (e as Error).message });
    }
  },

  pickDriver: (id) => {
    const ds = get().ds;
    if (!ds) return;
    const driver = ds.drivers.find((d) => d.driver_id === id) ?? null;
    if (!driver) return;
    const proposed = predictGoals(ds, driver);
    set({ driver, proposed, screen: 'discovery', chosen: [], state: null });
  },

  confirmGoals: (chosen) => {
    const { ds, driver } = get();
    if (!ds || !driver) return;
    const state = runAgent(ds, driver, chosen, null);
    set({ chosen, state, screen: 'dashboard', tab: 'dashboard' });
  },

  go: (screen) => set({ screen }),
  setTab: (tab) =>
    set({
      tab,
      screen:
        tab === 'dashboard'
          ? 'dashboard'
          : tab === 'route'
            ? 'route'
            : tab === 'unlocks'
              ? 'unlocks'
              : 'ask',
    }),
  openGoal: (goalId) => set({ focusGoalId: goalId, screen: 'goal' }),

  replan: async (shock) => {
    const { ds, driver, chosen } = get();
    if (!ds || !driver) return;
    set({ replanning: true });
    await new Promise((r) => setTimeout(r, 1300)); // agent step text streams here
    const state = runAgent(ds, driver, chosen, shock);
    set({ replanning: false, state, screen: 'dashboard', tab: 'dashboard' });
  },

  pushChat: (m) => set({ chat: [...get().chat, m] }),
}));

export type { Answer };
