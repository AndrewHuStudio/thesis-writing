import React, { useEffect } from 'react';
import { createRoot } from 'react-dom/client';
import { motion, useReducedMotion } from 'motion/react';

// Adapted from Motion-Primitives TextShimmer for the local Rhino waiting row.
// https://github.com/ibelick/motion-primitives/blob/main/components/core/text-shimmer.tsx
function TextShimmer({ children, duration = 1.4, spread = 2.5 }) {
  const reduced = useReducedMotion();
  useEffect(() => { window.chrome.webview.postMessage('ready'); }, []);
  return <motion.span role="status" className="shimmer"
    style={{ '--spread': children.length * spread + 'px' }}
    initial={{ backgroundPosition: '100% center' }}
    animate={{ backgroundPosition: reduced ? '100% center' : '0% center' }}
    transition={{ duration, repeat: reduced ? 0 : Infinity, ease: 'linear' }}>
    {children}
  </motion.span>;
}

createRoot(document.getElementById('root')).render(<TextShimmer>正在思考</TextShimmer>);
