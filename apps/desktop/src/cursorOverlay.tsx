import React, { useEffect, useRef, useState } from "react";
import ReactDOM from "react-dom/client";
import { listen } from "@tauri-apps/api/event";
import { cursorPosition, getCurrentWindow, PhysicalPosition } from "@tauri-apps/api/window";
import type { CursorWidgetState } from "./lib/types";
import "./cursorOverlay.css";

const CURSOR_WIDGET_WIDTH = 178;
const CURSOR_WIDGET_HEIGHT = 58;
const CURSOR_MARKER_SIZE = 48;
const CURSOR_WIDGET_GAP = 10;
const POLL_MS = 100;

const defaultState: CursorWidgetState = {
  active: false,
  status: "idle",
  stepIndex: 0,
  screenshot: null,
  updatedAt: new Date().toISOString(),
};

type CursorPoint = {
  x: number;
  y: number;
};

function CursorOverlay() {
  const [state, setState] = useState<CursorWidgetState>(() => {
    try {
      const saved = window.localStorage.getItem("computeruse.cursor.state");
      return saved ? { ...defaultState, ...JSON.parse(saved) } : defaultState;
    } catch {
      return defaultState;
    }
  });
  const [cursor, setCursor] = useState<CursorPoint | null>(null);
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

    async function syncCursorWidget() {
      try {
        const point = await cursorPosition();
        if (cancelled) {
          return;
        }
        const current = { x: Math.round(point.x), y: Math.round(point.y) };
        setCursor(current);
        const nextPosition = getWidgetPosition(current, stateRef.current.screenshot);
        await appWindow.setPosition(new PhysicalPosition(nextPosition.x, nextPosition.y));
        if (stateRef.current.active) {
          await appWindow.show();
        }
      } catch {
        // A cursor widget failure should not interfere with the automation run.
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
        await syncCursorWidget();
        timer = window.setInterval(syncCursorWidget, POLL_MS);
      } catch {
        // The main app still carries the run even if this helper window cannot be configured.
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

  const screenshotBounds = state.screenshot ?? null;
  const relative = cursor ? getRelativeCursor(cursor, screenshotBounds) : null;
  const insideScreenshot =
    relative !== null &&
    screenshotBounds !== null &&
    relative.x >= 0 &&
    relative.y >= 0 &&
    relative.x < screenshotBounds.width &&
    relative.y < screenshotBounds.height;

  return (
    <div className={`cursorWidget ${state.active ? "cursorWidget-active" : ""}`}>
      <div className="cursorTitle">
        Cursor <span>step {state.stepIndex}</span>
      </div>
      <div className="cursorCoords">
        {relative ? (
          <>
            <strong>img x={relative.x} y={relative.y}</strong>
            <span>
              screen x={cursor?.x ?? 0} y={cursor?.y ?? 0}
            </span>
          </>
        ) : (
          <>
            <strong>img x=-- y=--</strong>
            <span>waiting for cursor</span>
          </>
        )}
      </div>
      {screenshotBounds && !insideScreenshot && relative ? (
        <div className="cursorWarning">outside screenshot</div>
      ) : null}
    </div>
  );
}

function getRelativeCursor(
  cursor: CursorPoint,
  screenshot: CursorWidgetState["screenshot"],
): CursorPoint | null {
  if (!screenshot) {
    return { x: cursor.x, y: cursor.y };
  }
  return {
    x: Math.round(cursor.x - (screenshot.left ?? 0)),
    y: Math.round(cursor.y - (screenshot.top ?? 0)),
  };
}

function getWidgetPosition(
  cursor: CursorPoint,
  screenshot: CursorWidgetState["screenshot"],
): CursorPoint {
  const bounds = screenshot
    ? {
        left: screenshot.left ?? 0,
        top: screenshot.top ?? 0,
        right: (screenshot.left ?? 0) + screenshot.width,
        bottom: (screenshot.top ?? 0) + screenshot.height,
      }
    : null;

  const markerRadius = CURSOR_MARKER_SIZE / 2;
  let x = cursor.x + markerRadius + CURSOR_WIDGET_GAP;
  let y = cursor.y - CURSOR_WIDGET_HEIGHT / 2;

  if (bounds) {
    if (x + CURSOR_WIDGET_WIDTH > bounds.right) {
      x = cursor.x - markerRadius - CURSOR_WIDGET_GAP - CURSOR_WIDGET_WIDTH;
    }
    x = clamp(x, bounds.left, Math.max(bounds.left, bounds.right - CURSOR_WIDGET_WIDTH));
    y = clamp(y, bounds.top, Math.max(bounds.top, bounds.bottom - CURSOR_WIDGET_HEIGHT));
  }

  return { x: Math.round(x), y: Math.round(y) };
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <CursorOverlay />
  </React.StrictMode>,
);
