import { Cpu } from "lucide-react";
import type { ModelInfo } from "../lib/types";

interface Props {
  models: ModelInfo[];
  selectedModel: string;
  onChange: (model: string) => void;
  onRefresh: () => void;
}

export function ModelSelector({ models, selectedModel, onChange, onRefresh }: Props) {
  return (
    <section className="rounded-lg border border-line bg-panel p-4 shadow-soft">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 font-semibold">
          <Cpu size={18} />
          Ollama model
        </div>
        <button
          className="rounded-md border border-line px-3 py-1.5 text-sm hover:bg-white"
          type="button"
          onClick={onRefresh}
        >
          Refresh
        </button>
      </div>
      <select
        className="w-full rounded-md border border-line bg-white px-3 py-2 outline-none focus:border-moss"
        value={selectedModel}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="">Select a model</option>
        {models.map((model) => (
          <option key={model.name} value={model.name}>
            {model.vision ? "Vision - " : ""}
            {model.name}
          </option>
        ))}
      </select>
      <div className="mt-2 text-xs text-ink/65">
        {models.length === 0
          ? "No models loaded yet."
          : `${models.filter((model) => model.vision).length} vision-ranked models found.`}
      </div>
    </section>
  );
}
