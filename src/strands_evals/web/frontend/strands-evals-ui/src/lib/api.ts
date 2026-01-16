import type {
  Experiment,
  ExperimentListItem,
  Case,
  CaseCreate,
  EvaluatorConfig,
  EvaluatorTypeInfo,
  EvaluationStatus,
  EvaluationReport,
} from './types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
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
    
    create: (data: { name: string; description?: string }) =>
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
      fetchApi<void>(`/api/experiments/${id}`, { method: 'DELETE' }),
    
    export: (id: string) => fetchApi<Record<string, unknown>>(`/api/experiments/${id}/export`),
    
    import: (data: Record<string, unknown>) =>
      fetchApi<Experiment>('/api/experiments/import', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
  },

  cases: {
    list: (experimentId: string) =>
      fetchApi<Case[]>(`/api/experiments/${experimentId}/cases`),
    
    create: (experimentId: string, data: CaseCreate) =>
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
      fetchApi<void>(`/api/experiments/${experimentId}/cases/${caseId}`, {
        method: 'DELETE',
      }),
    
    bulkCreate: (experimentId: string, cases: CaseCreate[]) =>
      fetchApi<Case[]>(`/api/experiments/${experimentId}/cases/bulk`, {
        method: 'POST',
        body: JSON.stringify(cases),
      }),
  },

  evaluators: {
    listTypes: () => fetchApi<EvaluatorTypeInfo[]>('/api/evaluators'),
    
    add: (experimentId: string, config: EvaluatorConfig) =>
      fetchApi<Experiment>(`/api/experiments/${experimentId}/evaluators`, {
        method: 'POST',
        body: JSON.stringify(config),
      }),
    
    remove: (experimentId: string, evaluatorId: string) =>
      fetchApi<Experiment>(`/api/experiments/${experimentId}/evaluators/${evaluatorId}`, {
        method: 'DELETE',
      }),
  },

  evaluations: {
    run: (experimentId: string) =>
      fetchApi<EvaluationStatus>(`/api/experiments/${experimentId}/run`, {
        method: 'POST',
      }),
    
    runAsync: (experimentId: string, maxWorkers?: number) =>
      fetchApi<EvaluationStatus>(`/api/experiments/${experimentId}/run-async`, {
        method: 'POST',
        body: JSON.stringify({ max_workers: maxWorkers }),
      }),
    
    getStatus: (evaluationId: string) =>
      fetchApi<EvaluationStatus>(`/api/evaluations/${evaluationId}/status`),
    
    getReport: (evaluationId: string) =>
      fetchApi<EvaluationReport[]>(`/api/evaluations/${evaluationId}/report`),
  },
};

export function createWebSocket(evaluationId: string): WebSocket {
  const wsUrl = API_BASE_URL.replace(/^http/, 'ws');
  return new WebSocket(`${wsUrl}/ws/evaluations/${evaluationId}`);
}
