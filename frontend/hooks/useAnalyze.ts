"use client";

import { useEffect, useState } from "react";
import { api, type AnalyzeResponse } from "@/lib/api";

export function useAnalyze(ticker: string, name: string, count: number) {
  const [data, setData] = useState<AnalyzeResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ticker) return;
    let cancelled = false;

    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await api.analyze(ticker, name, count);
        if (!cancelled) setData(response);
      } catch (caught: unknown) {
        if (!cancelled) {
          setError(
            caught instanceof Error ? caught.message : "알 수 없는 오류가 발생했습니다.",
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    load();
    return () => {
      cancelled = true;
    };
  }, [ticker, name, count]);

  return { data, loading, error };
}
