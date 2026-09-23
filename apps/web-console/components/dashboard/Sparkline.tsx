import { useId } from 'react';

/**
 * 迷你趋势线：内联 SVG polyline，无图表库。
 * data 为 0–100 归一化数据点；colorClass 为 text-* 类名（用 currentColor 描边）。
 */
export default function Sparkline({
  data,
  width = 90,
  height = 30,
  strokeWidth = 1.8,
  className = 'text-text-tertiary',
}: {
  data: number[];
  width?: number;
  height?: number;
  strokeWidth?: number;
  className?: string;
}) {
  const id = useId();
  if (!data.length) return null;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const span = max - min || 1;
  const pad = strokeWidth; // 防止描边被裁剪
  const stepX = data.length > 1 ? width / (data.length - 1) : width;
  const points = data
    .map((v, i) => {
      const x = i * stepX;
      const y = pad + (1 - (v - min) / span) * (height - pad * 2);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');

  return (
    <svg
      key={id}
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      fill="none"
      aria-hidden="true"
      className={className}
    >
      <polyline
        points={points}
        stroke="currentColor"
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
