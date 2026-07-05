export type RunStatus =
  | "idle"
  | "starting"
  | "running"
  | "paused"
  | "done"
  | "failed"
  | "cancelled";

export interface ModelInfo {
  name: string;
  vision: boolean;
  size?: number | null;
  modified_at?: string | null;
}

export interface PlannerAction {
  thought: string;
  action: string;
  args: Record<string, unknown>;
  done: boolean;
  confidence: number;
}

export interface ScreenshotEvent {
  type: "screenshot";
  path: string;
  width: number;
  height: number;
  left?: number;
  top?: number;
  monitor_width?: number;
  monitor_height?: number;
}

export interface TimelineStep {
  step_index: number;
  action: string;
  thought: string;
  confidence: number;
  result: string;
  ok?: boolean;
}

export type SessionStatus = "running" | "done" | "failed" | "cancelled";

export interface HistorySessionSummary {
  session_id: string;
  created_at: string;
  updated_at: string;
  status: SessionStatus;
  task: string;
  selected_model: string;
  step_index: number;
  summary: string;
  last_screenshot_path?: string | null;
}

export interface HistoryStep extends TimelineStep {
  screenshot_path?: string | null;
  timings?: Record<string, unknown>;
}

export interface HistorySessionDetail extends HistorySessionSummary {
  last_action?: Record<string, unknown> | null;
  last_observation_summary: string;
  steps: HistoryStep[];
}

export interface TimingEvent {
  type: "timing";
  step_index: number;
  capture_ms?: number;
  encode_ms?: number;
  ollama_ms?: number;
  execute_ms?: number;
  settle_ms?: number;
  verify_ms?: number;
  grid_ms?: number;
  perception_ms?: number;
  element_count?: number;
  session_write_ms?: number;
  metrics_ms?: number;
  metrics_available?: boolean;
  metrics_error?: string;
  cpu_percent?: number;
  cpu_user_percent?: number;
  cpu_system_percent?: number;
  process_cpu_percent?: number;
  process_rss_mb?: number;
  process_vms_mb?: number;
  process_threads?: number;
  ram_percent?: number;
  ram_used_mb?: number;
  ram_available_mb?: number;
  ram_total_mb?: number;
  disk_read_mb?: number;
  disk_write_mb?: number;
  gpu_available?: boolean;
  gpu_source?: string;
  gpu_error?: string;
  gpu_count?: number;
  gpu_names?: string;
  gpu_util_percent?: number;
  gpu_memory_used_mb?: number;
  gpu_memory_total_mb?: number;
}

export type WorkerCommand =
  | { type: "list_models" }
  | {
      type: "start_task";
      task: string;
      model: string;
      dry_run: boolean;
      max_steps: number;
    }
  | { type: "pause" }
  | { type: "resume" }
  | { type: "stop" }
  | { type: "take_screenshot" }
  | { type: "list_history"; limit?: number }
  | { type: "get_history_session"; session_id: string };

export type WorkerEvent =
  | { type: "ready" }
  | { type: "models"; models: ModelInfo[] }
  | { type: "session_started"; session_id: string }
  | ScreenshotEvent
  | { type: "step_started"; step_index: number }
  | { type: "model_action"; action: PlannerAction }
  | { type: "tool_result"; ok: boolean; message: string; recoverable?: boolean }
  | TimingEvent
  | { type: "session_done"; summary: string }
  | { type: "session_failed"; reason: string }
  | { type: "session_cancelled"; reason: string }
  | { type: "history"; sessions: HistorySessionSummary[] }
  | { type: "history_session"; session: HistorySessionDetail | null }
  | { type: "status"; status: RunStatus }
  | { type: "error"; message: string };

export interface WidgetState {
  status: RunStatus;
  stepIndex: number;
  maxSteps: number;
  action?: PlannerAction | null;
  message: string;
  screenshot?: {
    width: number;
    height: number;
    left?: number;
    top?: number;
  } | null;
  updatedAt: string;
}

export interface CursorWidgetState {
  active: boolean;
  status: RunStatus;
  stepIndex: number;
  screenshot?: {
    width: number;
    height: number;
    left?: number;
    top?: number;
  } | null;
  updatedAt: string;
}
