interface RadarChartProps {
  data: { label: string; value: number; color?: string }[];
  size?: number;
  maxValue?: number;
}

export default function RadarChart({ data, size = 200, maxValue = 1 }: RadarChartProps) {
  const center = size / 2;
  const radius = size / 2 - 30;
  const n = data.length;
  const angleStep = (2 * Math.PI) / n;

  const getPoint = (index: number, value: number) => {
    const angle = angleStep * index - Math.PI / 2;
    const r = (value / maxValue) * radius;
    return {
      x: center + r * Math.cos(angle),
      y: center + r * Math.sin(angle),
    };
  };

  // Background polygons
  const levels = [0.25, 0.5, 0.75, 1.0];
  const bgPolygons = levels.map(level => {
    const points = Array.from({ length: n }, (_, i) => {
      const p = getPoint(i, level * maxValue);
      return `${p.x},${p.y}`;
    }).join(' ');
    return <polygon key={level} points={points} fill="none" stroke="#eee" strokeWidth="1" />;
  });

  // Data polygon
  const dataPoints = data.map((d, i) => {
    const p = getPoint(i, d.value);
    return `${p.x},${p.y}`;
  }).join(' ');

  // Labels
  const labels = data.map((d, i) => {
    const p = getPoint(i, maxValue * 1.15);
    return (
      <text key={i} x={p.x} y={p.y} textAnchor="middle" fontSize="13" fontWeight="bold">
        {d.label} {d.value.toFixed(2)}
      </text>
    );
  });

  // Data points
  const dots = data.map((d, i) => {
    const p = getPoint(i, d.value);
    return <circle key={i} cx={p.x} cy={p.y} r="4" fill={d.color || '#1890ff'} />;
  });

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      {bgPolygons}
      <polygon points={dataPoints} fill="rgba(24,144,255,0.15)" stroke="#1890ff" strokeWidth="2" />
      {dots}
      {labels}
    </svg>
  );
}
