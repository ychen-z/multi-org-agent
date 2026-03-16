import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Card, Loading } from "../components/cards/Cards";
import { reportsApi } from "../services/api";

export default function StrategicReport() {
  const [reportGenerated, setReportGenerated] = useState(false);

  const {
    data: reportData,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ["strategic-report"],
    queryFn: () => reportsApi.generate(),
    enabled: reportGenerated,
  });

  const generateMutation = useMutation({
    mutationFn: () => reportsApi.generate(),
    onSuccess: () => {
      setReportGenerated(true);
      refetch();
    },
  });

  const report = reportData?.data || {};
  const sections = report.sections || {};

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-800">CEO 战略报告</h2>
        <button
          onClick={() => generateMutation.mutate()}
          disabled={generateMutation.isPending}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {generateMutation.isPending ? "生成中..." : "🔄 生成报告"}
        </button>
      </div>

      {!reportGenerated && !isLoading && (
        <Card>
          <div className="text-center py-12">
            <span className="text-6xl">📋</span>
            <h3 className="text-xl font-semibold mt-4">生成战略报告</h3>
            <p className="text-gray-500 mt-2">
              点击上方按钮，AI 将自动分析数据并生成 CEO 一页纸战略报告
            </p>
          </div>
        </Card>
      )}

      {isLoading && <Loading text="正在生成报告..." />}

      {reportGenerated && report.title && (
        <>
          {/* 报告头部 */}
          <Card>
            <div className="text-center">
              <h3 className="text-xl font-bold">{report.title}</h3>
              <p className="text-gray-500 text-sm mt-1">{report.subtitle}</p>
              <p className="text-xs text-gray-400 mt-2">
                生成时间: {new Date(report.generated_at).toLocaleString()}
              </p>
            </div>
          </Card>

          {/* 执行摘要 */}
          <Card title="📊 执行摘要">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
              {report.executive_summary?.key_metrics &&
                Object.entries(report.executive_summary.key_metrics).map(
                  ([key, value]) => (
                    <div
                      key={key}
                      className="text-center p-3 bg-gray-50 rounded-lg"
                    >
                      <p className="text-2xl font-bold text-blue-600">
                        {String(value)}
                      </p>
                      <p className="text-xs text-gray-500">
                        {key.replace(/_/g, " ")}
                      </p>
                    </div>
                  ),
                )}
            </div>
            <div className="space-y-2">
              {report.executive_summary?.key_findings?.map(
                (finding: string, i: number) => (
                  <p key={i} className="text-sm text-gray-600">
                    • {finding}
                  </p>
                ),
              )}
            </div>
          </Card>

          {/* 招聘分析 */}
          {sections.recruitment && (
            <Card title="👥 招聘效能">
              <div className="space-y-2">
                {sections.recruitment.action_items?.map(
                  (item: string, i: number) => (
                    <div key={i} className="flex items-center gap-2 text-sm">
                      <span className="text-blue-500">→</span>
                      <span>{item}</span>
                    </div>
                  ),
                )}
              </div>
            </Card>
          )}

          {/* 建议 */}
          {report.recommendations && (
            <Card title="💡 策略建议">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="p-4 bg-red-50 rounded-lg">
                  <h4 className="font-semibold text-red-800">短期 (1-3月)</h4>
                  <ul className="mt-2 space-y-1">
                    {report.recommendations.short_term?.map(
                      (r: string, i: number) => (
                        <li key={i} className="text-sm text-red-600">
                          • {r}
                        </li>
                      ),
                    )}
                  </ul>
                </div>
                <div className="p-4 bg-yellow-50 rounded-lg">
                  <h4 className="font-semibold text-yellow-800">
                    中期 (3-6月)
                  </h4>
                  <ul className="mt-2 space-y-1">
                    {report.recommendations.medium_term?.map(
                      (r: string, i: number) => (
                        <li key={i} className="text-sm text-yellow-600">
                          • {r}
                        </li>
                      ),
                    )}
                  </ul>
                </div>
                <div className="p-4 bg-green-50 rounded-lg">
                  <h4 className="font-semibold text-green-800">
                    长期 (6-12月)
                  </h4>
                  <ul className="mt-2 space-y-1">
                    {report.recommendations.long_term?.map(
                      (r: string, i: number) => (
                        <li key={i} className="text-sm text-green-600">
                          • {r}
                        </li>
                      ),
                    )}
                  </ul>
                </div>
              </div>
            </Card>
          )}

          {/* 导出按钮 */}
          <div className="flex justify-center gap-4">
            <button className="px-6 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200">
              📄 导出 PDF
            </button>
            <button className="px-6 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200">
              📊 导出 Excel
            </button>
          </div>
        </>
      )}
    </div>
  );
}
