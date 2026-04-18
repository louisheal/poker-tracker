import { useState, useEffect, useRef } from "react";
import type { SolverResult, SolverParams } from "@/models";

interface StreamState {
  result: SolverResult | null;
  loading: boolean;
  progress: number;
  simsComplete: number;
}

const INITIAL_STATE: StreamState = {
  result: null,
  loading: false,
  progress: 0,
  simsComplete: 0,
};

export function useSolverStream(params: SolverParams | null): StreamState {
  const [state, setState] = useState<StreamState>(INITIAL_STATE);
  const sourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!params) {
      setState(INITIAL_STATE);
      return;
    }

    const sp = new URLSearchParams();
    for (const c of params.board) sp.append("board", c);
    sp.append("street", params.street);
    for (const a of params.actions) sp.append("actions", a);
    if (params.heroPosition) sp.append("hero_position", params.heroPosition);

    // Preflop: use regular fetch (no tree enumeration needed)
    if (params.street === "preflop") {
      const controller = new AbortController();
      setState((prev) => ({ ...prev, loading: true }));

      fetch(`http://localhost:8000/solver/solve?${sp}`, {
        signal: controller.signal,
      })
        .then((r) => r.json())
        .then((data) => {
          setState({ result: data, loading: false, progress: 1, simsComplete: 0 });
        })
        .catch(() => {
          setState((prev) => ({ ...prev, loading: false }));
        });

      return () => controller.abort();
    }

    // Postflop: use SSE streaming
    const source = new EventSource(
      `http://localhost:8000/solver/solve-stream?${sp}`,
    );
    sourceRef.current = source;
    setState((prev) => ({ ...prev, loading: true, progress: 0, simsComplete: 0 }));

    source.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === "update") {
        setState({
          result: data,
          loading: true,
          progress: data.progress ?? 0,
          simsComplete: data.simsComplete ?? 0,
        });
      } else if (data.type === "complete") {
        setState({
          result: data,
          loading: false,
          progress: 1,
          simsComplete: data.simsComplete ?? 0,
        });
        source.close();
      }
    };

    source.onerror = () => {
      setState((prev) => ({ ...prev, loading: false }));
      source.close();
    };

    return () => {
      source.close();
      sourceRef.current = null;
    };
  }, [
    params?.board.join(","),
    params?.street,
    params?.actions.join(","),
    params?.heroPosition,
  ]);

  return state;
}
