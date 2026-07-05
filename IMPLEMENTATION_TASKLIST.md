# ComputerUse Implementation Tasklist

## Current MVP Scope

- [x] Create implementation tasklist markdown.
- [x] Create initial directory layout.
- [x] Create Python project scaffold and dependency metadata.
- [x] Implement worker JSON-message protocol.
- [x] Implement Ollama model listing and model ranking.
- [x] Implement screenshot capture to `screenshots/current.png`.
- [x] Implement mouse and keyboard action handlers.
- [x] Implement Pydantic action validation.
- [x] Implement active JSON session read/write.
- [x] Implement observe-plan-act loop.
- [x] Add CLI command: `computeruse run "<task>"`.
- [x] Create Tauri plus React desktop scaffold.
- [x] Add GUI task runner with model selector, screenshot preview, timeline, pause/stop, and dry-run controls.
- [x] Add dry-run mode that validates model actions without executing mouse or keyboard events.
- [x] Add README usage instructions.
- [x] Run practical validation checks and record known gaps.

## Change Request: On-Screen Widget, Screenshot Preview, Pointer Coordinate Mapping

- [x] Add a persistent always-on-top status widget window along the screen border.
- [x] Forward worker status, current step, model action, and tool result events to the widget.
- [x] Enable Tauri asset protocol access for `screenshots/current.png`.
- [x] Normalize Windows screenshot paths and cache-bust the preview URL on each capture.
- [x] Include screenshot monitor origin and monitor dimensions in screenshot events.
- [x] Map pointer-action coordinates from screenshot pixels into desktop coordinates before PyAutoGUI execution.
- [x] Validate and report pointer coordinate mapping in dry-run mode.
- [x] Update planner prompt so the model ignores the ComputerUse widget and returns screenshot-pixel coordinates.
- [x] Make the always-on-top widget draggable and preserve its last dragged position.
- [x] Set Python worker DPI awareness before screenshot capture and PyAutoGUI input.
- [x] Replace PyAutoGUI-size-based pointer scaling with direct screenshot-pixel to monitor-pixel mapping.
- [x] Close the widget automatically when the main app window closes.
- [x] Generate a labeled coordinate-grid screenshot before each Ollama planner call.
- [x] Send the grid screenshot to the LLM while preserving original screenshot dimensions for execution.
- [x] Update planner prompt to use the graph grid for x/y coordinate estimation.

## Change Request: Cursor Coordinate Widget And Move-Then-Click Targeting

- [x] Add a hidden Tauri cursor-coordinate widget window that activates when a task starts.
- [x] Broadcast task status, step index, and latest screenshot bounds to the cursor widget.
- [x] Attach the cursor widget near the OS pointer and show screenshot-pixel plus screen-pixel coordinates.
- [x] Make the cursor widget always-on-top and click-through so it does not block automation actions.
- [x] Hide the cursor widget when the task is stopped, cancelled, done, failed, or the app exits.
- [x] Update the planner system prompt to move first, verify with the next screenshot, then click only after confirmation.
- [x] Update the per-step user prompt with the cursor widget coordinate contract.

## Change Request: Separate Cursor Marker Ring

- [x] Keep the existing cursor-coordinate widget as the offset coordinate label.
- [x] Add a separate hidden Tauri cursor-marker window that activates with the task loop.
- [x] Center a high-contrast red/yellow ring and crosshair around the OS cursor position.
- [x] Make the marker always-on-top and click-through so it does not block automation actions.
- [x] Broadcast the cursor active state to both the coordinate widget and marker widget.
- [x] Close the marker widget automatically when the main app window closes.
- [x] Update planner prompts so the model uses the marker ring center as the visible cursor position.

## Change Request: Larger Planner Grid Labels

- [x] Replace the tiny default grid font with a larger TrueType font when available.
- [x] Increase major grid line and border thickness for better model visibility.
- [x] Draw high-contrast x/y label boxes with larger padding and text stroke.
- [x] Remove crowded corner labels so coordinate references stay readable.
- [x] Update planner prompts to mention the large edge labels.

## Change Request: Smaller Cursor Marker

- [x] Reduce the cursor marker window from 72px to 48px.
- [x] Thin the marker rings, crosshair, glow, and center dot.
- [x] Keep the coordinate widget unchanged.
- [x] Update planner wording to describe the marker as small.

## Change Request: Side-By-Side Cursor Indicator Layout

- [x] Position the coordinate widget beside the cursor marker instead of below it.
- [x] Vertically center the coordinate widget against the cursor marker center.
- [x] Flip the coordinate widget to the left side near the screenshot right edge.
- [x] Update planner wording so the coordinate widget and marker are interpreted together.

