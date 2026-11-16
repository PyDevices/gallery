/** Direct MicroPython host for generated PyDevices hero applications. */
(function () {
  const state = { phase: "idle", heroes: [], errors: [] };
  window.__pydevicesHeroes = state;

  // Browsers require a user gesture before unlocking Web Audio. Most heroes
  // never touch audio and this is a no-op for them; the one that does (the
  // pydevices signal generator) just needs this armed so its first click
  // both unlocks audio and toggles the tone in the same gesture.
  let audioGestureArmed = false;
  function armAudioGesture() {
    if (audioGestureArmed) return;
    audioGestureArmed = true;
    // A gesture while the page is still loading finds no runtime to unlock, so
    // the listeners stay until one works.
    const tryEnable = () => {
      globalThis.Module?.pydevicesBridge?.enableAudio(false)?.then(() => {
        document.removeEventListener("pointerdown", tryEnable);
        document.removeEventListener("keydown", tryEnable);
      }).catch(() => {});
    };
    document.addEventListener("pointerdown", tryEnable);
    document.addEventListener("keydown", tryEnable);
  }
  armAudioGesture();
  async function launch(container) {
    const canvasId = container.dataset.heroCanvas || "hero_canvas";
    const appName = container.dataset.heroApp || "watch";
    const canvas = container.querySelector("canvas");
    const canvasWidth = (canvas && canvas.width) || 240;
    const canvasHeight = (canvas && canvas.height) || 240;
    const status = container.querySelector(".hero-canvas-status");
    const setStatus = (text) => { if (status) status.textContent = text; };
    const record = { app: appName, canvas: canvasId, phase: "loading" };
    state.heroes.push(record); state.phase = "loading";
    try {
      setStatus("Booting direct MicroPython…");
      const { loadMicroPython } = await import("/vendor/micropython/micropython.mjs");
      const mp = await loadMicroPython({
        stdout: (line) => console.log(`[${appName}] ${line}`),
        stderr: (line) => console.error(`[${appName}] ${line}`),
        heapsize: 16 * 1024 * 1024
      });
      setStatus(`Loading ${appName}…`);
      const response = await fetch(`/assets/apps/${appName}.py`, { cache: "no-store" });
      if (!response.ok) throw new Error(`${response.status} fetching ${appName}.py`);
      mp.FS.writeFile(`/${appName}.py`, await response.text());
      await mp.runPythonAsync(`
import os, sys
if "/" not in sys.path: sys.path.insert(0, "/")
os.chdir("/")
# The PyDevices stack and the desktop board_config are frozen into the
# runtime; nothing is installed. A runtime without them fails right here.
from boarddev import env_set
env_set("PYDEVICES_CANVAS_ID", ${JSON.stringify(canvasId)})
env_set("PYDEVICES_WIDTH", ${JSON.stringify(String(canvasWidth))})
env_set("PYDEVICES_HEIGHT", ${JSON.stringify(String(canvasHeight))})
env_set("PYDEVICES_TZ_OFFSET_MIN", ${JSON.stringify(String(new Date().getTimezoneOffset()))})
__import__(${JSON.stringify(appName)})
`);
      record.phase = "ready"; record.mp = mp;
      container.classList.add("active");
      if (status) status.remove();
      state.phase = state.heroes.every((hero) => hero.phase === "ready") ? "ready" : "loading";
      window.dispatchEvent(new CustomEvent("pydevices-heroes-ready", { detail: record }));
    } catch (error) {
      record.phase = "failed"; record.error = String(error && (error.stack || error));
      state.errors.push(record.error); state.phase = "failed";
      setStatus("Live preview offline"); console.error("Direct hero failed:", error);
      window.dispatchEvent(new CustomEvent("pydevices-heroes-failed", { detail: record }));
    }
  }
  function start() { document.querySelectorAll("[data-hero-canvas]").forEach(launch); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
