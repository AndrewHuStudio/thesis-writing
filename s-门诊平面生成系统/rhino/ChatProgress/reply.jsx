import React, { useEffect, useLayoutEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { Streamdown } from "streamdown";
import "streamdown/styles.css";
import "./reply-layout.css";

const bridge = window.chrome.webview;
const animation = {
  animation: "fadeIn", sep: "char", duration: 200, easing: "ease-out",
  stagger: 12, maxBacklogMs: 160
};
const components = {
  strong: ({ children }) => <strong>{children}</strong>,
  pre: ({ children }) => <pre>{children}</pre>,
  code: ({ children }) => <code>{children}</code>,
  table: ({ children }) => <div className="table-scroll"><table>{children}</table></div>,
  a: ({ href, children }) => /^https?:\/\//i.test(href || "")
    ? <a href={href} target="_blank" rel="noopener noreferrer">{children}</a>
    : <span>{children}</span>,
  img: ({ alt }) => <span>{alt}</span>
};

function Reply() {
  const [text, setText] = useState("");
  const [active, setActive] = useState(false);
  useEffect(() => {
    let settle;
    function receive({ data }) {
      clearTimeout(settle);
      if (typeof data.text === "string") {
        setText(data.text);
        setActive(!window.matchMedia("(prefers-reduced-motion: reduce)").matches);
      }
      // Let the final stagger and fade finish before removing animated spans.
      if (data.done) settle = setTimeout(() => setActive(false), animation.duration + animation.maxBacklogMs + 32);
    }
    bridge.addEventListener("message", receive);
    bridge.postMessage("ready");
    return () => {
      clearTimeout(settle);
      bridge.removeEventListener("message", receive);
    };
  }, []);
  // WebView2 can defer ResizeObserver while its native window is hidden.
  useLayoutEffect(() => {
    if (text) bridge.postMessage("height:" + Math.ceil(document.getElementById("root").getBoundingClientRect().height));
  }, [text, active]);
  useLayoutEffect(() => {
    const root = document.getElementById("root");
    const measure = () => bridge.postMessage("height:" + Math.ceil(root.getBoundingClientRect().height));
    const observer = new ResizeObserver(measure);
    observer.observe(root);
    return () => observer.disconnect();
  }, []);
  return <Streamdown animated={animation} isAnimating={active} controls={false}
    components={components} lineNumbers={false} skipHtml>{text}</Streamdown>;
}

// The Rhino transcript owns vertical scrolling, including over a reply.
window.addEventListener("wheel", (event) => {
  if (event.ctrlKey || event.shiftKey || Math.abs(event.deltaX) > Math.abs(event.deltaY)) return;
  event.preventDefault();
  const unit = event.deltaMode === 1 ? 20 : event.deltaMode === 2 ? window.innerHeight : 1;
  bridge.postMessage("scroll:" + event.deltaY * unit);
}, { passive: false });
createRoot(document.getElementById("root")).render(<Reply />);