## Change Request: Non-Obscuring Planner Rulers

- [x] Move coordinate labels out of the screenshot content into external top and left rulers.
- [x] Replace heavy in-image grid lines with faint guide lines aligned to the rulers.
- [x] Preserve original screenshot coordinate semantics even though the planner image has a larger ruler canvas.
- [x] Update planner prompts to use ruler labels and avoid planner-canvas coordinates.
- [x] Validate the ruler layout against the provided Steam taskbar icon screenshot.

## Change Request: Auto-Minimize On Run

- [x] Minimize the main Tauri window when Run is clicked.
- [x] Start the worker task after the minimize request settles so screenshots are less likely to include the app.
- [x] Keep the status, cursor coordinate, and cursor marker helper windows independent of the minimized main window.
- [x] Add the main-window Tauri permission required for minimize.

## Change Request: Post-Action Screenshot Settle Delay

- [x] Increase the default post-action settle delay from 400 ms to 1200 ms.
- [x] Wait after real actions before capturing the verification screenshot.
- [x] Skip the extra settle delay for explicit `wait` and `screenshot` actions.
- [x] Keep the settle wait responsive to pause and stop requests.
- [x] Surface `settle_ms` in debug timing events and the GUI debug drawer.

## Change Request: Element-Based Targeting

- [x] Add a screen element schema for detected UI targets.
- [x] Collect visible Windows UI Automation elements for the current screenshot.
- [x] Add `click_element` and `move_element` actions with `element_id` validation.
- [x] Resolve element actions to the detected clickable point or bounds center at execution time.
- [x] Draw compact `E#` markers on the planner screenshot.
- [x] Include detected element IDs, names, roles, bounds, and click points in the planner prompt.
- [x] Update planner instructions to prefer element IDs over raw coordinate guessing.
- [x] Surface perception timing and element count in debug timing events.

## Change Request: Foreground-Safe Semantic Targeting

- [x] Diagnose the failed session: UIA exposed background Chrome/YouTube controls whose click points were covered by VS Code.
- [x] Filter UIA elements using Windows `WindowFromPoint` hit-testing at each candidate click point.
- [x] Report how many occluded elements were filtered from the visible element list.
- [x] Add `click_target` and `move_target` actions that accept a natural-language target query.
- [x] Resolve semantic target actions locally with fuzzy matching against visible element names and roles.
- [x] Refuse weak semantic matches instead of blindly clicking a low-confidence target.
- [x] Update planner prompts to prefer `click_target`, avoid stale IDs/coordinates, and treat the visible element list as the source of truth.

## Change Request: Latest Run Failure Recovery

- [x] Inspect the latest failed session and identify the failure at step 8.
- [x] Diagnose `click_target query="Search" role="ComboBox"` as a local matcher refusal, not an Ollama or mouse execution failure.
- [x] Mark stale element and semantic target refusals as recoverable tool failures so one safe refusal does not end the whole run.
- [x] Add a safe role-only input fallback for cases like a single unnamed visible `ComboBox` search field.
- [x] Keep ambiguous role-only input matches refused and recoverable.
- [x] Harden UIA collection so per-window/per-control COM errors are skipped instead of failing the full perception pass.
- [x] Limit full UIA descendant enumeration to foreground/shell surfaces.
- [x] Query UIA by prioritized clickable roles instead of unfiltered descendants.
- [x] Update the prompt so a model that mentions `E42` uses `click_element` rather than a vague `click_target`.
- [x] Add YouTube `/` search-focus guidance as a keyboard fallback.

## Change Request: Debug Performance Metrics And Log File

- [x] Add a `logs` runtime directory and `logs/debug_timing.jsonl` path.
- [x] Add `psutil` dependency for CPU, RAM, process, thread, and disk counters.
- [x] Add best-effort NVIDIA GPU probing through `nvidia-smi`.
- [x] Sample resource metrics once per completed agent step.
- [x] Merge CPU, RAM, process, disk, GPU, and metric-collection timing into worker timing events.
- [x] Persist expanded timing/resource metrics into `sessions/active_session.json` recent steps.
- [x] Append step timing/resource records to `logs/debug_timing.jsonl`.
- [x] Show CPU, process CPU, RAM, process RSS, threads, GPU, and metrics overhead in the GUI debug drawer.
- [x] Keep GPU metrics optional and non-fatal when `nvidia-smi` is unavailable.

## Change Request: Strict Pylance/Pyright Cleanup

- [x] Add repo-level `pyrightconfig.json` with strict type checking.
- [x] Fix local union narrowing in pointer/target action execution.
- [x] Add typed protocols around `pyautogui` mouse and keyboard calls.
- [x] Add typed boundaries around untyped `mss` and `pywinauto` APIs.
- [x] Tighten action validation, model selector, session schema, and metrics types.
- [x] Resolve Pillow/Pydantic strict-mode typing edge cases.

