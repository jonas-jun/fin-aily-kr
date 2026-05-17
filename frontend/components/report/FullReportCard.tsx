import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface Props {
  report: string | null;
  analyzedAt?: string;
}

export function FullReportCard({ report, analyzedAt }: Props) {
  if (!report) return null;

  const dateLabel = analyzedAt
    ? new Date(analyzedAt).toLocaleDateString("ko-KR", { timeZone: "Asia/Seoul" })
    : new Date().toLocaleDateString("ko-KR", { timeZone: "Asia/Seoul" });

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6">
      <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-100">
        <span className="text-xs text-slate-400">작성자: <span className="font-semibold text-slate-600">fin-aily</span></span>
        <span className="text-xs text-slate-400">작성일자: <span className="font-semibold text-slate-600">{dateLabel}</span></span>
      </div>
      <div className="prose prose-slate prose-sm max-w-none
        prose-headings:font-bold prose-headings:text-slate-800
        prose-h1:text-lg prose-h2:text-base prose-h3:text-sm
        prose-table:text-sm prose-td:py-1.5 prose-th:py-1.5
        prose-strong:text-slate-800
        prose-p:text-slate-700 prose-p:leading-relaxed
        prose-li:text-slate-700">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{report}</ReactMarkdown>
      </div>
    </div>
  );
}
