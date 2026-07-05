import { useEffect, useMemo, useRef, useState } from "react";
import { convertFileSrc } from "@tauri-apps/api/core";
import { emitTo } from "@tauri-apps/api/event";
import { getCurrentWindow } from "@tauri-apps/api/window";
import { AlertTriangle } from "lucide-react";
import { DebugTiming } from "./components/DebugTiming";
import { HistoryPanel } from "./components/HistoryPanel";
import { ModelSelector } from "./components/ModelSelector";
import { ScreenshotPanel } from "./components/ScreenshotPanel";
import { StepTimeline } from "./components/StepTimeline";
import { TaskRunner } from "./components/TaskRunner";
import type {
  CursorWidgetState,
  HistorySessionDetail,
  HistorySessionSummary,
  ModelInfo,
  PlannerAction,
  RunStatus,
  ScreenshotEvent,
  TimelineStep,
  TimingEvent,
  WidgetState,
  WorkerEvent,
} from "./lib/types";
import { normalizeLocalPath, screenshotAssetUrl } from "./lib/paths";
import { WorkerClient } from "./lib/workerClient";

export default function App() {
  const clientRef = useRef<WorkerClient | null>(null);
  const currentStepRef = useRef(0);
  const maxStepsRef = useRef(50);
  const widgetStateRef = useRef<WidgetState>({
    status: "idle",
    stepIndex: 0,
    maxSteps: 50,
    action: null,
    message: "Idle",
    screenshot: null,
    updatedAt: new Date().toISOString(),
  });
  const cursorWidgetStateRef = useRef<CursorWidgetState>({
    active: false,
    status: "idle",
    stepIndex: 0,
    screenshot: null,
    updatedAt: new Date().toISOString(),
  });
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [selectedModel, setSelectedModel] = useState("");
  const [task, setTask] = useState("");
  const [dryRun, setDryRun] = useState(false);
  const [maxSteps, setMaxSteps] = useState(50);
  const [status, setStatus] = useState<RunStatus>("idle");
  const [screenshot, setScreenshot] = useState<ScreenshotEvent | null>(null);
  const [screenshotVersion, setScreenshotVersion] = useState(0);
  const [lastAction, setLastAction] = useState<PlannerAction | null>(null);
  const [steps, setSteps] = useState<TimelineStep[]>([]);
  const [timings, setTimings] = useState<TimingEvent[]>([]);
  const [historySessions, setHistorySessions] = useState<HistorySessionSummary[]>([]);
  const [selectedHistory, setSelectedHistory] = useState<HistorySessionDetail | null>(null);
  const [debugTiming, setDebugTiming] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const client = new WorkerClient();
    clientRef.current = client;
    const unsubscribe = client.subscribe(handleWorkerEvent);
    broadcastWidget({ message: "Idle" });
    broadcastCursorWidget({ active: false, status: "idle", stepIndex: 0, screenshot: null });
    client.send({ type: "list_models" }).catch((err) => setError(String(err)));
    client.send({ type: "list_history", limit: 50 }).catch((err) => setError(String(err)));
    return () => {
      broadcastCursorWidget({ active: false, status: "idle" });
      unsubscribe();
      client.stop().catch(() => undefined);
    };
  }, []);

  useEffect(() => {
    maxStepsRef.current = maxSteps;
    broadcastWidget({ maxSteps });
  }, [maxSteps]);

  const screenshotSrc = useMemo(() => {
    if (!screenshot?.path) {
      return "";
    }
    const converted = convertFileSrc(normalizeLocalPath(screenshot.path));
    return screenshotAssetUrl(converted, screenshotVersion);
  }, [screenshot, screenshotVersion]);

  function handleWorkerEvent(event: WorkerEvent) {
    if (event.type === "ready") {
      setStatus((current) => (current === "starting" ? "running" : current));
      broadcastWidget({ message: "Worker ready" });
      return;
    }
    if (event.type === "models") {
      setModels(event.models);
      setSelectedModel((current) => current || event.models[0]?.name || "");
      return;
    }
    if (event.type === "history") {
      setHistorySessions(event.sessions);
      setSelectedHistory((current) => {
        if (!current) {
          return current;
        }
        return event.sessions.some((session) => session.session_id === current.session_id) ? current : null;
      });
      return;
    }
    if (event.type === "history_session") {
      setSelectedHistory(event.session);
      return;
    }
    if (event.type === "session_started") {
      setStatus("running");
      setError("");
      broadcastWidget({
        status: "running",
        stepIndex: 0,
        maxSteps: maxStepsRef.current,
        action: null,
        message: "Session started",
      });
      broadcastCursorWidget({ active: true, status: "running", stepIndex: 0 });
      return;
    }
    if (event.type === "status") {
      setStatus(event.status);
      broadcastWidget({ status: event.status, message: event.status });
      broadcastCursorWidget({
        active: isCursorWidgetActive(event.status),
        status: event.status,
      });
      return;
    }
    if (event.type === "screenshot") {
      setScreenshot(event);
      setScreenshotVersion((current) => current + 1);
      const screenshotBounds = {
        width: event.width,
        height: event.height,
        left: event.left,
        top: event.top,
      };
      broadcastWidget({
        screenshot: screenshotBounds,
        message: `Captured ${event.width}x${event.height}`,
      });
      broadcastCursorWidget({ screenshot: screenshotBounds });
      return;
    }
    if (event.type === "step_started") {
      currentStepRef.current = event.step_index;
      broadcastWidget({
        status: "running",
        stepIndex: event.step_index,
        maxSteps: maxStepsRef.current,
        message: `Starting step ${event.step_index}`,
      });
      broadcastCursorWidget({
        active: true,
        status: "running",
        stepIndex: event.step_index,
      });
      return;
    }
    if (event.type === "model_action") {
      setLastAction(event.action);
      const index = currentStepRef.current || 1;
      broadcastWidget({
        status: "running",
        stepIndex: index,
        maxSteps: maxStepsRef.current,
        action: event.action,
        message: event.action.thought || event.action.action,
      });
      const nextStep: TimelineStep = {
        step_index: index,
        action: event.action.action,
        thought: event.action.thought,
        confidence: event.action.confidence,
        result: "planned",
      };
      setSteps((current) => [...current.filter((step) => step.step_index !== index), nextStep]);
      return;
    }
    if (event.type === "tool_result") {
      broadcastWidget({
        status: event.ok ? "running" : "failed",
        stepIndex: currentStepRef.current,
        maxSteps: maxStepsRef.current,
        message: event.message,
      });
      setSteps((current) => {
        if (current.length === 0) {
          return current;
        }
        const next = [...current];
        next[next.length - 1] = { ...next[next.length - 1], result: event.message, ok: event.ok };
        return next;
      });
      return;
    }
    if (event.type === "timing") {
      setTimings((current) => [...current, event]);
      return;
    }
    if (event.type === "session_done") {
      setStatus("done");
      broadcastWidget({ status: "done", message: event.summary });
      broadcastCursorWidget({ active: false, status: "done" });
      setSteps((current) => updateLastResult(current, event.summary, true));
      refreshHistory();
      return;
    }
    if (event.type === "session_failed") {
      setStatus("failed");
      setError(event.reason);
      broadcastWidget({ status: "failed", message: event.reason });
      broadcastCursorWidget({ active: false, status: "failed" });
      setSteps((current) => updateLastResult(current, event.reason, false));
      refreshHistory();
      return;
    }
    if (event.type === "session_cancelled") {
      setStatus("cancelled");
      broadcastWidget({ status: "cancelled", message: event.reason });
      broadcastCursorWidget({ active: false, status: "cancelled" });
      setSteps((current) => updateLastResult(current, event.reason, false));
      refreshHistory();
      return;
    }
    if (event.type === "error") {
      setError(event.message);
      broadcastWidget({ status: "failed", message: event.message });
      broadcastCursorWidget({ active: false, status: "failed" });
    }
  }

  function send(command: Parameters<WorkerClient["send"]>[0]) {
    clientRef.current?.send(command).catch((err) => setError(String(err)));
  }

  function refreshHistory() {
    send({ type: "list_history", limit: 50 });
  }

  function selectHistory(sessionId: string) {
    send({ type: "get_history_session", session_id: sessionId });
  }

  function broadcastWidget(patch: Partial<WidgetState>) {
    const next: WidgetState = {
      ...widgetStateRef.current,
      ...patch,
      updatedAt: new Date().toISOString(),
    };
    widgetStateRef.current = next;
    try {
      window.localStorage.setItem("computeruse.widget.state", JSON.stringify(next));
    } catch {
      // Local storage is only a best-effort fallback for the secondary window.
    }
    emitTo("widget", "computeruse-status", next).catch(() => undefined);
  }

  function broadcastCursorWidget(patch: Partial<CursorWidgetState>) {
    const next: CursorWidgetState = {
      ...cursorWidgetStateRef.current,
      ...patch,
      updatedAt: new Date().toISOString(),
    };
    cursorWidgetStateRef.current = next;
    try {
      window.localStorage.setItem("computeruse.cursor.state", JSON.stringify(next));
    } catch {
      // Local storage is only a best-effort fallback for the secondary window.
    }
    emitTo("cursor-widget", "computeruse-cursor-status", next).catch(() => undefined);
    emitTo("cursor-marker", "computeruse-cursor-status", next).catch(() => undefined);
  }

  function runTask() {
    setStatus("starting");
    broadcastWidget({
      status: "starting",
      stepIndex: 0,
      maxSteps: maxStepsRef.current,
      action: null,
      message: "Starting",
    });
    broadcastCursorWidget({
      active: true,
      status: "starting",
      stepIndex: 0,
      screenshot: null,
    });
    setSteps([]);
    setTimings([]);
    setLastAction(null);
    setError("");
    currentStepRef.current = 0;
    const command = {
      type: "start_task",
      task,
      model: selectedModel,
      dry_run: dryRun,
      max_steps: maxSteps,
    } as const;
    minimizeMainWindow().finally(() => send(command));
  }

  function stopTask() {
    broadcastCursorWidget({ active: false, status: "cancelled" });
    send({ type: "stop" });
  }

  const canRun = task.trim().length > 0 && selectedModel.length > 0;

  return (
    <main className="grid h-screen grid-cols-[340px_minmax(420px,1fr)_360px] gap-4 bg-[#ece9de] p-4 text-ink">
      <aside className="flex min-h-0 flex-col gap-4">
        <TaskRunner
          task={task}
          setTask={setTask}
          dryRun={dryRun}
          setDryRun={setDryRun}
          maxSteps={maxSteps}
          setMaxSteps={setMaxSteps}
          status={status}
          canRun={canRun}
          onRun={runTask}
          onPause={() => send({ type: "pause" })}
          onResume={() => send({ type: "resume" })}
          onStop={stopTask}
          onScreenshot={() => send({ type: "take_screenshot" })}
        />
        <ModelSelector
          models={models}
          selectedModel={selectedModel}
          onChange={setSelectedModel}
          onRefresh={() => send({ type: "list_models" })}
        />
        <DebugTiming timings={timings} enabled={debugTiming} onToggle={setDebugTiming} />
      </aside>

      <section className="flex min-h-0 flex-col gap-4">
        {error ? (
          <div className="flex items-start gap-2 rounded-lg border border-amber bg-white p-3 text-sm text-amber shadow-soft">
            <AlertTriangle className="mt-0.5 shrink-0" size={16} />
            <span>{error}</span>
          </div>
        ) : null}
        <ScreenshotPanel
          src={screenshotSrc}
          width={screenshot?.width}
          height={screenshot?.height}
        />
      </section>

      <aside className="flex min-h-0 flex-col gap-4">
        <section className="rounded-lg border border-line bg-panel p-4 shadow-soft">
          <div className="mb-3 font-semibold">Last model action</div>
          <pre className="scrollbar-thin max-h-56 overflow-auto rounded-md border border-line bg-white p-3 text-xs">
            {lastAction ? JSON.stringify(lastAction, null, 2) : "No action yet."}
          </pre>
        </section>
        <StepTimeline steps={steps} />
        <HistoryPanel
          sessions={historySessions}
          selectedSession={selectedHistory}
          onRefresh={refreshHistory}
          onSelect={selectHistory}
        />
      </aside>
    </main>
  );
}

function updateLastResult(steps: TimelineStep[], result: string, ok: boolean): TimelineStep[] {
  if (steps.length === 0) {
    return steps;
  }
  const next = [...steps];
  next[next.length - 1] = { ...next[next.length - 1], result, ok };
  return next;
}

function isCursorWidgetActive(status: RunStatus): boolean {
  return status === "starting" || status === "running" || status === "paused";
}

function minimizeMainWindow(): Promise<void> {
  return getCurrentWindow()
    .minimize()
    .catch(() => undefined);
}
