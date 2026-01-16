import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ArrowLeft,
  Play,
  Download,
  Plus,
  Trash2,
  Edit,
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  XCircle,
  Loader2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { api, createWebSocket } from '@/lib/api';
import type { Experiment, EvaluationStatus, EvaluationReport } from '@/lib/types';
import { formatScore, downloadJson } from '@/lib/utils';
import { CaseEditor } from './CaseEditor';
import { EvaluatorEditor } from './EvaluatorEditor';

export function ExperimentDetail() {
  const { id } = useParams<{ id: string }>();
  const [experiment, setExperiment] = useState<Experiment | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [evaluation, setEvaluation] = useState<EvaluationStatus | null>(null);
  const [reports, setReports] = useState<EvaluationReport[]>([]);
  const [expandedCases, setExpandedCases] = useState<Set<number>>(new Set());
  const [deleteCase, setDeleteCase] = useState<string | null>(null);
  const [deleteEvaluator, setDeleteEvaluator] = useState<string | null>(null);
  const [showCaseEditor, setShowCaseEditor] = useState(false);
  const [showEvaluatorEditor, setShowEvaluatorEditor] = useState(false);
  const [editingCase, setEditingCase] = useState<string | null>(null);

  useEffect(() => {
    if (id) {
      loadExperiment();
    }
  }, [id]);

  async function loadExperiment() {
    if (!id) return;
    try {
      setLoading(true);
      const data = await api.experiments.get(id);
      setExperiment(data);
      setError(null);

      const evaluations = await api.evaluations.list(id);
      const completed = evaluations.find(e => e.status === 'completed');
      if (completed) {
        setEvaluation(completed);
        try {
          const reportData = await api.evaluations.getReport(completed.id);
          setReports(reportData.reports);
        } catch {
          // No reports available
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load experiment');
    } finally {
      setLoading(false);
    }
  }

  async function runEvaluation() {
    if (!id) return;
    try {
      const evalStatus = await api.evaluations.runAsync(id);
      setEvaluation(evalStatus);
      setReports([]);

      const ws = createWebSocket(evalStatus.id);
      ws.onmessage = async (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'progress') {
          setEvaluation(prev => prev ? {
            ...prev,
            progress: data.progress,
            current_case: data.current_case,
            status: 'running',
          } : null);
        } else if (data.type === 'completed') {
          setEvaluation(prev => prev ? { ...prev, status: 'completed', progress: 100 } : null);
          try {
            const reportData = await api.evaluations.getReport(evalStatus.id);
            setReports(reportData.reports);
          } catch {
            // Handle error
          }
          ws.close();
        } else if (data.type === 'error') {
          setEvaluation(prev => prev ? { ...prev, status: 'failed', error: data.error } : null);
          ws.close();
        }
      };
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to run evaluation');
    }
  }

  async function handleExport() {
    if (!id) return;
    try {
      const data = await api.experiments.export(id);
      downloadJson(data, `${experiment?.name || 'experiment'}.json`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to export experiment');
    }
  }

  async function handleDeleteCase() {
    if (!id || !deleteCase) return;
    try {
      await api.cases.delete(id, deleteCase);
      await loadExperiment();
      setDeleteCase(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete case');
    }
  }

  async function handleDeleteEvaluator() {
    if (!id || !deleteEvaluator) return;
    try {
      await api.evaluators.delete(id, deleteEvaluator);
      await loadExperiment();
      setDeleteEvaluator(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete evaluator');
    }
  }

  function toggleCase(index: number) {
    const newExpanded = new Set(expandedCases);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedCases(newExpanded);
  }

  if (loading) {
    return (
      <div className="container mx-auto py-8 px-4">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-muted rounded w-1/4" />
          <div className="h-4 bg-muted rounded w-1/2" />
          <div className="h-64 bg-muted rounded" />
        </div>
      </div>
    );
  }

  if (!experiment) {
    return (
      <div className="container mx-auto py-8 px-4">
        <div className="text-center py-12">
          <h2 className="text-xl font-semibold mb-2">Experiment not found</h2>
          <Link to="/">
            <Button variant="outline">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Dashboard
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 px-4">
      <div className="flex items-center gap-4 mb-6">
        <Link to="/">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div className="flex-1">
          <h1 className="text-2xl font-bold">{experiment.name}</h1>
          {experiment.description && (
            <p className="text-muted-foreground">{experiment.description}</p>
          )}
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleExport}>
            <Download className="mr-2 h-4 w-4" />
            Export
          </Button>
          <Button
            onClick={runEvaluation}
            disabled={
              experiment.cases.length === 0 ||
              experiment.evaluators.length === 0 ||
              evaluation?.status === 'running'
            }
          >
            {evaluation?.status === 'running' ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Running...
              </>
            ) : (
              <>
                <Play className="mr-2 h-4 w-4" />
                Run Evaluation
              </>
            )}
          </Button>
        </div>
      </div>

      {error && (
        <div className="bg-destructive/10 text-destructive px-4 py-3 rounded-md mb-6">
          {error}
        </div>
      )}

      {evaluation?.status === 'running' && (
        <Card className="mb-6">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium">Running evaluation...</span>
              <span className="text-sm text-muted-foreground">
                {evaluation.current_case} / {evaluation.total_cases} cases
              </span>
            </div>
            <Progress value={evaluation.progress} />
          </CardContent>
        </Card>
      )}

      <Tabs defaultValue="cases" className="space-y-4">
        <TabsList>
          <TabsTrigger value="cases">
            Cases ({experiment.cases.length})
          </TabsTrigger>
          <TabsTrigger value="evaluators">
            Evaluators ({experiment.evaluators.length})
          </TabsTrigger>
          <TabsTrigger value="results" disabled={reports.length === 0}>
            Results
          </TabsTrigger>
        </TabsList>

        <TabsContent value="cases" className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-semibold">Test Cases</h2>
            <Button onClick={() => setShowCaseEditor(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Add Case
            </Button>
          </div>

          {experiment.cases.length === 0 ? (
            <Card className="text-center py-8">
              <CardContent>
                <p className="text-muted-foreground mb-4">No test cases yet</p>
                <Button onClick={() => setShowCaseEditor(true)}>
                  <Plus className="mr-2 h-4 w-4" />
                  Add First Case
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-2">
              {experiment.cases.map((testCase, index) => (
                <Collapsible
                  key={testCase.id}
                  open={expandedCases.has(index)}
                  onOpenChange={() => toggleCase(index)}
                >
                  <Card>
                    <CollapsibleTrigger asChild>
                      <CardHeader className="cursor-pointer hover:bg-muted/50 transition-colors">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            {expandedCases.has(index) ? (
                              <ChevronDown className="h-4 w-4" />
                            ) : (
                              <ChevronRight className="h-4 w-4" />
                            )}
                            <CardTitle className="text-base">
                              {testCase.name || `Case ${index + 1}`}
                            </CardTitle>
                          </div>
                          <div className="flex items-center gap-2" onClick={e => e.stopPropagation()}>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => {
                                setEditingCase(testCase.id);
                                setShowCaseEditor(true);
                              }}
                            >
                              <Edit className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="text-destructive"
                              onClick={() => setDeleteCase(testCase.id)}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                      </CardHeader>
                    </CollapsibleTrigger>
                    <CollapsibleContent>
                      <CardContent className="pt-0 space-y-4">
                        <div>
                          <h4 className="text-sm font-medium mb-1">Input</h4>
                          <pre className="bg-muted p-3 rounded-md text-sm overflow-auto max-h-40">
                            {typeof testCase.input === 'string'
                              ? testCase.input
                              : JSON.stringify(testCase.input, null, 2)}
                          </pre>
                        </div>
                        {testCase.expected_output !== null && testCase.expected_output !== undefined && (
                          <div>
                            <h4 className="text-sm font-medium mb-1">Expected Output</h4>
                            <pre className="bg-muted p-3 rounded-md text-sm overflow-auto max-h-40">
                              {typeof testCase.expected_output === 'string'
                                ? testCase.expected_output
                                : JSON.stringify(testCase.expected_output, null, 2)}
                            </pre>
                          </div>
                        )}
                        {testCase.expected_trajectory && (
                          <div>
                            <h4 className="text-sm font-medium mb-1">Expected Trajectory</h4>
                            <pre className="bg-muted p-3 rounded-md text-sm overflow-auto max-h-40">
                              {JSON.stringify(testCase.expected_trajectory, null, 2)}
                            </pre>
                          </div>
                        )}
                        {testCase.metadata && (
                          <div>
                            <h4 className="text-sm font-medium mb-1">Metadata</h4>
                            <pre className="bg-muted p-3 rounded-md text-sm overflow-auto max-h-40">
                              {JSON.stringify(testCase.metadata, null, 2)}
                            </pre>
                          </div>
                        )}
                      </CardContent>
                    </CollapsibleContent>
                  </Card>
                </Collapsible>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="evaluators" className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-semibold">Evaluators</h2>
            <Button onClick={() => setShowEvaluatorEditor(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Add Evaluator
            </Button>
          </div>

          {experiment.evaluators.length === 0 ? (
            <Card className="text-center py-8">
              <CardContent>
                <p className="text-muted-foreground mb-4">No evaluators configured</p>
                <Button onClick={() => setShowEvaluatorEditor(true)}>
                  <Plus className="mr-2 h-4 w-4" />
                  Add Evaluator
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4">
              {experiment.evaluators.map((evaluator, index) => (
                <Card key={evaluator.id || index}>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <div>
                        <CardTitle className="text-base">{evaluator.evaluator_type}</CardTitle>
                        {evaluator.rubric && (
                          <CardDescription className="mt-1 line-clamp-2">
                            {evaluator.rubric}
                          </CardDescription>
                        )}
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="text-destructive"
                        onClick={() => setDeleteEvaluator(evaluator.id || '')}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </CardHeader>
                  {(evaluator.model_id || evaluator.include_inputs !== undefined) && (
                    <CardContent className="pt-0">
                      <div className="flex gap-2 flex-wrap">
                        {evaluator.model_id && (
                          <Badge variant="secondary">{evaluator.model_id}</Badge>
                        )}
                        {evaluator.include_inputs !== undefined && (
                          <Badge variant="outline">
                            {evaluator.include_inputs ? 'Includes inputs' : 'No inputs'}
                          </Badge>
                        )}
                      </div>
                    </CardContent>
                  )}
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="results" className="space-y-4">
          {reports.map((report, reportIndex) => (
            <Card key={reportIndex}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>
                      {experiment.evaluators[reportIndex]?.evaluator_type || `Evaluator ${reportIndex + 1}`}
                    </CardTitle>
                    <CardDescription>
                      Overall Score: {formatScore(report.overall_score)}
                    </CardDescription>
                  </div>
                  <div className="text-right">
                    <div className="text-2xl font-bold">{formatScore(report.overall_score)}</div>
                    <div className="text-sm text-muted-foreground">
                      {report.test_passes.filter(Boolean).length} / {report.test_passes.length} passed
                    </div>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {report.cases.map((caseResult, caseIndex) => (
                    <Collapsible key={caseIndex}>
                      <CollapsibleTrigger asChild>
                        <div className="flex items-center justify-between p-3 bg-muted rounded-md cursor-pointer hover:bg-muted/80 transition-colors">
                          <div className="flex items-center gap-3">
                            {report.test_passes[caseIndex] ? (
                              <CheckCircle2 className="h-5 w-5 text-green-500" />
                            ) : (
                              <XCircle className="h-5 w-5 text-red-500" />
                            )}
                            <span className="font-medium">
                              {caseResult.name || `Case ${caseIndex + 1}`}
                            </span>
                          </div>
                          <div className="flex items-center gap-4">
                            <Badge variant={report.test_passes[caseIndex] ? 'default' : 'destructive'}>
                              {formatScore(report.scores[caseIndex])}
                            </Badge>
                            <ChevronDown className="h-4 w-4" />
                          </div>
                        </div>
                      </CollapsibleTrigger>
                      <CollapsibleContent>
                        <div className="p-4 border-l-2 border-muted ml-2 mt-2 space-y-3">
                          <div>
                            <h4 className="text-sm font-medium mb-1">Input</h4>
                            <pre className="bg-muted/50 p-2 rounded text-sm overflow-auto max-h-32">
                              {typeof caseResult.input === 'string'
                                ? caseResult.input
                                : JSON.stringify(caseResult.input, null, 2)}
                            </pre>
                          </div>
                          {caseResult.actual_output !== null && caseResult.actual_output !== undefined && (
                            <div>
                              <h4 className="text-sm font-medium mb-1">Actual Output</h4>
                              <pre className="bg-muted/50 p-2 rounded text-sm overflow-auto max-h-32">
                                {typeof caseResult.actual_output === 'string'
                                  ? caseResult.actual_output
                                  : JSON.stringify(caseResult.actual_output, null, 2)}
                              </pre>
                            </div>
                          )}
                          {report.reasons[caseIndex] && (
                            <div>
                              <h4 className="text-sm font-medium mb-1">Reason</h4>
                              <p className="text-sm text-muted-foreground">
                                {report.reasons[caseIndex]}
                              </p>
                            </div>
                          )}
                        </div>
                      </CollapsibleContent>
                    </Collapsible>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </TabsContent>
      </Tabs>

      {showCaseEditor && (
        <CaseEditor
          experimentId={id!}
          caseId={editingCase}
          existingCase={editingCase ? experiment.cases.find(c => c.id === editingCase) : undefined}
          onClose={() => {
            setShowCaseEditor(false);
            setEditingCase(null);
          }}
          onSave={() => {
            setShowCaseEditor(false);
            setEditingCase(null);
            loadExperiment();
          }}
        />
      )}

      {showEvaluatorEditor && (
        <EvaluatorEditor
          experimentId={id!}
          onClose={() => setShowEvaluatorEditor(false)}
          onSave={() => {
            setShowEvaluatorEditor(false);
            loadExperiment();
          }}
        />
      )}

      <AlertDialog open={!!deleteCase} onOpenChange={() => setDeleteCase(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Case</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this test case? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDeleteCase} className="bg-destructive text-destructive-foreground">
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={!!deleteEvaluator} onOpenChange={() => setDeleteEvaluator(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Evaluator</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to remove this evaluator? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDeleteEvaluator} className="bg-destructive text-destructive-foreground">
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
