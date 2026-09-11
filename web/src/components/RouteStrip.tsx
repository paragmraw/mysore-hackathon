export function RouteStrip({
  current,
  total,
}: {
  current: number;
  total: number;
}) {
  const traveled =
    total > 1 ? ((current - 1) / (total - 1)) * 100 : 0;

  return (
    <div className="relative" aria-hidden="true">
      <div className="absolute top-1/2 right-0 left-0 h-0.5 -translate-y-1/2 bg-kerb" />
      <div
        className="absolute top-1/2 left-0 h-0.5 -translate-y-1/2 bg-asphalt transition-[width] duration-200"
        style={{ width: `${traveled}%` }}
      />
      <div className="flex items-center justify-between">
        {Array.from({ length: total }).map((_, i) => (
          <span
            key={i}
            className={
              i < current - 1
                ? "size-3 rounded-full bg-asphalt"
                : i === current - 1
                  ? "size-3.5 rounded-full bg-arishina ring-2 ring-asphalt"
                  : "size-3 rounded-full border-2 border-kerb-deep bg-board"
            }
          />
        ))}
      </div>
    </div>
  );
}