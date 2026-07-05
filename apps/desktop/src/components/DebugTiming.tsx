import { Clock3 } from "lucide-react";
import type { TimingEvent } from "../lib/types";

interface Props {
  timings: TimingEvent[];
  enabled: boolean;
  onToggle: (enabled: boolean) => void;
}

export function DebugTiming({ timings, enabled, onToggle }: Props) {
  return (
    <section className="rounded-lg border border-line bg-panel p-4 shadow-soft">
      <label className="flex cursor-pointer items-center justify-between gap-3">
        <span className="flex items-center gap-2 font-semibold">
          <Clock3 size={18} />
          Debug timing
        </span>
        <input type="checkbox" checked={enabled} onChange={(event) => onToggle(event.target.checked)} />
      </label>
      {enabled ? (
        <div className="scrollbar-thin mt-3 max-h-52 space-y-2 overflow-auto">
          <div className="text-xs text-ink/55">Log file: logs/debug_timing.jsonl</div>
          {timings.length === 0 ? (
            <div className="text-sm text-ink/65">No timing events yet.</div>
          ) : (
            timings.slice(-8).map((timing) => (
              <div key={timing.step_index} className="rounded-md border border-line bg-white p-2 text-xs">
                <div className="mb-1 font-medium">Step {timing.step_index}</div>
                <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-ink/75">
                  <span>capture {timing.capture_ms ?? 0} ms</span>
                  <span>encode {timing.encode_ms ?? 0} ms</span>
                  <span>grid {timing.grid_ms ?? 0} ms</span>
                  <span>perception {timing.perception_ms ?? 0} ms</span>
                  <span>elements {timing.element_count ?? 0}</span>
                  <span>ollama {timing.ollama_ms ?? 0} ms</span>
                  <span>execute {timing.execute_ms ?? 0} ms</span>
                  <span>settle {timing.settle_ms ?? 0} ms</span>
                  <span>verify {timing.verify_ms ?? 0} ms</span>
                  <span>metrics {timing.metrics_ms ?? 0} ms</span>
                  <span>CPU {formatPercent(timing.cpu_percent)}</span>
                  <span>proc CPU {formatPercent(timing.process_cpu_percent)}</span>
                  <span>RAM {formatPercent(timing.ram_percent)}</span>
                  <span>RAM used {formatMb(timing.ram_used_mb)}</span>
                  <span>proc RSS {formatMb(timing.process_rss_mb)}</span>
                  <span>threads {timing.process_threads ?? "-"}</span>
                  <span>GPU {formatGpu(timing)}</span>
                </div>
                {timing.metrics_error ? <div className="mt-1 text-ink/55">{timing.metrics_error}</div> : null}
                {!timing.gpu_available && timing.gpu_source ? (
                  <div className="mt-1 text-ink/55">GPU: {timing.gpu_source}</div>
                ) : null}
              </div>
            ))
          )}
        </div>
      ) : null}
    </section>
  );
}

function formatPercent(value?: number): string {
  return typeof value === "number" ? `${value.toFixed(1)}%` : "-";
}

function formatMb(value?: number): string {
  return typeof value === "number" ? `${value.toFixed(1)} MB` : "-";
}

function formatGpu(timing: TimingEvent): string {
  if (!timing.gpu_available) {
    return "-";
  }
  const util = formatPercent(timing.gpu_util_percent);
  const memory =
    typeof timing.gpu_memory_used_mb === "number" && typeof timing.gpu_memory_total_mb === "number"
      ? ` ${timing.gpu_memory_used_mb.toFixed(0)}/${timing.gpu_memory_total_mb.toFixed(0)} MB`
      : "";
  return `${util}${memory}`;
}