## Change Request: SQLite Run History Tracking

- [x] Add a SQLite data directory and history database path.
- [x] Add history session summary/detail schemas.
- [x] Add SQLite tables for session runs and per-step tracking.
- [x] Persist task lifecycle updates and step records to SQLite while keeping `active_session.json`.
- [x] Add worker commands/events for listing history and inspecting a run.
- [x] Add a GUI history panel for tracking previous runs without playback controls.
- [x] Validate Python typing, compile checks, and frontend build.

## Change Request: Built-In MCP Server For External Agents

- [x] Add a stdio MCP JSON-RPC server entrypoint.
- [x] Expose ComputerUse workflow guidance and action schema to MCP clients.
- [x] Expose observe, execute-step, session-tracking, and history tools.
- [x] Return structured JSON and screenshot image content from observe/verify tools.
- [x] Wire MCP step execution into the same action validation, executor, and SQLite history tracking.
- [x] Add CLI/package entrypoints and README setup instructions for Codex-style MCP clients.
- [x] Validate MCP initialize/tools/list/tools/call smoke checks.

## Change Request: Generic MCP Client Settings

- [x] Update README wording so the MCP server is documented as generic stdio MCP, not Codex-only.
- [x] Add paste-ready MCP settings for generic JSON clients, Claude Desktop, Cline, and Codex TOML.
- [x] Add an in-app MCP settings panel with the command, args, cwd, and JSON snippet.
- [x] Validate frontend typecheck and build after adding the settings panel.

## Change Request: Hide MCP Settings Panel

- [x] Remove the MCP settings card from the main desktop UI.
- [x] Keep the MCP server, README settings, and component code available for future use.
- [x] Validate frontend typecheck and build after hiding the panel.

## Validation Completed

