import type { QuarterlyFinancialItem } from "@/lib/api";

interface Props {
  financials: QuarterlyFinancialItem[];
}

function formatAmount(value: number | null): string {
  if (value == null) return "—";
  const eok = Math.round(value / 100_000_000);
  return `${eok.toLocaleString("ko-KR")}억`;
}

export function QuarterlyFinancialsTable({ financials }: Props) {
  if (!financials || financials.length === 0) return null;

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">
        분기별 주요 재무
      </h2>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100">
              <th className="py-2 pr-4 text-left text-xs text-slate-400 font-medium whitespace-nowrap">분기</th>
              <th className="py-2 px-4 text-right text-xs text-slate-400 font-medium whitespace-nowrap">매출액</th>
              <th className="py-2 px-4 text-right text-xs text-slate-400 font-medium whitespace-nowrap">영업이익</th>
              <th className="py-2 pl-4 text-right text-xs text-slate-400 font-medium whitespace-nowrap">당기순이익</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {financials.map((row, i) => (
              <tr key={i} className="hover:bg-slate-50 transition-colors">
                <td className="py-2.5 pr-4 text-xs font-semibold text-slate-600 whitespace-nowrap">{row.quarter}</td>
                <td className="py-2.5 px-4 text-right text-sm text-slate-700 tabular-nums">{formatAmount(row.revenue)}</td>
                <td className="py-2.5 px-4 text-right text-sm text-slate-700 tabular-nums">{formatAmount(row.operating_profit)}</td>
                <td className="py-2.5 pl-4 text-right text-sm text-slate-700 tabular-nums">{formatAmount(row.net_income)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
