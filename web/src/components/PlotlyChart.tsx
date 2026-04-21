"use client";

import dynamic from "next/dynamic";
import { useMemo } from "react";

// Plotly cannot be SSR'd because it relies heavily on window object
const Plot = dynamic(() => import("react-plotly.js"), { 
  ssr: false,
  loading: () => (
    <div className="w-full h-full flex items-center justify-center bg-gray-50/50 rounded-lg animate-pulse">
      <div className="flex flex-col items-center gap-2">
         <div className="w-8 h-8 border-4 border-blue-200 border-t-blue-500 rounded-full animate-spin"></div>
         <span className="text-xs text-gray-400 font-medium tracking-wide">Loading Visualization...</span>
      </div>
    </div>
  )
});

interface PlotlyChartProps {
  data: any[];
  layout: any;
  config?: any;
  className?: string;
  height?: number | string;
}

export function PlotlyChart({ data, layout, config, className, height = "100%" }: PlotlyChartProps) {
  
  // Merge default responsive layout with incoming layout
  const responsiveLayout = useMemo(() => {
    return {
      autosize: true,
      margin: { t: 20, r: 20, b: 40, l: 40 },
      paper_bgcolor: 'transparent',
      plot_bgcolor: 'transparent',
      font: {
        family: 'system-ui, -apple-system, sans-serif',
        color: '#4B5563'
      },
      ...layout
    };
  }, [layout]);

  const defaultConfig = {
    displayModeBar: true,
    displaylogo: false,
    responsive: true,
    modeBarButtonsToRemove: ['lasso2d', 'select2d'],
    ...config
  };

  return (
    <div className={`w-full ${className}`} style={{ height }}>
      <Plot
        data={data}
        layout={responsiveLayout}
        config={defaultConfig}
        style={{ width: "100%", height: "100%" }}
        useResizeHandler={true}
      />
    </div>
  );
}
