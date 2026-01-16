import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { api } from '@/lib/api';
import type { Case } from '@/lib/types';

interface CaseEditorProps {
  experimentId: string;
  caseId?: string | null;
  existingCase?: Case;
  onClose: () => void;
  onSave: () => void;
}

export function CaseEditor({ experimentId, caseId, existingCase, onClose, onSave }: CaseEditorProps) {
  const [name, setName] = useState(existingCase?.name || '');
  const [input, setInput] = useState(
    existingCase?.input
      ? typeof existingCase.input === 'string'
        ? existingCase.input
        : JSON.stringify(existingCase.input, null, 2)
      : ''
  );
  const [expectedOutput, setExpectedOutput] = useState(
    existingCase?.expected_output
      ? typeof existingCase.expected_output === 'string'
        ? existingCase.expected_output
        : JSON.stringify(existingCase.expected_output, null, 2)
      : ''
  );
  const [expectedTrajectory, setExpectedTrajectory] = useState(
    existingCase?.expected_trajectory
      ? JSON.stringify(existingCase.expected_trajectory, null, 2)
      : ''
  );
  const [metadata, setMetadata] = useState(
    existingCase?.metadata
      ? JSON.stringify(existingCase.metadata, null, 2)
      : ''
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function parseJsonOrString(value: string): unknown {
    if (!value.trim()) return null;
    try {
      return JSON.parse(value);
    } catch {
      return value;
    }
  }

  async function handleSave() {
    if (!input.trim()) {
      setError('Input is required');
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const caseData = {
        name: name.trim() || null,
        input: parseJsonOrString(input),
        expected_output: parseJsonOrString(expectedOutput),
        expected_trajectory: expectedTrajectory.trim() ? JSON.parse(expectedTrajectory) : null,
        metadata: metadata.trim() ? JSON.parse(metadata) : null,
      };

      if (caseId) {
        await api.cases.update(experimentId, caseId, caseData);
      } else {
        await api.cases.add(experimentId, caseData);
      }

      onSave();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save case');
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{caseId ? 'Edit Case' : 'Add New Case'}</DialogTitle>
          <DialogDescription>
            Define a test case with input and expected output for evaluation.
          </DialogDescription>
        </DialogHeader>

        {error && (
          <div className="bg-destructive/10 text-destructive px-4 py-3 rounded-md text-sm">
            {error}
          </div>
        )}

        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">Name (optional)</Label>
            <Input
              id="name"
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="e.g., Simple Math Test"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="input">Input *</Label>
            <Textarea
              id="input"
              value={input}
              onChange={e => setInput(e.target.value)}
              placeholder="Enter the input for this test case (text or JSON)"
              rows={4}
              className="font-mono text-sm"
            />
            <p className="text-xs text-muted-foreground">
              The input to the task, e.g., the query to the agent
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="expectedOutput">Expected Output (optional)</Label>
            <Textarea
              id="expectedOutput"
              value={expectedOutput}
              onChange={e => setExpectedOutput(e.target.value)}
              placeholder="Enter the expected output (text or JSON)"
              rows={4}
              className="font-mono text-sm"
            />
            <p className="text-xs text-muted-foreground">
              The expected response given the input
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="expectedTrajectory">Expected Trajectory (optional)</Label>
            <Textarea
              id="expectedTrajectory"
              value={expectedTrajectory}
              onChange={e => setExpectedTrajectory(e.target.value)}
              placeholder='["tool1", "tool2", "tool3"]'
              rows={3}
              className="font-mono text-sm"
            />
            <p className="text-xs text-muted-foreground">
              JSON array of expected tool calls or actions
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="metadata">Metadata (optional)</Label>
            <Textarea
              id="metadata"
              value={metadata}
              onChange={e => setMetadata(e.target.value)}
              placeholder='{"category": "math", "difficulty": "easy"}'
              rows={3}
              className="font-mono text-sm"
            />
            <p className="text-xs text-muted-foreground">
              JSON object with additional information about the test case
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? 'Saving...' : caseId ? 'Update Case' : 'Add Case'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
