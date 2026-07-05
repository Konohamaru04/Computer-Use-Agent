import { Camera, Pause, Play, Square, RotateCcw } from "lucide-react";
import type { RunStatus } from "../lib/types";

interface Props {
  task: string;
  setTask: (task: string) => void;
  dryRun: boolean;
  setDryRun: (dryRun: boolean) => void;
  maxSteps: number;
  setMaxSteps: (maxSteps: number) => void;
  status: RunStatus;
  canRun: boolean;
  onRun: () => void;
  onPause: () => void;
  onResume: () => void;
  onStop: () => void;
  onScreenshot: () => void;
}

export function TaskRunner({
  task,
  setTask,
  dryRun,
  setDryRun,
  maxSteps,
  setMaxSteps,
  status,
  canRun,
  onRun,
  onPause,
  onResume,
  onStop,
  onScreenshot,
}: Props) {
  const running = status === "running" || status === "starting";

  return (
    <section className="rounded-lg border border-line bg-panel p-4 shadow-soft">
      <div className="mb-3 flex items-center justify-between">
        <h1 className="text-lg font-semibold">Task runner</h1>
        <span className="rounded-full border border-line bg-white px-3 py-1 text-xs capitalize">
          {status}
        </span>
      </div>
      <textarea
        className="h-32 w-full resize-none rounded-md border border-line bg-white p-3 outline-none focus:border-moss"
        placeholder="Open Chrome, go to YouTube, search for TWICE, and open the first video."
        value={task}
        onChange={(event) => setTask(event.target.value)}
      />
      <div className="mt-3 grid grid-cols-2 gap-3">
        <label className="flex items-center gap-2 rounded-md border border-line bg-white px-3 py-2 text-sm">
          <input
            type="checkbox"
            checked={dryRun}
            onChange={(event) => setDryRun(event.target.checked)}
          />
          Dry run
        </label>
        <label className="flex items-center gap-2 rounded-md border border-line bg-white px-3 py-2 text-sm">
          Max
          <input
            className="w-full bg-transparent text-right outline-none"
            min={1}
            max={200}
            type="number"
            value={maxSteps}
            onChange={(event) => setMaxSteps(Number(event.target.value))}
          />
        </label>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-2">
        <button
          className="flex items-center justify-center gap-2 rounded-md bg-moss px-3 py-2 font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
          type="button"
          disabled={!canRun || running}
          onClick={onRun}
        >
          <Play size={16} />
          Run
        </button>
        {status === "paused" ? (
          <button
            className="flex items-center justify-center gap-2 rounded-md border border-line bg-white px-3 py-2"
            type="button"
            onClick={onResume}
          >
            <RotateCcw size={16} />
            Resume
          </button>
        ) : (
          <button
            className="flex items-center justify-center gap-2 rounded-md border border-line bg-white px-3 py-2 disabled:cursor-not-allowed disabled:opacity-50"
            type="button"
            disabled={!running}
            onClick={onPause}
          >
            <Pause size={16} />
            Pause
          </button>
        )}
        <button
          className="flex items-center justify-center gap-2 rounded-md border border-line bg-white px-3 py-2"
          type="button"
          onClick={onScreenshot}
        >
          <Camera size={16} />
          Screenshot
        </button>
        <button
          className="flex items-center justify-center gap-2 rounded-md border border-amber px-3 py-2 text-amber disabled:cursor-not-allowed disabled:opacity-50"
          type="button"
          disabled={!running && status !== "paused"}
          onClick={onStop}
        >
          <Square size={16} />
          Stop
        </button>
      </div>
    </section>
  );
}
