"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { Bot, Settings, HelpCircle, Mic } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useVoiceMode } from "@/components/voice";

/**
 * Navigation component
 *
 * Provides top-level navigation between main pages and voice mode toggle.
 * Highlights the currently active page.
 */
export function Navigation() {
  const pathname = usePathname();
  const { isConnected, isConnecting, enterVoiceMode, agentState } = useVoiceMode();

  const links = [
    {
      href: "/",
      label: "Agent Simulation",
      icon: Bot,
      isActive: pathname === "/",
    },
    {
      href: "/config-editor",
      label: "Config Editor",
      icon: Settings,
      isActive: pathname === "/config-editor",
    },
    {
      href: "/help",
      label: "Help",
      icon: HelpCircle,
      isActive: pathname === "/help",
    },
  ];

  return (
    <nav className="glass-panel border-b border-border/50 bg-card/60 backdrop-blur-xl shadow-sm sticky top-0 z-50">
      <div className="container mx-auto px-4">
        <div className="flex h-16 items-center justify-between">
          {/* Logo */}
          <Link href="/" className="flex items-center space-x-2 group">
            <div className="p-2 rounded-lg bg-primary/10 group-hover:bg-primary/20 transition-colors">
              <Bot className="h-6 w-6 text-primary" />
            </div>
            <span className="text-xl font-bold bg-gradient-to-r from-foreground to-foreground/70 bg-clip-text text-transparent">
              OpenAgents
            </span>
          </Link>

          {/* Navigation Links */}
          <div className="flex items-center space-x-1">
            {links.map((link) => {
              const Icon = link.icon;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={cn(
                    "flex items-center space-x-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200",
                    link.isActive
                      ? "glass-panel bg-gradient-to-br from-primary to-primary/80 text-primary-foreground shadow-md"
                      : "text-muted-foreground hover:bg-accent/50 hover:text-accent-foreground"
                  )}
                >
                  <Icon className="h-4 w-4" />
                  <span>{link.label}</span>
                </Link>
              );
            })}

            {/* Voice Mode Toggle */}
            <Button
              variant={isConnected ? "default" : "ghost"}
              size="sm"
              onClick={() => !isConnected && !isConnecting && enterVoiceMode()}
              className={cn(
                "flex items-center space-x-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200",
                isConnected && "glass-panel bg-gradient-to-br from-green-500 to-green-600 text-white shadow-md animate-pulse",
                !isConnected && isConnecting && "glass-panel bg-gradient-to-br from-amber-500 to-amber-600 text-white shadow-md animate-pulse"
              )}
              title={
                isConnected
                  ? `Voice Mode Active (${agentState})`
                  : isConnecting
                    ? "Voice Mode Connecting..."
                    : "Start Voice Mode"
              }
            >
              <Mic className={cn(
                "h-4 w-4",
                (isConnected || isConnecting) && "animate-pulse"
              )} />
              <span>
                {isConnected ? "Voice Active" : isConnecting ? "Voice Connecting" : "Voice Mode"}
              </span>
            </Button>
          </div>
        </div>
      </div>
    </nav>
  );
}
