import { useEffect, useState } from "react";

/** Barra fina no topo — progresso de leitura do artigo. */
export function ReadingProgress({ targetSelector = ".dossier-main" }: { targetSelector?: string }) {
  const [pct, setPct] = useState(0);

  useEffect(() => {
    const onScroll = () => {
      const el = document.querySelector(targetSelector) as HTMLElement | null;
      if (!el) {
        const doc = document.documentElement;
        const max = doc.scrollHeight - window.innerHeight;
        setPct(max > 0 ? Math.min(100, (window.scrollY / max) * 100) : 0);
        return;
      }
      const rect = el.getBoundingClientRect();
      const total = el.offsetHeight - window.innerHeight;
      const scrolled = -rect.top;
      setPct(total > 0 ? Math.min(100, Math.max(0, (scrolled / total) * 100)) : 0);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
    };
  }, [targetSelector]);

  return (
    <div className="read-progress" aria-hidden="true">
      <div className="read-progress-bar" style={{ width: `${pct}%` }} />
    </div>
  );
}
