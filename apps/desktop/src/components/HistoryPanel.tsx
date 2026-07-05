import { History, RefreshCw } from "lucide-react";
import type { HistorySessionDetail, HistorySessionSummary, SessionStatus } from "../lib/types";

interface Props {
  sessions: HistorySessionSummary[];
  selectedSession: HistorySessionDetail | null;
  onRefresh: () => void;
  onSelect: (sessionId: string) => void;
}

export function HistoryPanel({ sessions, selectedSession, onRefresh, onSelect }: Props) {
  return (
    <section className="flex max-h-80 min-h-0 flex-col rounded-lg border border-line bg-panel p-4 shadow-soft">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 font-semibold">
          <History size={18} />
          Run history
        </div>
        <button
          type="button"
          onClick={onRefresh}
          className="inline-flex items-center gap-1 rounded-md border border-line bg-white px-2 py-1 text-xs text-ink/75 hover:bg-[#ece9de]"
        >
          <RefreshCw size={13} />
          Refresh
        </button>
      </div>

      <div className="scrollbar-thin min-h-0 flex-1 space-y-2 overflow-auto pr-1">
        {sessions.length === 0 ? (
          <div className="rounded-md border border-dashed border-line bg-white p-3 text-sm text-ink/65">
            Completed and active runs will appear here.
          </div>
        ) : (
          sessions.map((session) => {
            const selected = selectedSession?.session_id === session.session_id;
            return (
              <button
                key={session.session_id}
                type="button"
                onClick={() => onSelect(session.session_id)}
                className={
                  selected
                    ? "w-full rounded-md border border-moss bg-white p-3 text-left shadow-sm"
                    : "w-full rounded-md border border-line bg-white p-3 text-left hover:border-moss/60"
                }
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="truncate text-sm font-medium">{session.task}</div>
                    <div className="mt-1 text-xs text-ink/55">
                      {formatDate(session.updated_at)} · step {session.step_index} · {session.selected_model}
                    </div>
                  </div>
                  <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs ${statusClass(session.status)}`}>
                    {session.status}
                  </span>
                </div>
                {session.summary ? <div className="mt-2 line-clamp-2 text-xs text-ink/65">{session.summary}</div> : null}
              </button>
            );
          })
        )}

        {selectedSession ? (
          <div className="rounded-md border border-line bg-white p-3">
            <div className="mb-2 text-sm font-semibold">Selected run</div>
            <div className="space-y-1 text-xs text-ink/70">
              <div>Status: {selectedSession.status}</div>
              <div>Created: {formatDate(selectedSession.created_at)}</div>
              <div>Updated: {formatDate(selectedSession.updated_at)}</div>
              <div>Steps tracked: {selectedSession.steps.length}</div>
            </div>
            {selectedSession.steps.length > 0 ? (
              <div className="mt-3 space-y-2">
                {selectedSession.steps.slice(-5).map((step) => (
                  <div key={step.step_index} className="rounded border border-line bg-[#ece9de]/40 p-2 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-medium">
                        {step.step_index}. {step.action}
                      </span>
                      <span className={step.ok === false ? "text-amber" : "text-moss"}>
                        {step.ok === false ? "failed" : "ok"}
                      </span>
                    </div>
                    {step.thought ? <div className="mt-1 line-clamp-2 text-ink/65">{step.thought}</div> : null}
                    <div className="mt-1 line-clamp-2 text-ink/60">{step.result}</div>
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}
      </div>
    </section>
  );
}

function statusClass(status: SessionStatus): string {
  if (status === "done") {
    return "bg-moss/15 text-moss";
  }
  if (status === "running") {
    return "bg-[#dfe9f3] text-ink";
  }
  if (status === "cancelled") {
    return "bg-ink/10 text-ink/70";
  }
  return "bg-amber/15 text-amber";
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}
