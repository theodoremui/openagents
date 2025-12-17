import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ExternalLink, Book, Code, GitBranch, Cpu } from "lucide-react";
import Link from "next/link";

/**
 * Help Page
 *
 * Provides documentation and guidance for using the application.
 */
export default function HelpPage() {
  return (
    <div className="max-w-4xl">
      <h1 className="text-3xl font-bold mb-2">Help & Documentation</h1>
      <p className="text-muted-foreground mb-8">
        Learn how to use the OpenAgents multi-agent orchestration system
      </p>

      {/* Overview */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Book className="h-5 w-5" />
            What is OpenAgents?
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p>
            OpenAgents is a multi-agent orchestration system that allows you to
            manage, configure, and simulate AI agents with different capabilities.
            The system is driven by a YAML configuration file that defines agent
            types, their behaviors, tools, and relationships.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 border rounded-md">
              <h4 className="font-semibold mb-2">Frontend (Next.js)</h4>
              <ul className="text-sm text-muted-foreground space-y-1">
                <li>• React 18 with Server Components</li>
                <li>• Tailwind CSS + shadcn/ui</li>
                <li>• ReactFlow for graph visualization</li>
                <li>• TypeScript for type safety</li>
              </ul>
            </div>

            <div className="p-4 border rounded-md">
              <h4 className="font-semibold mb-2">Backend (FastAPI)</h4>
              <ul className="text-sm text-muted-foreground space-y-1">
                <li>• Python 3.11+ with FastAPI</li>
                <li>• Pydantic models for validation</li>
                <li>• API key authentication</li>
                <li>• Integration with asdrp.agents</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Main Features */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Cpu className="h-5 w-5" />
            Main Features
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* Agent Simulation */}
            <div>
              <h4 className="font-semibold mb-2">1. Agent Simulation</h4>
              <p className="text-sm text-muted-foreground mb-2">
                Interact with agents in real-time through a Q&A interface.
              </p>
              <ul className="text-sm text-muted-foreground space-y-1 ml-4">
                <li>• Select an agent from the dropdown</li>
                <li>• View agent configuration (model, tools, connections)</li>
                <li>• Send messages and receive responses</li>
                <li>• View execution traces to understand agent behavior</li>
              </ul>
              <Link href="/">
                <Button variant="outline" size="sm" className="mt-2">
                  Go to Simulation
                </Button>
              </Link>
            </div>

            {/* Config Editor */}
            <div>
              <h4 className="font-semibold mb-2">2. Configuration Editor</h4>
              <p className="text-sm text-muted-foreground mb-2">
                Edit agent configuration with a YAML editor and visualize relationships.
              </p>
              <ul className="text-sm text-muted-foreground space-y-1 ml-4">
                <li>• Edit YAML configuration with syntax highlighting</li>
                <li>• Real-time YAML validation</li>
                <li>• Save changes to update agents</li>
                <li>• Visualize agent graph with ReactFlow</li>
                <li>• Interactive nodes showing agent details</li>
              </ul>
              <Link href="/config-editor">
                <Button variant="outline" size="sm" className="mt-2">
                  Go to Config Editor
                </Button>
              </Link>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Multi-Agent Graph Concept */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <GitBranch className="h-5 w-5" />
            Multi-Agent Graph Concept
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p>
            The multi-agent system uses a graph-based architecture where:
          </p>

          <div className="space-y-3">
            <div className="p-3 border-l-4 border-primary bg-muted/50">
              <p className="font-semibold">Agents (Nodes)</p>
              <p className="text-sm text-muted-foreground">
                Each agent is a specialized component with specific capabilities,
                tools, and instructions. Examples: GeoAgent, FinanceAgent, MapAgent.
              </p>
            </div>

            <div className="p-3 border-l-4 border-secondary bg-muted/50">
              <p className="font-semibold">Edges (Connections)</p>
              <p className="text-sm text-muted-foreground">
                Edges represent routing, delegation, or data flow between agents.
                They define how agents can communicate and orchestrate tasks.
              </p>
            </div>

            <div className="p-3 border-l-4 border-accent bg-muted/50">
              <p className="font-semibold">Orchestration</p>
              <p className="text-sm text-muted-foreground">
                The system can route requests through multiple agents, each
                contributing their specialized capabilities to solve complex tasks.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Tech Stack */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Code className="h-5 w-5" />
            Technology Stack
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div>
              <h4 className="font-semibold mb-1">Frontend</h4>
              <div className="flex flex-wrap gap-2">
                {["Next.js 14", "React 18", "TypeScript", "Tailwind CSS", "shadcn/ui", "ReactFlow", "Monaco Editor"].map((tech) => (
                  <span key={tech} className="px-2 py-1 bg-primary/10 text-primary rounded text-xs">
                    {tech}
                  </span>
                ))}
              </div>
            </div>

            <div>
              <h4 className="font-semibold mb-1">Backend</h4>
              <div className="flex flex-wrap gap-2">
                {["FastAPI", "Python 3.11+", "Pydantic", "PyYAML", "uvicorn"].map((tech) => (
                  <span key={tech} className="px-2 py-1 bg-secondary/50 text-secondary-foreground rounded text-xs">
                    {tech}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Links */}
      <Card>
        <CardHeader>
          <CardTitle>Additional Resources</CardTitle>
          <CardDescription>
            Documentation and external links
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className="flex items-center justify-between p-3 border rounded-md">
            <div>
              <p className="font-semibold">Architecture Documentation</p>
              <p className="text-sm text-muted-foreground">
                Detailed system architecture and design decisions
              </p>
            </div>
            <Link href="/docs/architecture" target="_blank">
              <Button variant="outline" size="sm">
                <ExternalLink className="h-4 w-4 mr-2" />
                View
              </Button>
            </Link>
          </div>

          <div className="flex items-center justify-between p-3 border rounded-md">
            <div>
              <p className="font-semibold">API Documentation</p>
              <p className="text-sm text-muted-foreground">
                OpenAPI/Swagger documentation for backend API
              </p>
            </div>
            <a href="http://localhost:8000/docs" target="_blank" rel="noopener noreferrer">
              <Button variant="outline" size="sm">
                <ExternalLink className="h-4 w-4 mr-2" />
                Open
              </Button>
            </a>
          </div>

          <div className="flex items-center justify-between p-3 border rounded-md">
            <div>
              <p className="font-semibold">README</p>
              <p className="text-sm text-muted-foreground">
                Project overview and setup instructions
              </p>
            </div>
            <Button variant="outline" size="sm" disabled>
              <ExternalLink className="h-4 w-4 mr-2" />
              View
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
