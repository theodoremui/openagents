/**
 * VoiceSettings Component
 *
 * Settings panel for voice features.
 * Features:
 * - Voice selection
 * - Profile selection
 * - TTS/STT toggles
 * - Volume and speed controls
 * - Auto-play settings
 */

'use client';

import React, { useCallback, useMemo, useState } from 'react';
import { Volume2, Mic, Speaker, Settings, RefreshCw, CheckCircle2, XCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useVoiceSettings, useVoices } from '@/lib/contexts/VoiceContext';
import { cn } from '@/lib/utils';

/**
 * VoiceSettings props
 */
export interface VoiceSettingsProps {
  /** Custom className */
  className?: string;
  /** Compact layout */
  compact?: boolean;
  /** Show advanced settings */
  showAdvanced?: boolean;
}

/**
 * VoiceSettings component
 */
export const VoiceSettings: React.FC<VoiceSettingsProps> = ({
  className,
  compact = false,
  showAdvanced = true,
}) => {
  const [settings, updateSettings] = useVoiceSettings();
  const { voices, loading, error, refresh } = useVoices();
  const [isRefreshing, setIsRefreshing] = useState(false);

  const volumeLabel = useMemo(() => Math.round(settings.volume * 100), [settings.volume]);
  const speedLabel = useMemo(() => settings.playbackSpeed.toFixed(2), [settings.playbackSpeed]);

  const setVolume = useCallback(
    (next: number) => {
      if (Number.isNaN(next) || next === settings.volume) return;
      updateSettings({ volume: next });
    },
    [settings.volume, updateSettings]
  );

  const setPlaybackSpeed = useCallback(
    (next: number) => {
      if (Number.isNaN(next) || next === settings.playbackSpeed) return;
      updateSettings({ playbackSpeed: next });
    },
    [settings.playbackSpeed, updateSettings]
  );

  /**
   * Handle refresh voices
   */
  const handleRefresh = async () => {
    setIsRefreshing(true);
    await refresh();
    setIsRefreshing(false);
  };

  /**
   * Render voice selector
   */
  const renderVoiceSelector = () => (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <Label htmlFor="voice-select" className="flex items-center gap-2">
          <Speaker className="h-4 w-4" />
          Voice
        </Label>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleRefresh}
          disabled={loading || isRefreshing}
          title="Refresh voices"
        >
          <RefreshCw className={cn('h-4 w-4', isRefreshing && 'animate-spin')} />
        </Button>
      </div>

      <Select
        value={settings.selectedVoiceId || undefined}
        onValueChange={(voiceId) => updateSettings({ selectedVoiceId: voiceId })}
        disabled={loading}
      >
        <SelectTrigger id="voice-select">
          <SelectValue placeholder="Select a voice..." />
        </SelectTrigger>
        <SelectContent>
          {voices.map((voice) => (
            <SelectItem key={voice.voice_id} value={voice.voice_id}>
              {voice.name}
              {voice.category && (
                <span className="text-xs text-muted-foreground ml-2">({voice.category})</span>
              )}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {error && (
        <p className="text-xs text-red-500 flex items-center gap-1">
          <XCircle className="h-3 w-3" />
          {error}
        </p>
      )}

      {!loading && voices.length > 0 && (
        <p className="text-xs text-muted-foreground flex items-center gap-1">
          <CheckCircle2 className="h-3 w-3" />
          {voices.length} voices available
        </p>
      )}
    </div>
  );

  /**
   * Render profile selector
   */
  const renderProfileSelector = () => (
    <div className="space-y-2">
      <Label htmlFor="profile-select" className="flex items-center gap-2">
        <Settings className="h-4 w-4" />
        Profile
      </Label>
      <Select
        value={settings.selectedProfile}
        onValueChange={(profile) => updateSettings({ selectedProfile: profile })}
      >
        <SelectTrigger id="profile-select">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="default">Default</SelectItem>
          <SelectItem value="professional">Professional</SelectItem>
          <SelectItem value="conversational">Conversational</SelectItem>
        </SelectContent>
      </Select>
      <p className="text-xs text-muted-foreground">
        Presets for voice stability and style
      </p>
    </div>
  );

  /**
   * Render feature toggles
   */
  const renderFeatureToggles = () => (
    <div className="space-y-4">
      {/* TTS Toggle */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Volume2 className="h-4 w-4" />
          <Label htmlFor="tts-toggle" className="cursor-pointer">
            Text-to-Speech
          </Label>
        </div>
        <Switch
          id="tts-toggle"
          checked={settings.ttsEnabled}
          onCheckedChange={(checked) => updateSettings({ ttsEnabled: checked })}
        />
      </div>

      {/* STT Toggle */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Mic className="h-4 w-4" />
          <Label htmlFor="stt-toggle" className="cursor-pointer">
            Speech-to-Text
          </Label>
        </div>
        <Switch
          id="stt-toggle"
          checked={settings.sttEnabled}
          onCheckedChange={(checked) => updateSettings({ sttEnabled: checked })}
        />
      </div>

      {/* Auto-play Toggle */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Speaker className="h-4 w-4" />
          <Label htmlFor="autoplay-toggle" className="cursor-pointer">
            Auto-play Responses
          </Label>
        </div>
        <Switch
          id="autoplay-toggle"
          checked={settings.autoPlayResponses}
          onCheckedChange={(checked) => updateSettings({ autoPlayResponses: checked })}
        />
      </div>
    </div>
  );

  /**
   * Render volume control
   */
  const renderVolumeControl = () => (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <Label htmlFor="volume-slider" className="flex items-center gap-2">
          <Volume2 className="h-4 w-4" />
          Volume
        </Label>
        <span className="text-sm text-muted-foreground">{volumeLabel}%</span>
      </div>
      {/* Native range avoids Radix Slider internal ref churn that can trigger infinite update loops */}
      <input
        id="volume-slider"
        type="range"
        min={0}
        max={1}
        step={0.05}
        value={settings.volume}
        onChange={(e) => setVolume(Number(e.target.value))}
        className="w-full accent-primary"
        aria-label="Volume"
      />
    </div>
  );

  /**
   * Render speed control
   */
  const renderSpeedControl = () => (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <Label htmlFor="speed-slider" className="flex items-center gap-2">
          <Speaker className="h-4 w-4" />
          Playback Speed
        </Label>
        <span className="text-sm text-muted-foreground">{speedLabel}x</span>
      </div>
      <input
        id="speed-slider"
        type="range"
        min={0.5}
        max={2.0}
        step={0.1}
        value={settings.playbackSpeed}
        onChange={(e) => setPlaybackSpeed(Number(e.target.value))}
        className="w-full accent-primary"
        aria-label="Playback speed"
      />
      <p className="text-xs text-muted-foreground">
        0.5x (slow) to 2.0x (fast)
      </p>
    </div>
  );

  /**
   * Render compact layout
   */
  if (compact) {
    return (
      <div className={cn('space-y-4 p-4', className)}>
        {renderVoiceSelector()}
        {renderFeatureToggles()}
        {renderVolumeControl()}
      </div>
    );
  }

  /**
   * Render full layout
   */
  return (
    <Card className={cn('glass-panel', className)}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Settings className="h-5 w-5" />
          Voice Settings
        </CardTitle>
        <CardDescription>
          Configure text-to-speech and speech-to-text settings
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Voice Selection */}
        {renderVoiceSelector()}

        {/* Profile Selection */}
        {renderProfileSelector()}

        {/* Divider */}
        <div className="border-t" />

        {/* Feature Toggles */}
        {renderFeatureToggles()}

        {/* Divider */}
        <div className="border-t" />

        {/* Volume Control */}
        {renderVolumeControl()}

        {/* Speed Control */}
        {showAdvanced && renderSpeedControl()}

        {/* Info */}
        <div className="text-xs text-muted-foreground space-y-1">
          <p>• Settings are saved locally</p>
          <p>• Voice changes apply to next synthesis</p>
          {settings.ttsEnabled && settings.autoPlayResponses && (
            <p className="text-blue-500">• Auto-play is enabled</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export default VoiceSettings;
