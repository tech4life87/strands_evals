import { useState, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, Upload } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { api } from '@/lib/api';

export function NewExperiment() {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [importData, setImportData] = useState('');

  async function handleCreate() {
    if (!name.trim()) {
      setError('Name is required');
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const experiment = await api.experiments.create({
        name: name.trim(),
        description: description.trim() || undefined,
      });
      navigate(`/experiments/${experiment.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create experiment');
      setSaving(false);
    }
  }

  async function handleImport() {
    if (!importData.trim()) {
      setError('Please paste JSON data or upload a file');
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const data = JSON.parse(importData);
      const experiment = await api.experiments.import(data, name.trim() || undefined);
      navigate(`/experiments/${experiment.id}`);
    } catch (err) {
      if (err instanceof SyntaxError) {
        setError('Invalid JSON format');
      } else {
        setError(err instanceof Error ? err.message : 'Failed to import experiment');
      }
      setSaving(false);
    }
  }

  function handleFileUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      const content = e.target?.result as string;
      setImportData(content);
      if (!name.trim()) {
        setName(file.name.replace(/\.json$/, ''));
      }
    };
    reader.onerror = () => {
      setError('Failed to read file');
    };
    reader.readAsText(file);
  }

  return (
    <div className="container mx-auto py-8 px-4 max-w-2xl">
      <div className="flex items-center gap-4 mb-6">
        <Link to="/">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <h1 className="text-2xl font-bold">New Experiment</h1>
      </div>

      {error && (
        <div className="bg-destructive/10 text-destructive px-4 py-3 rounded-md mb-6">
          {error}
        </div>
      )}

      <Tabs defaultValue="create" className="space-y-4">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="create">Create New</TabsTrigger>
          <TabsTrigger value="import">Import JSON</TabsTrigger>
        </TabsList>

        <TabsContent value="create">
          <Card>
            <CardHeader>
              <CardTitle>Create New Experiment</CardTitle>
              <CardDescription>
                Start with a blank experiment and add test cases and evaluators.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Name *</Label>
                <Input
                  id="name"
                  value={name}
                  onChange={e => setName(e.target.value)}
                  placeholder="e.g., Agent Response Quality"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="description">Description (optional)</Label>
                <Textarea
                  id="description"
                  value={description}
                  onChange={e => setDescription(e.target.value)}
                  placeholder="Describe what this experiment evaluates..."
                  rows={3}
                />
              </div>

              <Button onClick={handleCreate} disabled={saving} className="w-full">
                {saving ? 'Creating...' : 'Create Experiment'}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="import">
          <Card>
            <CardHeader>
              <CardTitle>Import Experiment</CardTitle>
              <CardDescription>
                Import an existing experiment from a JSON file.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="importName">Name (optional)</Label>
                <Input
                  id="importName"
                  value={name}
                  onChange={e => setName(e.target.value)}
                  placeholder="Override the imported name"
                />
              </div>

              <div className="space-y-2">
                <Label>Upload File</Label>
                <div
                  className="border-2 border-dashed rounded-lg p-6 text-center cursor-pointer hover:border-primary transition-colors"
                  onClick={() => fileInputRef.current?.click()}
                >
                  <Upload className="mx-auto h-8 w-8 text-muted-foreground mb-2" />
                  <p className="text-sm text-muted-foreground">
                    Click to upload a JSON file
                  </p>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".json"
                    className="hidden"
                    onChange={handleFileUpload}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="importData">Or Paste JSON</Label>
                <Textarea
                  id="importData"
                  value={importData}
                  onChange={e => setImportData(e.target.value)}
                  placeholder='{"cases": [...], "evaluators": [...]}'
                  rows={8}
                  className="font-mono text-sm"
                />
              </div>

              <Button onClick={handleImport} disabled={saving} className="w-full">
                {saving ? 'Importing...' : 'Import Experiment'}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
