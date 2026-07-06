import React, { useEffect, useState } from "react";
import ReactDOM from "react-dom/client";
import { listen } from "@tauri-apps/api/event";
import {
  getCurrentWindow,
  LogicalPosition,
  PhysicalPosition,
  primaryMonitor,
} from "@tauri-apps/api/window";
import type { WidgetState } from "./lib/types";
import "./overlay.css";

const WIDGET_WIDTH = 400;
const WIDGET_HEIGHT = 188;
const WIDGET_MARGIN = 12;

const defaultState: WidgetState = {
  status: "idle",
  stepIndex: 0,
  maxSteps: 50,
  action: null,
  message: "Idle",
  reasoning: "",
  reasoningPhase: null,
  reasoningStreaming: false,
  screenshot: null,
  updatedAt: new Date().toISOString(),
};

function OverlayWidget() {
  const [state, setState] = useState<WidgetState>(() => {
    try {
      const saved = window.localStorage.getItem("computeruse.widget.state");
      return saved ? { ...defaultState, ...JSON.parse(saved) } : defaultState;
    } catch {
      return defaultState;
    }
  });

  useEffect(() => {
    positionWidget().catch(() => undefined);
    const widgetWindow = getCurrentWindow();
    let unlistenStatus: (() => void) | undefined;
    let unlistenMoved: (() => void) | undefined;

    listen<WidgetState>("computeruse-status", (event) => {
      setState({ ...defaultState, ...event.payload });
    }).then((fn) => {
      unlistenStatus = fn;
    });

    widgetWindow
      .onMoved(({ payload }) => {
        window.localStorage.setItem(
          "computeruse.widget.position",
          JSON.stringify({ x: payload.x, y: payload.y }),
        );
      })
      .then((fn) => {
        unlistenMoved = fn;
      });

    return () => {
      unlistenStatus?.();
      unlistenMoved?.();
    };
  }, []);

  const action = state.action?.action ?? state.status;
  const confidence =
    typeof state.action?.confidence === "number"
      ? `${Math.round(state.action.confidence * 100)}%`
      : "";
  const reasoning = formatReasoning(state.reasoning || state.action?.thought || "");
  const phaseLabel = state.reasoningPhase === "repair" ? "Repair stream" : "LLM reasoning";

  return (
    <div
      className={`widget widget-${state.status}`}
      onMouseDown={startWidgetDrag}
      title="Drag to move"
    >
      <div className="statusRail" />
      <div className="content">
        <div className="topline">
          <span className="brand">ComputerUse</span>
          <span className="pill">{state.status}</span>
        </div>
        <div className="stepLine">
          Step {state.stepIndex}/{state.maxSteps} - {action}
          {confidence ? ` - ${confidence}` : ""}
        </div>
        <div className="message">{state.message}</div>
        <div className="reasoningHeader">
          <span>{phaseLabel}</span>
          {state.reasoningStreaming ? <span className="streamDot" aria-label="streaming" /> : null}
        </div>
        <div className="reasoningBox">
          {reasoning || "Waiting for the next model response."}
        </div>
      </div>
    </div>
  );
}

function startWidgetDrag(event: React.MouseEvent<HTMLDivElement>) {
  if (event.button !== 0) {
    return;
  }
  getCurrentWindow().startDragging().catch(() => undefined);
}

async function positionWidget() {
  const window = getCurrentWindow();
  await window.setAlwaysOnTop(true);

  const savedPosition = readSavedPosition();
  if (savedPosition) {
    await window.setPosition(new PhysicalPosition(savedPosition.x, savedPosition.y));
    return;
  }

  const monitor = await primaryMonitor();
  if (!monitor) {
    return;
  }

  const scale = monitor.scaleFactor || 1;
  const workPos = monitor.workArea.position.toLogical(scale);
  const workSize = monitor.workArea.size.toLogical(scale);
  const x = workPos.x + workSize.width - WIDGET_WIDTH - WIDGET_MARGIN;
  const y = workPos.y + WIDGET_MARGIN;
  await window.setPosition(new LogicalPosition(Math.max(workPos.x, x), Math.max(workPos.y, y)));
}

function readSavedPosition(): { x: number; y: number } | null {
  try {
    const saved = window.localStorage.getItem("computeruse.widget.position");
    if (!saved) {
      return null;
    }
    const position = JSON.parse(saved) as { x?: unknown; y?: unknown };
    if (typeof position.x !== "number" || typeof position.y !== "number") {
      return null;
    }
    return { x: position.x, y: position.y };
  } catch {
    return null;
  }
}

function formatReasoning(value: string): string {
  const trimmed = value.replace(/\s+/g, " ").trim();
  if (trimmed.length <= 360) {
    return trimmed;
  }
  return `...${trimmed.slice(-357)}`;
}

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <OverlayWidget />
  </React.StrictMode>,
);