- [x] `python -m compileall computeruse`
- [x] `python -m computeruse.cli --help`
- [x] Pydantic action parsing smoke check.
- [x] `npm audit --omit=dev`
- [x] `npm audit`
- [x] `npm run typecheck`
- [x] `npm run build`
- [x] `cargo check` in `apps/desktop/src-tauri`
- [x] `npm audit`
- [x] Re-ran `npm run typecheck` after adding the cursor widget.
- [x] Re-ran `npm run build` after adding the cursor widget.
- [x] Re-ran `cargo check` in `apps/desktop/src-tauri` after adding the cursor widget capability.
- [x] Re-ran `python -m compileall computeruse` after prompt updates.
- [x] Re-ran `npm audit` after this pass.
- [x] Re-ran `npm run typecheck` after adding the separate cursor marker.
- [x] Re-ran `npm run build` after adding the separate cursor marker.
- [x] Re-ran `cargo check` in `apps/desktop/src-tauri` after adding the cursor marker capability.
- [x] Re-ran `python -m compileall computeruse` after marker prompt updates.
- [x] Re-ran `npm audit` after adding the separate cursor marker.
- [x] Re-ran `python -m compileall computeruse` after enlarging planner grid labels.
- [x] Generated a neutral 1920x1080 planner grid validation image and visually checked label readability.
- [x] Re-ran `npm run typecheck` after shrinking the cursor marker.
- [x] Re-ran `npm run build` after shrinking the cursor marker.
- [x] Re-ran `cargo check` in `apps/desktop/src-tauri` after shrinking the cursor marker window.
- [x] Re-ran `python -m compileall computeruse` after marker prompt wording updates.
- [x] Re-ran `npm run typecheck` after side-by-side cursor indicator layout.
- [x] Re-ran `npm run build` after side-by-side cursor indicator layout.
- [x] Re-ran `python -m compileall computeruse` after side-by-side cursor prompt wording.
- [x] Re-ran `python -m compileall computeruse` after switching planner grid to external rulers.
- [x] Generated a planner-ruler validation image from the provided Steam icon test screenshot.
- [x] Re-ran `npm run typecheck` after adding auto-minimize on Run.
- [x] Re-ran `npm run build` after adding auto-minimize on Run.
- [x] Re-ran `cargo check` in `apps/desktop/src-tauri` after adding the minimize permission.
- [x] Ran AST syntax validation after adding post-action settle delay.
- [x] Re-ran `npm run typecheck` after adding `settle_ms` timing.
- [x] Installed `pywinauto` into `.venv` and the `python` environment on PATH for UI Automation targeting.
- [x] Installed the project editable into the `python` environment on PATH so the Tauri worker command can load runtime dependencies.
- [x] Ran UI Automation perception smoke test; detected 80 elements and generated `screenshots/planner.png` with element markers.
- [x] Re-ran the UI Automation perception and dry-run `click_element` smoke test with the exact `python` command used by Tauri.
- [x] Ran `click_element` and `move_element` Pydantic parsing smoke checks.
- [x] Ran dry-run `click_element` executor smoke check using a detected element.
- [x] Re-ran `.venv\Scripts\python.exe -m compileall computeruse` after element targeting changes.
- [x] Re-ran `python -m compileall computeruse` with the same `python` command used by Tauri.
- [x] Re-ran `npm run typecheck` after adding perception timing fields.
- [x] Re-ran `npm run build` after adding perception timing fields.
- [x] Re-ran `python -m compileall computeruse` after adding foreground-safe semantic targeting.
- [x] Ran foreground UIA smoke test; current screenshot filtered 47 occluded elements.
- [x] Ran `click_target` and `move_target` Pydantic parsing smoke checks.
- [x] Ran dry-run `click_target` positive smoke check against a visible concise button.
- [x] Ran dry-run `move_target` negative smoke check and confirmed weak/no-evidence targets are refused.
- [x] Re-ran `npm run typecheck` after semantic targeting changes.
- [x] Re-ran `npm run build` after semantic targeting changes.
- [x] Re-ran `python -m compileall computeruse` after latest-run recovery changes.
- [x] Ran synthetic regression for `click_target query="Search" role="ComboBox"` with one unnamed visible `ComboBox`.
- [x] Ran synthetic ambiguity regression and confirmed multiple unnamed `ComboBox` candidates are refused as recoverable.
- [x] Ran live dry-run positive and negative `click_target` checks.
- [x] Re-ran `npm run typecheck` after adding recoverable tool-result events.
- [x] Re-ran `npm run build` after adding recoverable tool-result events.
- [x] Installed updated Python dependencies into both `python` and `.venv`.
- [x] Ran metrics sampler smoke test and wrote a JSONL record to `logs/debug_timing.jsonl`.
- [x] Re-ran `python -m compileall computeruse` after adding performance metrics.
- [x] Re-ran `npm run typecheck` after adding debug metric fields.
- [x] Re-ran `npm run build` after updating the debug timing drawer.
- [x] Ran `npx pyright --project pyrightconfig.json`; strict pass reports 0 errors.
- [x] Re-ran `python -m compileall computeruse` after strict typing fixes.
- [x] Re-ran `npm run typecheck` after strict typing fixes.
- [x] Re-ran `npm run build` after strict typing fixes.
- [x] Ran isolated SQLite history smoke test with a temporary database.
- [x] Ran worker `list_history` command smoke test against the real database path.
- [x] Re-ran `python -m compileall computeruse` after SQLite history changes.
- [x] Re-ran `npx pyright --project pyrightconfig.json` after SQLite history changes.
- [x] Re-ran `npm run typecheck` after adding the history panel.
- [x] Re-ran `npm run build` after adding the history panel.
- [x] Ran no-bytecode Python syntax/import smoke after adding the MCP server.
- [x] Ran `npx pyright --project pyrightconfig.json` after adding the MCP server.
- [x] Ran MCP initialize, `tools/list`, and `computeruse_help` stdio smoke checks.
- [x] Ran MCP `computeruse_execute_step` dry-run wait smoke check without tracking.
- [x] Ran MCP session tracking smoke check with a temporary SQLite database.
- [x] Re-ran `npm run typecheck` after adding generic MCP settings panel.
- [x] Re-ran `npm --prefix apps/desktop run build` after adding generic MCP settings panel.
- [x] Re-ran `npm run typecheck` after hiding the MCP settings panel.
- [x] Re-ran `npm --prefix apps/desktop run build` after hiding the MCP settings panel.

## Known Gaps From This Pass

- [ ] Full live Ollama task execution was not run as part of this validation pass.
- [ ] Live Ollama planning was not exercised against an installed vision model.
- [ ] Live mouse/keyboard execution was not exercised outside dry-run-oriented validation.
- [ ] The always-on-top status, cursor coordinate, and cursor marker widgets were build/type/Rust checked but not visually verified in a live Tauri window during this pass.
- [ ] UI Automation perception currently takes about 1.7-2.9 seconds on this machine, so it should be optimized if it becomes noticeable compared with Ollama latency.

## Later Hardening

- [ ] Add explicit user-confirmation flow for destructive or external-effect actions.
- [ ] Add optional OpenCV visual-anchor targeting.
- [ ] Add pywinauto-based Windows-native window helpers.
- [ ] Package Python worker as a bundled Tauri sidecar.
