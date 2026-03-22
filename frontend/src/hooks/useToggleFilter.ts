import { useState, useMemo, useCallback } from "react";

/**
 * Hook for toggle-based filters. Manages boolean state, toggle handler,
 * and conversion to API parameter values.
 *
 * When no filters are active, activeValues returns ALL values (no filtering).
 */
export function useToggleFilter<
  TState extends Record<string, boolean>,
  TMap extends Record<keyof TState & string, unknown>,
>(
  initial: TState,
  valueMap: TMap,
): [TState, (key: string) => void, TMap[keyof TMap][]] {
  const [state, setState] = useState<TState>(initial);

  const toggle = useCallback((key: string) => {
    setState((prev) => ({
      ...prev,
      [key]: !prev[key as keyof TState],
    }));
  }, []);

  const activeValues = useMemo(() => {
    const active = Object.entries(state)
      .filter(([, v]) => v)
      .map(([k]) => valueMap[k as keyof TState & string]);
    return (
      active.length > 0 ? active : Object.values(valueMap)
    ) as TMap[keyof TMap][];
  }, [state, valueMap]);

  return [state, toggle, activeValues];
}
