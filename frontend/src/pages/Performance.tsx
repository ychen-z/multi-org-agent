import { useQuery } from "@tanstack/react-query";
import { Card, Loading } from "../components/cards/Cards";
import { PieChart, BarChart } from "../components/charts/Charts";
import { analysisApi } from "../services/api";

export default function Performance() {
  const { data, isLoading } = useQuery({
    queryKey: ["performance"],
    queryFn: () => analysisApi.performance(),
  });

  if (isLoading) return <Loading />;

  const distribution = data?.data?.distribution || [];

  const pieData = distribution.map((d: { _id: string; count: number }) => ({
    name: d._id || "未知",
    value: d.count,
  }));

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-800">绩效分析</h2>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="绩效等级分布">
          <PieChart data={pieData} height={300} />
        </Card>

        <Card title="绩效等级人数">
          <BarChart data={pieData} height={300} color="#10b981" />
        </Card>
      </div>

      <Card title="绩效分布明细">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left">等级</th>
                <th className="px-4 py-3 text-right">人数</th>
                <th className="px-4 py-3 text-right">占比</th>
                <th className="px-4 py-3 text-right">平均 OKR</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {distribution.map(
                (d: { _id: string; count: number; avg_okr_score?: number }) => (
                  <tr key={d._id}>
                    <td className="px-4 py-3 font-medium">{d._id || "未知"}</td>
                    <td className="px-4 py-3 text-right">{d.count}</td>
                    <td className="px-4 py-3 text-right">
                      {(
                        (d.count /
                          pieData.reduce(
                            (a: number, b: { value: number }) => a + b.value,
                            0,
                          )) *
                        100
                      ).toFixed(1)}
                      %
                    </td>
                    <td className="px-4 py-3 text-right">
                      {((d.avg_okr_score || 0) * 100).toFixed(0)}%
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
