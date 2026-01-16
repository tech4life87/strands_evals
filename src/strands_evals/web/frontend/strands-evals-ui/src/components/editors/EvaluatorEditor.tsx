'use client';

import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { api } from '@/lib/api';
import type { EvaluatorTypeInfo, EvaluatorConfig } from '@/lib/types';

interface EvaluatorEditorProps {
  experimentId: string;
  onClose: () => void;
  onSave: () => void;
}

export function EvaluatorEditor({ experimentId, onClose, onSave }: EvaluatorEditorProps) {
  const [evaluatorTypes, setEvaluatorTypes] = useState<EvaluatorTypeInfo[]>([]);
  const [selectedType, setSelectedType] = useState<string>('');
  const [rubric, setRubric] = useState('');
  const [modelId, setModelId] = useState('');
  const [includeInputs, setIncludeInputs] = useState(true);
  const [trajectoryDescription, setTrajectoryDescription] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadEvaluatorTypes();
  }, []);

  async function loadEvaluatorTypes() {
    try {
      const types = await api.evaluators.listTypes();
      setEvaluatorTypes(types);
      if (types.length > 0) {
        setSelectedType(types[0].name);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load evaluator types');
    } finally {
      setLoading(false);
    }
  }

  const selectedEvaluator = evaluatorTypes.find(e => e.name === selectedType);
  const requiresRubric = selectedEvaluator?.parameters.some(p => p.name === 'rubric' && p.required);
  const supportsModel = selectedEvaluator?.parameters.some(p => p.name === 'model_id');
  const supportsIncludeInputs = selectedEvaluator?.parameters.some(p => p.name === 'include_inputs');
  const supportsTrajectoryDescription = selectedEvaluator?.parameters.some(p => p.name === 'trajectory_description');

  async function handleSave() {
    if (requiresRubric && !rubric.trim()) {
      setError('Rubric is required for this evaluator');
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const config: EvaluatorConfig = {
        evaluator_type: selectedType,
      };

      if (rubric.trim()) {
        config.rubric = rubric.trim();
      }
      if (modelId.trim()) {
        config.model_id = modelId.trim();
      }
      if (supportsIncludeInputs) {
        config.include_inputs = includeInputs;
      }
      if (trajectoryDescription.trim()) {
        try {
          config.trajectory_description = JSON.parse(trajectoryDescription);
        } catch {
          setError('Invalid JSON for trajectory description');
          setSaving(false);
          return;
        }
      }

      await api.evaluators.add(experimentId, config);
      onSave();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add evaluator');
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Add Evaluator</DialogTitle>
          <DialogDescription>
            Configure an evaluator to assess your test cases.
          </DialogDescription>
        </DialogHeader>

        {error && (
          <div className="bg-destructive/10 text-destructive px-4 py-3 rounded-md text-sm">
            {error}
          </div>
        )}

        {loading ? (
          <div className="py-8 text-center text-muted-foreground">
            Loading evaluator types...
          </div>
        ) : (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="evaluatorType">Evaluator Type</Label>
              <Select value={selectedType} onValueChange={setSelectedType}>
                <SelectTrigger>
                  <SelectValue placeholder="Select an evaluator type" />
                </SelectTrigger>
                <SelectContent>
                  {evaluatorTypes.map(type => (
                    <SelectItem key={type.name} value={type.name}>
                      {type.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {selectedEvaluator && (
                <p className="text-xs text-muted-foreground">
                  {selectedEvaluator.description}
                </p>
              )}
            </div>

            {(requiresRubric || selectedEvaluator?.parameters.some(p => p.name === 'rubric')) && (
              <div className="space-y-2">
                <Label htmlFor="rubric">
                  Rubric {requiresRubric && '*'}
                </Label>
                <Textarea
                  id="rubric"
                  value={rubric}
                  onChange={e => setRubric(e.target.value)}
                  placeholder="Enter the evaluation criteria..."
                  rows={4}
                />
                <p className="text-xs text-muted-foreground">
                  The criteria used to evaluate test cases
                </p>
              </div>
            )}

            {supportsModel && (
              <div className="space-y-2">
                <Label htmlFor="modelId">Model ID (optional)</Label>
                <Input
                  id="modelId"
                  value={modelId}
                  onChange={e => setModelId(e.target.value)}
                  placeholder="e.g., us.anthropic.claude-sonnet-4-20250514-v1:0"
                />
                <p className="text-xs text-muted-foreground">
                  The model to use for evaluation. Leave empty for default.
                </p>
              </div>
            )}

            {supportsIncludeInputs && (
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Include Inputs</Label>
                  <p className="text-xs text-muted-foreground">
                    Include task inputs in the evaluation context
                  </p>
                </div>
                <Switch
                  checked={includeInputs}
                  onCheckedChange={setIncludeInputs}
                />
              </div>
            )}

            {supportsTrajectoryDescription && (
              <div className="space-y-2">
                <Label htmlFor="trajectoryDescription">Trajectory Description (optional)</Label>
                <Textarea
                  id="trajectoryDescription"
                  value={trajectoryDescription}
                  onChange={e => setTrajectoryDescription(e.target.value)}
                  placeholder='{"tool1": "Description of tool1", "tool2": "Description of tool2"}'
                  rows={3}
                  className="font-mono text-sm"
                />
                <p className="text-xs text-muted-foreground">
                  JSON object describing available trajectory types
                </p>
              </div>
            )}
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={saving || loading}>
            {saving ? 'Adding...' : 'Add Evaluator'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
