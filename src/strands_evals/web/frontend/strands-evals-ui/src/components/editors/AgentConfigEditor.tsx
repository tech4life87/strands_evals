'use client';

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
import type { AgentConfig } from '@/lib/types';

interface AgentConfigEditorProps {
  experimentId: string;
  currentConfig?: AgentConfig | null;
  onClose: () => void;
  onSave: () => void;
}

export function AgentConfigEditor({ experimentId, currentConfig, onClose, onSave }: AgentConfigEditorProps) {
  const [modelId, setModelId] = useState(currentConfig?.model_id || '');
  const [systemPrompt, setSystemPrompt] = useState(currentConfig?.system_prompt || '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSave() {
    setSaving(true);
    setError(null);

    try {
      const agentConfig: AgentConfig = {};
      
      if (modelId.trim()) {
        agentConfig.model_id = modelId.trim();
      }
      if (systemPrompt.trim()) {
        agentConfig.system_prompt = systemPrompt.trim();
      }

      await api.experiments.update(experimentId, {
        agent_config: agentConfig,
      });
      onSave();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save agent configuration');
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Configure Agent</DialogTitle>
          <DialogDescription>
            Configure the AI agent that will be used to process test cases during evaluation.
            The agent will receive each case input and generate a response.
          </DialogDescription>
        </DialogHeader>

        {error && (
          <div className="bg-destructive/10 text-destructive px-4 py-3 rounded-md text-sm">
            {error}
          </div>
        )}

        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="modelId">Model ID</Label>
            <Input
              id="modelId"
              value={modelId}
              onChange={e => setModelId(e.target.value)}
              placeholder="e.g., us.anthropic.claude-sonnet-4-20250514-v1:0"
            />
            <p className="text-xs text-muted-foreground">
              The model identifier to use for the agent. Leave empty to use the default model.
              Examples: us.anthropic.claude-sonnet-4-20250514-v1:0, anthropic.claude-3-haiku-20240307-v1:0
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="systemPrompt">System Prompt</Label>
            <Textarea
              id="systemPrompt"
              value={systemPrompt}
              onChange={e => setSystemPrompt(e.target.value)}
              placeholder="Enter a system prompt for the agent..."
              rows={6}
            />
            <p className="text-xs text-muted-foreground">
              The system prompt that defines the agent&apos;s behavior and capabilities.
              This will be used for all test cases in the evaluation.
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? 'Saving...' : 'Save Configuration'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
