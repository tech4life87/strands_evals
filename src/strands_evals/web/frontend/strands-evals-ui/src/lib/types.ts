export interface Case {
  id: string;
  name: string | null;
  session_id: string;
  input: unknown;
  expected_output: unknown | null;
  expected_trajectory: unknown[] | null;
  expected_interactions: Record<string, unknown>[] | null;
  metadata: Record<string, unknown> | null;
}

export interface CaseCreate {
  name?: string | null;
  input: unknown;
  expected_output?: unknown | null;
  expected_trajectory?: unknown[] | null;
  expected_interactions?: Record<string, unknown>[] | null;
  metadata?: Record<string, unknown> | null;
}

export interface EvaluatorConfig {
  id?: string;
  evaluator_type: string;
  rubric?: string | null;
  model_id?: string | null;
  system_prompt?: string | null;
  include_inputs?: boolean;
  trajectory_description?: Record<string, unknown> | null;
}

export interface Experiment {
  id: string;
  name: string;
  description: string | null;
  cases: Case[];
  evaluators: EvaluatorConfig[];
  created_at: string;
  updated_at: string;
}

export interface ExperimentListItem {
  id: string;
  name: string;
  description: string | null;
  case_count: number;
  evaluator_count: number;
  created_at: string;
  updated_at: string;
}

export interface EvaluatorTypeInfo {
  name: string;
  description: string;
  parameters: {
    name: string;
    type: string;
    required: boolean;
    description: string;
  }[];
}

export interface EvaluationStatus {
  id: string;
  experiment_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  current_case: number;
  total_cases: number;
  started_at: string | null;
  completed_at: string | null;
  error: string | null;
}

export interface CaseResult {
  name?: string;
  input: unknown;
  expected_output?: unknown;
  actual_output?: unknown;
}

export interface EvaluationReport {
  overall_score: number;
  scores: number[];
  test_passes: boolean[];
  cases: CaseResult[];
  reasons: string[];
  detailed_results: Record<string, unknown>[][];
}

export interface EvaluationResult {
  id: string;
  experiment_id: string;
  reports: EvaluationReport[];
  created_at: string;
}
