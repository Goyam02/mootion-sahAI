import React, { useEffect, useRef, useState } from 'react';

interface MootionSimulationPlayerProps {
  html: string;
  title?: string;
}

export const MootionSimulationPlayer: React.FC<MootionSimulationPlayerProps> = ({ html, title }) => {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const iframe = iframeRef.current;
    if (!iframe) return;

    const blob = new Blob([html], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    iframe.src = url;

    const handleLoad = () => setLoading(false);
    iframe.addEventListener('load', handleLoad);

    return () => {
      URL.revokeObjectURL(url);
      iframe.removeEventListener('load', handleLoad);
    };
  }, [html]);

  return (
    <div className="relative w-full rounded-xl overflow-hidden border border-slate-800 bg-slate-950 shadow-2xl">
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-slate-950/90 z-10">
          <div className="flex flex-col items-center gap-3">
            <span className="w-8 h-8 border-4 border-violet-500/20 border-t-violet-500 rounded-full animate-spin" />
            <span className="text-xs text-slate-400 font-semibold animate-pulse">
              Loading Simulation...
            </span>
          </div>
        </div>
      )}
      {title && (
        <div className="absolute top-3 left-3 z-20 bg-slate-950/90 px-3 py-1.5 rounded-lg text-[10px] font-bold text-slate-400 border border-slate-800 shadow-md">
          {title}
        </div>
      )}
      <iframe
        ref={iframeRef}
        title={title || 'Mootion Simulation'}
        className="w-full h-[600px] md:h-[700px] border-0"
        sandbox="allow-scripts allow-same-origin"
      />
    </div>
  );
};
