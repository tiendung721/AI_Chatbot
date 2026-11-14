(() => {
  const script = document.currentScript as HTMLScriptElement | null;
  const key = script?.dataset.assistant;
  if (!script?.src || !key || !/^[a-zA-Z0-9_-]{1,120}$/.test(key)) return;
  const origin = new URL(script.src).origin;
  // M1 deliberately supports same-origin embedding only; trusted external domains belong to M3.
  if (origin !== window.location.origin) return;
  const button = document.createElement("button");
  button.textContent = "Hỏi trợ lý";
  button.setAttribute("aria-expanded", "false");
  Object.assign(button.style, {
    position: "fixed",
    bottom: "24px",
    right: "24px",
    border: "0",
    borderRadius: "30px",
    padding: "14px 22px",
    background: "#146b64",
    color: "white",
    cursor: "pointer",
    zIndex: "1000",
    fontFamily: "Arial,sans-serif",
  });
  const iframe = document.createElement("iframe");
  iframe.src = `${origin}/embed/${encodeURIComponent(key)}`;
  iframe.title = "Trợ lý thông tin phường";
  iframe.hidden = true;
  Object.assign(iframe.style, {
    position: "fixed",
    bottom: "80px",
    right: "24px",
    width: "min(420px,calc(100vw - 32px))",
    height: "min(680px,calc(100svh - 110px))",
    border: "1px solid #dce5e7",
    borderRadius: "16px",
    background: "white",
    zIndex: "1000",
    boxShadow: "0 15px 60px #15352a22",
  });
  button.addEventListener("click", () => {
    iframe.hidden = !iframe.hidden;
    button.setAttribute("aria-expanded", String(!iframe.hidden));
    button.textContent = iframe.hidden ? "Hỏi trợ lý" : "Đóng trợ lý";
  });
  document.body.append(iframe, button);
})();
