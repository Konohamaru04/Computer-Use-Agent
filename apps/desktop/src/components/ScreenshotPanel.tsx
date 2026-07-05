import { Monitor } from "lucide-react";

interface Props {
  src: string;
  width?: number;
  height?: number;
}

export function ScreenshotPanel({ src, width, height }: Props) {
  return (
    <section className="flex min-h-0 flex-1 flex-col rounded-lg border border-line bg-panel p-4 shadow-soft">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2 font-semibold">
          <Monitor size={18} />
          Current screenshot
        </div>
        {width && height ? (
          <span className="text-xs text-ink/65">
            {width} x {height}
          </span>
        ) : null}
      </div>
      <div className="flex min-h-[360px] flex-1 items-center justify-center overflow-hidden rounded-md border border-line bg-[#22251f]">
        {src ? (
          <img className="h-full max-h-full w-full object-contain" src={src} alt="Current desktop screenshot" />
        ) : (
          <div className="text-sm text-white/70">No screenshot captured yet.</div>
        )}
      </div>
    </section>
  );
}
