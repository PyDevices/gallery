/** Reusable direct MicroPython runner for first-party Read the Docs embeds. */
(function () {
  const RUNTIME_URL = "https://PyDevices.github.io/vendor/micropython/micropython.mjs";
  const state = { phase: "idle", errors: [], mp: null, activeOutput: null };
  window.__pydevicesDocsRuntime = state;

  function setAll(demos, text) {
    demos.forEach((demo) => {
      const status = demo.querySelector(".demo-status");
      if (status) status.textContent = text;
    });
  }

  async function runtime(demos) {
    if (state.mp) return state.mp;
    state.phase = "loading"; setAll(demos, "Downloading direct MicroPython…");
    const { loadMicroPython } = await import(RUNTIME_URL);
    state.mp = await loadMicroPython({
      stdout: (line) => { if (state.activeOutput) state.activeOutput.textContent += `${line}\n`; },
      stderr: (line) => { if (state.activeOutput) state.activeOutput.textContent += `${line}\n`; },
      heapsize: 16 * 1024 * 1024
    });
    // The PyDevices stack and the desktop board_config are frozen into the
    // runtime; nothing is installed. A demo's import fails loudly on a
    // runtime built without them.
    await state.mp.runPythonAsync(`
import os, sys
if "/" not in sys.path: sys.path.insert(0, "/")
os.chdir("/")
`);
    state.phase = "ready"; setAll(demos, "Ready");
    window.dispatchEvent(new CustomEvent("pydevices-docs-ready"));
    return state.mp;
  }

  async function execute(demo, demos) {
    const editor = demo.querySelector(".code-editor");
    const canvas = demo.querySelector("canvas");
    const output = demo.querySelector(".demo-output");
    const status = demo.querySelector(".demo-status");
    const button = demo.querySelector(".run-btn");
    if (!editor || !canvas) return;
    if (button) button.disabled = true;
    if (output) output.textContent = "";
    if (status) status.textContent = "Running…";
    try {
      const mp = await runtime(demos);
      state.activeOutput = output;
      const source = JSON.stringify(editor.value);
      const canvasId = JSON.stringify(canvas.id);
      await mp.runPythonAsync(`
from boarddev import env_set
env_set("PYDEVICES_CANVAS_ID", ${canvasId})
CANVAS_ID = ${canvasId}
_source = ${source}
exec(compile(_source, "<docs-demo>", "exec"), {"__name__": "__main__", "CANVAS_ID": CANVAS_ID})
`);
      if (status) status.textContent = "Active";
    } catch (error) {
      const detail = String(error && (error.stack || error));
      state.errors.push(detail); state.phase = "failed";
      if (output) output.textContent += `${detail}\n`;
      if (status) status.textContent = "Error";
      console.error("Direct documentation demo failed:", error);
      window.dispatchEvent(new CustomEvent("pydevices-docs-failed", { detail }));
    } finally {
      state.activeOutput = null;
      if (button) button.disabled = false;
    }
  }

  function init() {
    const demos = [...document.querySelectorAll(".pydevices-live-demo")];
    demos.forEach((demo, index) => {
      const canvas = demo.querySelector("canvas");
      const editor = demo.querySelector(".code-editor");
      const run = demo.querySelector(".run-btn");
      const reset = demo.querySelector(".reset-btn");
      if (canvas && !canvas.id) canvas.id = `live_canvas_${index}`;
      if (editor) demo._initialCode = editor.value;
      run?.addEventListener("click", () => execute(demo, demos));
      reset?.addEventListener("click", () => {
        if (editor) editor.value = demo._initialCode || "";
        execute(demo, demos);
      });
    });
    if (!demos.length) return;
    runtime(demos).then(() => {
      demos.forEach((demo) => execute(demo, demos));
    }).catch((error) => {
      state.phase = "failed"; state.errors.push(String(error));
      setAll(demos, "Load Failed"); console.error(error);
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
