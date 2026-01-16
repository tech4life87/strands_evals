'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Plus, Trash2, FileText, Users } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
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
import { api } from '@/lib/api';
import type { ExperimentListItem } from '@/lib/types';
import { formatDate } from '@/lib/utils';

export default function Dashboard() {
  const [experiments, setExperiments] = useState<ExperimentListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleteId, setDeleteId] = useState<string | null>(null);

  useEffect(() => {
    loadExperiments();
  }, []);

  async function loadExperiments() {
    try {
      const data = await api.experiments.list();
      setExperiments(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load experiments');
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete() {
    if (!deleteId) return;
    try {
      await api.experiments.delete(deleteId);
      setExperiments(experiments.filter(e => e.id !== deleteId));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete experiment');
    } finally {
      setDeleteId(null);
    }
  }

  if (loading) {
    return (
      <div className="container mx-auto py-8 px-4">
        <div className="text-center text-muted-foreground">Loading experiments...</div>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 px-4">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold">Strands Evals</h1>
          <p className="text-muted-foreground">Evaluation framework for AI agents and LLM applications</p>
        </div>
        <Link href="/experiments/new">
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            New Experiment
          </Button>
        </Link>
      </div>

      {error && (
        <div className="bg-destructive/10 text-destructive px-4 py-3 rounded-md mb-6">
          {error}
        </div>
      )}

      {experiments.length === 0 ? (
        <Card className="text-center py-12">
          <CardContent>
            <p className="text-muted-foreground mb-4">No experiments yet. Create your first experiment to get started.</p>
            <Link href="/experiments/new">
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                Create Experiment
              </Button>
            </Link>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {experiments.map(experiment => (
            <Card key={experiment.id} className="hover:shadow-md transition-shadow">
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between">
                  <Link href={`/experiments/${experiment.id}`} className="flex-1">
                    <CardTitle className="text-lg hover:underline">{experiment.name}</CardTitle>
                    {experiment.description && (
                      <CardDescription className="mt-1 line-clamp-2">
                        {experiment.description}
                      </CardDescription>
                    )}
                  </Link>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="text-destructive -mt-1 -mr-2"
                    onClick={(e) => {
                      e.preventDefault();
                      setDeleteId(experiment.id);
                    }}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-4 text-sm text-muted-foreground">
                  <div className="flex items-center gap-1">
                    <FileText className="h-4 w-4" />
                    {experiment.case_count} cases
                  </div>
                  <div className="flex items-center gap-1">
                    <Users className="h-4 w-4" />
                    {experiment.evaluator_count} evaluators
                  </div>
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  Updated {formatDate(experiment.updated_at)}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <AlertDialog open={!!deleteId} onOpenChange={() => setDeleteId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Experiment</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this experiment? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} className="bg-destructive text-destructive-foreground">
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
