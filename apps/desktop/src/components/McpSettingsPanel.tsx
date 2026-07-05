import { Clipboard, PlugZap } from "lucide-react";

const PROJECT_ROOT = "E:\\ComputerUse";
const PYTHON_COMMAND = "python";
const VENV_PYTHON_COMMAND = "E:\\ComputerUse\\.venv\\Scripts\\python.exe";
const MCP_ARGS = ["-m", "computeruse.mcp_server"];

const genericConfig = {
  mcpServers: {
    computeruse: {
      command: PYTHON_COMMAND,
      args: MCP_ARGS,
      cwd: PROJECT_ROOT,
    },
  },
};

const venvConfig = {
  mcpServers: {
    computeruse: {
      command: VENV_PYTHON_COMMAND,
      args: MCP_ARGS,
      cwd: PROJECT_ROOT,
    },
  },
};

const genericConfigText = JSON.stringify(genericConfig, null, 2);
const venvConfigText = JSON.stringify(venvConfig, null, 2);

export function McpSettingsPanel() {
  return (
    <section className="rounded-lg border border-line bg-panel p-4 shadow-soft">
      <div className="mb-3 flex items-center gap-2 font-semibold">
        <PlugZap size={18} />
        MCP settings
      </div>
      <div className="space-y-2 text-xs text-ink/70">
        <div className="rounded-md border border-line bg-white p-2">
          <div className="mb-1 font-medium text-ink">Generic stdio server</div>
          <div>Command: {PYTHON_COMMAND}</div>
          <div>Args: {MCP_ARGS.join(" ")}</div>
          <div>Cwd: {PROJECT_ROOT}</div>
        </div>
        <div className="rounded-md border border-line bg-white p-2">
          <div className="mb-2 flex items-center justify-between gap-2">
            <span className="font-medium text-ink">mcpServers JSON</span>
            <CopyButton text={genericConfigText} />
          </div>
          <pre className="scrollbar-thin max-h-32 overflow-auto whitespace-pre-wrap text-[11px] leading-relaxed">
            {genericConfigText}
          </pre>
        </div>
        <details className="rounded-md border border-line bg-white p-2">
          <summary className="cursor-pointer font-medium text-ink">Use repo venv path</summary>
          <div className="mt-2 flex items-center justify-between gap-2">
            <span>For agents that do not inherit your activated shell.</span>
            <CopyButton text={venvConfigText} />
          </div>
          <pre className="scrollbar-thin mt-2 max-h-32 overflow-auto whitespace-pre-wrap text-[11px] leading-relaxed">
            {venvConfigText}
          </pre>
        </details>
        <div className="text-ink/60">
          Paste this into any MCP host that supports local stdio servers. Client-specific files differ, but the
          command, args, and cwd stay the same.
        </div>
      </div>
    </section>
  );
}

function CopyButton({ text }: { text: string }) {
  return (
    <button
      type="button"
      className="inline-flex items-center gap-1 rounded-md border border-line px-2 py-1 text-[11px] text-ink/70 hover:bg-[#ece9de]"
      onClick={() => navigator.clipboard.writeText(text).catch(() => undefined)}
    >
      <Clipboard size={12} />
      Copy
    </button>
  );
}
