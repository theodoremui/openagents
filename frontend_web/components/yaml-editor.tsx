"use client";

import { useState, useEffect } from "react";
import Editor from "@monaco-editor/react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getApiClient, ApiClientError } from "@/lib/api-client";
import { Loader2, Save, RefreshCw, CheckCircle2, AlertCircle } from "lucide-react";
import * as yaml from "js-yaml";

interface YamlEditorProps {
  onSave?: () => void;
}

/**
 * YAML Editor Component
 *
 * Provides a Monaco editor for editing agent configuration YAML.
 * Includes validation, save, and reload functionality.
 */
export function YamlEditor({ onSave }: YamlEditorProps) {
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [validating, setValidating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isValid, setIsValid] = useState(true);

  // Load configuration on mount
  useEffect(() => {
    loadConfig();
  }, []);

  // Validate YAML on content change (debounced)
  useEffect(() => {
    const timer = setTimeout(() => {
      validateYaml(content);
    }, 500);

    return () => clearTimeout(timer);
  }, [content]);

  async function loadConfig() {
    try {
      setLoading(true);
      setError(null);
      const client = getApiClient();
      const data = await client.getConfig();
      setContent(data.content);
    } catch (err) {
      const message =
        err instanceof ApiClientError
          ? err.message
          : "Failed to load configuration";
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  function validateYaml(yamlContent: string) {
    if (!yamlContent.trim()) {
      setIsValid(false);
      return;
    }

    try {
      yaml.load(yamlContent);
      setIsValid(true);
      setError(null);
    } catch (err) {
      setIsValid(false);
      if (err instanceof Error) {
        setError(`YAML Syntax Error: ${err.message}`);
      }
    }
  }

  async function handleSave() {
    if (!isValid) {
      setError("Cannot save invalid YAML");
      return;
    }

    try {
      setSaving(true);
      setError(null);
      setSuccess(null);

      const client = getApiClient();

      // Validate first
      setValidating(true);
      await client.validateConfig(content);
      setValidating(false);

      // Save
      const result = await client.updateConfig({ content });
      setSuccess(
        result.message +
          (result.agents_count
            ? ` (${result.agents_count} agents loaded)`
            : "")
      );

      if (onSave) {
        onSave();
      }

      // Clear success message after 3 seconds
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      const message =
        err instanceof ApiClientError
          ? err.message
          : "Failed to save configuration";
      setError(message);
    } finally {
      setSaving(false);
      setValidating(false);
    }
  }

  if (loading) {
    return (
      <Card>
        <CardContent className="pt-6 flex items-center justify-center h-96">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>YAML Configuration</CardTitle>
          <div className="flex items-center gap-2">
            {validating && <span className="text-sm text-muted-foreground">Validating...</span>}
            {isValid && !validating && (
              <CheckCircle2 className="h-5 w-5 text-green-600" />
            )}
            {!isValid && !validating && (
              <AlertCircle className="h-5 w-5 text-destructive" />
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={loadConfig}
              disabled={loading}
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Reload
            </Button>
            <Button
              size="sm"
              onClick={handleSave}
              disabled={saving || !isValid}
            >
              {saving ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Save className="h-4 w-4 mr-2" />
              )}
              Save
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Status Messages */}
        {error && (
          <div className="p-3 bg-destructive/10 border border-destructive rounded-md text-sm text-destructive">
            {error}
          </div>
        )}
        {success && (
          <div className="p-3 bg-green-50 border border-green-200 rounded-md text-sm text-green-800">
            {success}
          </div>
        )}

        {/* Editor */}
        <div className="border rounded-md overflow-hidden">
          <Editor
            height="600px"
            defaultLanguage="yaml"
            value={content}
            onChange={(value) => setContent(value || "")}
            theme="vs-light"
            options={{
              minimap: { enabled: false },
              fontSize: 14,
              lineNumbers: "on",
              scrollBeyondLastLine: false,
              wordWrap: "on",
              wrappingIndent: "indent",
              automaticLayout: true,
            }}
          />
        </div>
      </CardContent>
    </Card>
  );
}
