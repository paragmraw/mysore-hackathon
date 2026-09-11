export function RouteTrack({ pct }: { pct: number }) {
  const x = 7 + 242 * (pct / 100);

  return (
    <svg
      viewBox="0 0 256 24"
      aria-hidden="true"
      className="h-6 w-full max-w-64"
    >
      <line
        x1="7"
        y1="12"
        x2="249"
        y2="12"
        stroke="var(--color-kerb)"
        strokeWidth="2"
        strokeDasharray="8 6"
      />
      <line
        x1="7"
        y1="12"
        x2={x}
        y2="12"
        stroke="var(--color-asphalt)"
        strokeWidth="2"
      />
      <g
        style={{ transition: "transform 140ms linear", transform: `translateX(${x - 7}px)` }}
      >
        <circle
          cx="7"
          cy="12"
          r="7"
          fill="var(--color-arishina)"
          stroke="var(--color-asphalt)"
          strokeWidth="2"
        />
      </g>
    </svg>
  );
}