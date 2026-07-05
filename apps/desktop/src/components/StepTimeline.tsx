import { ListChecks } from "lucide-react";
import type { TimelineStep } from "../lib/types";

interface Props {
  steps: TimelineStep[];
}

export function StepTimeline({ steps }: Props) {
  return (
    <section className="flex min-h-0 flex-1 flex-col rounded-lg border border-line bg-panel p-4 shadow-soft">
      <div className="mb-3 flex items-center gap-2 font-semibold">
        <ListChecks size={18} />
        Step timeline
      </div>
      <div className="scrollbar-thin min-h-0 flex-1 space-y-3 overflow-auto pr-1">
        {steps.length === 0 ? (
          <div className="rounded-md border border-dashed border-line bg-white p-4 text-sm text-ink/65">
            Steps will appear as the worker plans and executes actions.
          </div>
        ) : (
          steps.map((step) => (
            <div key={step.step_index} className="rounded-md border border-line bg-white p-3">
              <div className="flex items-center justify-between gap-3">
                <div className="font-medium">
                  {step.step_index}. {step.action}
                </div>
                <span className="text-xs text-ink/60">{Math.round(step.confidence * 100)}%</span>
              </div>
              {step.thought ? <p className="mt-1 text-sm text-ink/75">{step.thought}</p> : null}
              <div className={step.ok === false ? "mt-2 text-sm text-amber" : "mt-2 text-sm text-moss"}>
                {step.result}
              </div>
            </div>
          ))
        )}
      </div>
    </section>
  );
}
