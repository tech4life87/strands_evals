import type {
  Case,
  CaseCreate,
  EvaluationResult,
  EvaluationStatus,
  EvaluatorConfig,
  EvaluatorTypeInfo,
  Experiment,
  ExperimentListItem,
} from './types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

export const api = {
  experiments: {
    list: () => fetchApi<ExperimentListItem[]>('/api/experiments'),

    get: (id: string) => fetchApi<Experiment>(`/api/experiments/${id}`),

    create: (data: {
      name: string;
      description?: string;
      cases?: CaseCreate[];
      evaluators?: EvaluatorConfig[];
    }) =>
      fetchApi<Experiment>('/api/experiments', {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    update: (id: string, data: { name?: string; description?: string }) =>
      fetchApi<Experiment>(`/api/experiments/${id}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      }),

    delete: (id: string) =>
      fetchApi<{ message: string }>(`/api/experiments/${id}`, {
        method: 'DELETE',
      }),

    import: (data: Record<string, unknown>, name?: string) =>
      fetchApi<Experiment>('/api/experiments/import', {
        method: 'POST',
        body: JSON.stringify({ data, name }),
      }),

    export: (id: string) =>
      fetchApi<Record<string, unknown>>(`/api/experiments/${id}/export`),
  },

  cases: {
    list: (experimentId: string) =>
      fetchApi<Case[]>(`/api/experiments/${experimentId}/cases`),

    add: (experimentId: string, data: CaseCreate) =>
      fetchApi<Case>(`/api/experiments/${experimentId}/cases`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    update: (experimentId: string, caseId: string, data: Partial<CaseCreate>) =>
      fetchApi<Case>(`/api/experiments/${experimentId}/cases/${caseId}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      }),

    delete: (experimentId: string, caseId: string) =>
      fetchApi<{ message: string }>(
        `/api/experiments/${experimentId}/cases/${caseId}`,
        { method: 'DELETE' }
      ),

    bulkCreate: (experimentId: string, cases: CaseCreate[]) =>
      fetchApi<Case[]>(`/api/experiments/${experimentId}/cases/bulk`, {
        method: 'POST',
        body: JSON.stringify({ cases }),
      }),
  },

  evaluators: {
    listTypes: () => fetchApi<EvaluatorTypeInfo[]>('/api/evaluators'),

    add: (experimentId: string, config: EvaluatorConfig) =>
      fetchApi<EvaluatorConfig>(
        `/api/experiments/${experimentId}/evaluators`,
        {
          method: 'POST',
          body: JSON.stringify(config),
        }
      ),

    delete: (experimentId: string, evaluatorId: string) =>
      fetchApi<{ message: string }>(
        `/api/experiments/${experimentId}/evaluators/${evaluatorId}`,
        { method: 'DELETE' }
      ),
  },

  evaluations: {
    run: (experimentId: string, maxWorkers?: number) =>
      fetchApi<EvaluationStatus>(`/api/experiments/${experimentId}/run`, {
        method: 'POST',
        body: JSON.stringify({ max_workers: maxWorkers || 10 }),
      }),

    runAsync: (experimentId: string, maxWorkers?: number) =>
      fetchApi<EvaluationStatus>(`/api/experiments/${experimentId}/run-async`, {
        method: 'POST',
        body: JSON.stringify({ max_workers: maxWorkers || 10 }),
      }),

    getStatus: (evaluationId: string) =>
      fetchApi<EvaluationStatus>(`/api/evaluations/${evaluationId}/status`),

    getReport: (evaluationId: string) =>
      fetchApi<EvaluationResult>(`/api/evaluations/${evaluationId}/report`),

    export: (evaluationId: string) =>
      fetchApi<Record<string, unknown>>(`/api/evaluations/${evaluationId}/export`),

    list: (experimentId: string) =>
      fetchApi<EvaluationStatus[]>(`/api/experiments/${experimentId}/evaluations`),
  },
};

export function createWebSocket(evaluationId: string): WebSocket {
  const wsUrl = API_BASE.replace(/^http/, 'ws');
  return new WebSocket(`${wsUrl}/ws/evaluations/${evaluationId}`);
}
