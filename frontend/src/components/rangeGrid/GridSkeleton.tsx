export const GridSkeleton = ({
  rows = 13,
  cols = 13,
}: {
  rows?: number;
  cols?: number;
}) => {
  const cells: number[] = Array.from({ length: rows * cols }).map((_, i) => i);

  return (
    <div
      className="grid gap-2 w-full"
      style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }}
    >
      {cells.map((c) => (
        <div
          key={c}
          className="box-border aspect-square flex items-center justify-center rounded-sm bg-gray-800 animate-pulse"
        />
      ))}
    </div>
  );
};

export default GridSkeleton;
