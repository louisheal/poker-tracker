export const RangeLegend = () => {
  return (
    <div className="flex gap-3 items-center text-xs">
      <div className="flex items-center gap-1">
        <span className="w-4 h-3 bg-red-500 inline-block rounded-sm" />
        <span>Raise</span>
      </div>
      <div className="flex items-center gap-1">
        <span className="w-4 h-3 bg-green-500 inline-block rounded-sm" />
        <span>Call</span>
      </div>
      <div className="flex items-center gap-1">
        <span className="w-4 h-3 bg-blue-400 inline-block rounded-sm" />
        <span>Fold</span>
      </div>
    </div>
  );
};

export default RangeLegend;
