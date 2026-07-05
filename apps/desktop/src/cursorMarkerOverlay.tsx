import React, { useEffect, useRef, useState } from "react";
import ReactDOM from "react-dom/client";
import { listen } from "@tauri-apps/api/event";
import { cursorPosition, getCurrentWindow, PhysicalPosition } from "@tauri-apps/api/window";
import type { CursorWidgetState } from "./lib/types";
import "./cursorMarkerOverlay.css";

const MARKER_SIZE = 48;
const MARKER_CENTER = MARKER_SIZE / 2;
const POLL_MS = 50;

const defaultState: CursorWidgetState = {
  active: false,
  status: "idle",
  stepIndex: 0,
  screenshot: null,
  updatedAt: new Date().toISOString(),
};

function CursorMarkerOverlay() {
  const [state, setState] = useState<CursorWidgetState>(() => {
    try {
      const saved = window.localStorage.getItem("computeruse.cursor.state");
      return saved ? { ...defaultState, ...JSON.parse(saved) } : defaultState;
    } catch {
      return defaultState;
    }
  });
  const stateRef = useRef(state);

  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  useEffect(() => {
    let unlistenStatus: (() => void) | undefined;
    listen<CursorWidgetState>("computeruse-cursor-status", (event) => {
      setState({ ...defaultState, ...event.payload });
    }).then((fn) => {
      unlistenStatus = fn;
    });

    return () => {
      unlistenStatus?.();
    };
  }, []);

  useEffect(() => {
    const appWindow = getCurrentWindow();
    let cancelled = false;
    let timer: number | undefined;

    async function syncMarker() {
      try {
        const point = await cursorPosition();
        if (cancelled) {
          return;
        }
        await appWindow.setPosition(
          new PhysicalPosition(
            Math.round(point.x - MARKER_CENTER),
            Math.round(point.y - MARKER_CENTER),
          ),
        );
        if (stateRef.current.active) {
          await appWindow.show();
        }
      } catch {
        // This marker is a visual aid only; failures should not interrupt automation.
      }
    }

    async function configure() {
      try {
        await appWindow.setAlwaysOnTop(true);
        await appWindow.setIgnoreCursorEvents(true);
        if (!stateRef.current.active) {
          await appWindow.hide();
          return;
        }
        await syncMarker();
        timer = window.setInterval(syncMarker, POLL_MS);
      } catch {
        // The coordinate widget and main task loop can continue without this marker.
      }
    }

    configure();

    return () => {
      cancelled = true;
      if (timer !== undefined) {
        window.clearInterval(timer);
      }
      if (!stateRef.current.active) {
        appWindow.hide().catch(() => undefined);
      }
    };
  }, [state.active]);

  return (
    <div className={`cursorMarker ${state.active ? "cursorMarker-active" : ""}`}>
      <div className="cursorMarkerRing" />
      <div className="cursorMarkerRingInner" />
      <div className="cursorMarkerCross cursorMarkerCross-horizontal" />
      <div className="cursorMarkerCross cursorMarkerCross-vertical" />
      <div className="cursorMarkerDot" />
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <CursorMarkerOverlay />
  </React.StrictMode>,
);
