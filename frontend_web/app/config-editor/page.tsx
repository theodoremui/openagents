"use client";

import { useState } from "react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { YamlEditor } from "@/components/yaml-editor";
import { GraphVisualizer } from "@/components/graph-visualizer";

/**
 * Config Editor Page
 *
 * Provides YAML editor and graph visualization for agent configuration.
 * Uses tabs to switch between editor and graph views.
 */
export default function ConfigEditorPage() {
  const [activeTab, setActiveTab] = useState("editor");
  const [refreshKey, setRefreshKey] = useState(0);

  const handleSave = () => {
    // Trigger graph refresh after save
    setRefreshKey((prev) => prev + 1);
    setActiveTab("graph");
  };

  return (
    <div className="h-full">
      <h1 className="text-3xl font-bold mb-6">Configuration Editor</h1>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="mb-4">
          <TabsTrigger value="editor">YAML Editor</TabsTrigger>
          <TabsTrigger value="graph">Graph View</TabsTrigger>
        </TabsList>

        <TabsContent value="editor">
          <YamlEditor onSave={handleSave} />
        </TabsContent>

        <TabsContent value="graph" key={refreshKey}>
          <GraphVisualizer />
        </TabsContent>
      </Tabs>
    </div>
  );
}
