import { useQuery } from "@tanstack/react-query";
import { Card, Loading } from "../components/cards/Cards";
import { BarChart, FunnelChart, PieChart } from "../components/charts/Charts";
import { analysisApi } from "../services/api";

export default function Recruitment() {
  const { data, isLoading } = useQuery({
    queryKey: ["recruitment-analysis"],
    queryFn: () => analysisApi.recruitment(),
  });

  if (isLoading) return <Loading />;

  const channelStats = data?.data?.channel_stats || [];
  const summary = data?.data?.summary || {};

  // 使用后端返回的真实漏斗数据
  const funnelData = data?.data?.funnel_data || [
    { name: "简历", value: summary.total_records || 0 },
    { name: "筛选", value: 0 },
    { name: "面试", value: 0 },
    { name: "Offer", value: 0 },
    { name: "入职", value: summary.total_hired || 0 },
  ];

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-800">招聘效能分析</h2>

      {/* 核心指标 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl p-5 border">
          <p className="text-sm text-gray-500">总渠道数</p>
          <p className="text-2xl font-bold">
            {summary.total_channels || channelStats.length}
          </p>
        </div>
        <div className="bg-white rounded-xl p-5 border">
          <p className="text-sm text-gray-500">总简历数</p>
          <p className="text-2xl font-bold">
            {summary.total_records?.toLocaleString() || 0}
          </p>
        </div>
        <div className="bg-white rounded-xl p-5 border">
          <p className="text-sm text-gray-500">入职人数</p>
          <p className="text-2xl font-bold text-green-600">
            {summary.total_hired || 0}
          </p>
        </div>
        <div className="bg-white rounded-xl p-5 border">
          <p className="text-sm text-gray-500">整体转化率</p>
          <p className="text-2xl font-bold">
            {summary.total_records
              ? ((summary.total_hired / summary.total_records) * 100).toFixed(1)
              : 0}
            %
          </p>
        </div>
      </div>

      {/* 图表 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="渠道简历数量">
          <BarChart
            data={channelStats.map((c: { _id: string; total: number }) => ({
              name: c._id,
              value: c.total,
            }))}
            height={300}
          />
        </Card>

        <Card title="招聘漏斗">
          <FunnelChart data={funnelData} height={300} />
        </Card>
      </div>

      {/* 渠道明细表 */}
      <Card title="渠道 ROI 明细">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left">渠道</th>
                <th className="px-4 py-3 text-right">简历数</th>
                <th className="px-4 py-3 text-right">入职数</th>
                <th className="px-4 py-3 text-right">转化率</th>
                <th className="px-4 py-3 text-center">效率</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {channelStats.map(
                (ch: { _id: string; total: number; hired: number }) => (
                  <tr key={ch._id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium">{ch._id}</td>
                    <td className="px-4 py-3 text-right">{ch.total}</td>
                    <td className="px-4 py-3 text-right">{ch.hired}</td>
                    <td className="px-4 py-3 text-right">
                      {ch.total ? ((ch.hired / ch.total) * 100).toFixed(1) : 0}%
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span
                        className={`px-2 py-1 rounded text-xs ${
                          ch.hired / ch.total > 0.05
                            ? "bg-green-100 text-green-700"
                            : "bg-yellow-100 text-yellow-700"
                        }`}
                      >
                        {ch.hired / ch.total > 0.05 ? "高效" : "待优化"}
                      </span>
                    </td>
                  </tr>
                ),
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
