import { useQuery } from "@tanstack/react-query";
import { Card, Loading } from "../components/cards/Cards";
import { GaugeChart, BarChart } from "../components/charts/Charts";
import { analysisApi } from "../services/api";

export default function OrgHealth() {
  const { data, isLoading } = useQuery({
    queryKey: ["org-health-full"],
    queryFn: () => analysisApi.orgHealth(),
  });

  if (isLoading) return <Loading />;

  const orgData = data?.data || {};
  const deptStats = orgData.department_stats || [];

  // 部门利用率图表数据
  const deptUtilData = deptStats
    .filter((d: { name: string; utilization: number }) => d.utilization > 0)
    .map((d: { name: string; utilization: number }) => ({
      name: d.name,
      value: Math.round(d.utilization * 100),
    }))
    .slice(0, 10);

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-800">组织健康分析</h2>

      {/* 健康度仪表盘 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card title="综合健康度">
          <GaugeChart value={orgData.health_score || 0} title="综合评分" />
        </Card>
        <Card title="人员稳定性">
          <GaugeChart value={orgData.stability_score || 0} title="稳定性" />
        </Card>
        <Card title="编制利用率">
          <GaugeChart
            value={Math.min(orgData.utilization_rate || 0, 100)}
            title="利用率"
          />
        </Card>
        <Card title="绩效水平">
          <GaugeChart value={orgData.performance_score || 0} title="效能" />
        </Card>
      </div>

      {/* 详细指标 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-xl p-5 border">
          <p className="text-sm text-gray-500">在职员工</p>
          <p className="text-2xl font-bold">
            {orgData.total_employees?.toLocaleString() || 0}
          </p>
        </div>
        <div className="bg-white rounded-xl p-5 border">
          <p className="text-sm text-gray-500">编制预算 / 实际</p>
          <p className="text-2xl font-bold">
            {orgData.headcount?.budget || 0} / {orgData.headcount?.actual || 0}
          </p>
        </div>
        <div className="bg-white rounded-xl p-5 border">
          <p className="text-sm text-gray-500">平均管理幅度</p>
          <p className="text-2xl font-bold">
            {orgData.avg_management_span || 0}
          </p>
        </div>
      </div>

      {/* 部门利用率 */}
      <Card title="部门编制利用率">
        {deptUtilData.length > 0 ? (
          <BarChart data={deptUtilData} height={300} color="#10b981" />
        ) : (
          <p className="text-gray-500 text-center py-8">暂无部门数据</p>
        )}
      </Card>

      {/* 健康度说明 */}
      <Card title="评分说明">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div className="p-4 bg-blue-50 rounded-lg">
            <h4 className="font-medium text-blue-800">综合健康度</h4>
            <p className="text-blue-600 mt-1">
              = 30% 利用率 + 30% 稳定性 + 20% 绩效 + 20% 结构
            </p>
          </div>
          <div className="p-4 bg-green-50 rounded-lg">
            <h4 className="font-medium text-green-800">稳定性评分</h4>
            <p className="text-green-600 mt-1">= 100 - 高风险员工占比</p>
          </div>
          <div className="p-4 bg-yellow-50 rounded-lg">
            <h4 className="font-medium text-yellow-800">编制利用率</h4>
            <p className="text-yellow-600 mt-1">= 实际人数 / 预算人数 × 100%</p>
          </div>
          <div className="p-4 bg-purple-50 rounded-lg">
            <h4 className="font-medium text-purple-800">绩效评分</h4>
            <p className="text-purple-600 mt-1">基于 A/B/C/D 等级加权计算</p>
          </div>
        </div>
      </Card>
    </div>
  );
}
