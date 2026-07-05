import { Command } from "@tauri-apps/plugin-shell";
import type { WorkerCommand, WorkerEvent } from "./types";

type Listener = (event: WorkerEvent) => void;

export class WorkerClient {
  private child: any | null = null;
  private command: any | null = null;
  private buffer = "";
  private listeners = new Set<Listener>();
  private starting: Promise<void> | null = null;

  subscribe(listener: Listener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  async send(command: WorkerCommand): Promise<void> {
    await this.ensureStarted();
    await this.child.write(`${JSON.stringify(command)}\n`);
  }

  async stop(): Promise<void> {
    if (this.child?.kill) {
      await this.child.kill();
    }
    this.child = null;
    this.command = null;
    this.starting = null;
  }

  private async ensureStarted(): Promise<void> {
    if (this.child) {
      return;
    }
    if (this.starting) {
      return this.starting;
    }
    this.starting = this.startWorker();
    return this.starting;
  }

  private async startWorker(): Promise<void> {
    try {
      this.command = Command.create(
        "python-computeruse-worker",
        ["-m", "computeruse.worker"],
        { cwd: "../.." },
      );
      this.command.stdout.on("data", (chunk: string | Uint8Array) => {
        this.consume(decodeChunk(chunk));
      });
      this.command.stderr.on("data", (chunk: string | Uint8Array) => {
        this.emit({ type: "error", message: decodeChunk(chunk) });
      });
      this.command.on("error", (error: string) => {
        this.emit({ type: "error", message: error });
      });
      this.command.on("close", () => {
        this.child = null;
        this.command = null;
        this.starting = null;
      });
      this.child = await this.command.spawn();
    } catch (error) {
      this.emit({
        type: "error",
        message: `Failed to start Python worker: ${String(error)}`,
      });
      this.starting = null;
      throw error;
    }
  }

  private consume(chunk: string): void {
    this.buffer += chunk;
    let newline = this.buffer.indexOf("\n");
    while (newline >= 0) {
      const line = this.buffer.slice(0, newline).trim();
      this.buffer = this.buffer.slice(newline + 1);
      if (line) {
        this.parseLine(line);
      }
      newline = this.buffer.indexOf("\n");
    }
  }

  private parseLine(line: string): void {
    try {
      this.emit(JSON.parse(line) as WorkerEvent);
    } catch {
      this.emit({ type: "error", message: `Worker emitted invalid JSON: ${line}` });
    }
  }

  private emit(event: WorkerEvent): void {
    for (const listener of this.listeners) {
      listener(event);
    }
  }
}

function decodeChunk(chunk: string | Uint8Array): string {
  return typeof chunk === "string" ? chunk : new TextDecoder().decode(chunk);
}
