"use client";

import { useEffect, useState } from "react";

// The backend sleeps on the free tier (~1 min to wake). Ping it on page load,
// and only show a note if it has not answered after 3 seconds.
export default function ServerWakeNotice() {
  const [waking, setWaking] = useState(false);

  useEffect(() => {
    let done = false;
    const timer = setTimeout(() => {
      if (!done) setWaking(true);
    }, 3000);
    fetch("/health")
      .catch(() => {})
      .finally(() => {
        done = true;
        clearTimeout(timer);
        setWaking(false);
      });
    return () => clearTimeout(timer);
  }, []);

  if (!waking) return null;
  return (
    <div className="note note-review rounded-none" role="status">
      The server is waking up. This can take up to a minute the first time.
    </div>
  );
}
