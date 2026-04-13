import type React from 'react';
import { useMemo } from 'react';

interface SparklineProps {
  data: number[];
  width?: number;
  height?: number;
  className?: string;
}

/**
 * Minimal SVG sparkline chart.
 * Color is determined by trend: last > first = cyan (up), last < first = danger (down), equal = muted.
 */
export const Sparkline: React.FC<SparklineProps> = ({
  data,
  width = 120,
  height = 40,
  className,
}) => {
  const pathData = useMemo(() => {
    if (data.length < 2) return null;

    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;
    const padding = 2;
    const usableHeight = height - padding * 2;
    const stepX = (width - padding * 2) / (data.length - 1);

    const points = data.map((value, index) => {
      const x = padding + index * stepX;
      const y = padding + usableHeight - ((value - min) / range) * usableHeight;
      return `${x},${y}`;
    });

    return points.join(' ');
  }, [data, width, height]);

  if (!pathData) return null;

  const first = data[0];
  const last = data[data.length - 1];
  const strokeColor =
    last > first
      ? 'hsl(var(--primary))'
      : last < first
        ? 'hsl(var(--color-danger))'
        : 'hsl(var(--muted-foreground))';

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className={className}
      aria-hidden="true"
    >
      <polyline
        points={pathData}
        fill="none"
        stroke={strokeColor}
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
};
