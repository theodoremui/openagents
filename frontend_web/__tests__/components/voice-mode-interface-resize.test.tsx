import React from "react";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";

jest.mock("@livekit/components-react", () => ({
  __esModule: true,
  RoomAudioRenderer: () => null,
  useLocalParticipant: () => ({ localParticipant: null }),
  useRemoteParticipants: () => [],
  useRoomContext: () => ({}),
  useVoiceAssistant: () => ({ state: "listening" }),
}));

jest.mock("@/lib/contexts/VoiceContext", () => ({
  useVoiceSettings: () => [{ ttsEnabled: true, volume: 1, playbackSpeed: 1 }],
}));

jest.mock("@/components/visualization/orchestration/MoEFlowVisualization", () => ({
  __esModule: true,
  MoEFlowVisualization: () => <div data-testid="moe-flow" />,
}));

jest.mock("@/components/voice/VoiceTranscript", () => ({
  __esModule: true,
  VoiceTranscript: () => <div data-testid="voice-transcript" />,
}));

jest.mock("@/components/voice/VoiceControls", () => ({
  __esModule: true,
  VoiceControls: () => <div data-testid="voice-controls" />,
}));

jest.mock("@/components/voice/VoiceStateAnimation", () => ({
  __esModule: true,
  VoiceStateAnimation: () => <div data-testid="voice-state-animation" />,
}));

jest.mock("@/components/voice/VoiceModeProvider", () => ({
  useVoiceMode: () => ({
    agentState: "listening",
    exitVoiceMode: jest.fn(),
    orchestrationTrace: null, // IMPORTANT: divider should still be present even without trace
  }),
}));

import { VoiceModeInterface } from "@/components/voice/VoiceModeInterface";

describe("VoiceModeInterface resize divider", () => {
  it("renders the draggable divider even when no orchestration trace exists", () => {
    render(<VoiceModeInterface onClose={() => {}} />);
    expect(screen.getByTestId("voice-moe-resize-divider")).toBeInTheDocument();
  });
});


