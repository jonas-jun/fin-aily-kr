"use client";

import { Suspense } from "react";
import { useParams, useSearchParams } from "next/navigation";
import Link from "next/link";
import { ReportSkeleton } from "@/components/report/ReportSkeleton";
import { TargetPriceCard } from "@/components/report/TargetPriceCard";
import { FullReportCard } from "@/components/report/FullReportCard";
import { SourceList } from "@/components/report/SourceList";
import { useAnalyze } from "@/hooks/useAnalyze";

function ReportContent() {
  const { ticker } = useParams<{ ticker: string }>();
  const searchParams = useSearchParams();
  const name = searchParams.get("name") ?? ticker;
  const n = Number(searchParams.get("n") ?? "5");

  const { data, loading, error } = useAnalyze(ticker, name, n);

  return (
    <div>
      <div className="mb-6">
        <Link href="/" className="text-sm text-slate-400 hover:text-slate-600 mb-3 inline-block">
          ← 뒤로
        </Link>
        <div className="flex items-center gap-2">
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900">{name}</h1>
          <span className="text-sm text-slate-400 font-mono">{ticker}</span>
        </div>
        {data && (
          <p className="text-xs text-slate-400 mt-1">
            리포트 {data.report_count}개 기반 · {new Date(data.analyzed_at).toLocaleDateString("ko-KR", { timeZone: "Asia/Seoul" })} 분석
          </p>
        )}
      </div>

      {loading && <ReportSkeleton />}

      {!loading && error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
          {error}
        </div>
      )}

      {!loading && !error && data && (
        <div className="space-y-4">
          <TargetPriceCard targetPrice={data.target_price} />
          <FullReportCard report={data.full_report} analyzedAt={data.analyzed_at} dartOnly={data.dart_only} />
          <SourceList sources={data.sources} />
        </div>
      )}
    </div>
  );
}

export default function ReportPage() {
  return (
    <Suspense fallback={<ReportSkeleton />}>
      <ReportContent />
    </Suspense>
  );
}
