import { useQuery } from "@tanstack/react-query";
import { MetricCard, Card, Loading } from "../components/cards/Cards";
import { PieChart, BarChart, GaugeChart } from "../components/charts/Charts";
import { dataApi, analysisApi } from "../services/api";

export default function Dashboard() {
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ["stats"],
    queryFn: () => dataApi.getStats(),
  });

  const { data: riskData } = useQuery({
    queryKey: ["talent-risk"],
    queryFn: () => analysisApi.talentRisk(),
  });

  const { data: recruitData } = useQuery({
    queryKey: ["recruitment"],
    queryFn: () => analysisApi.recruitment(),
  });

  const { data: orgHealthData } = useQuery({
    queryKey: ["org-health"],
    queryFn: () => analysisApi.orgHealth(),
  });

  if (statsLoading) return <Loading />;

  const statsData = stats?.data || {};
  const riskDist = riskData?.data?.risk_distribution || {};
  const channelStats = recruitData?.data?.channel_stats || [];
  const orgHealth = orgHealthData?.data || {};

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-800">组织总览</h2>
        <span className="text-sm text-gray-500">
          数据更新时间: {new Date().toLocaleString()}
        </span>
      </div>

      {/* 核心指标 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="员工总数"
          value={statsData.employees?.toLocaleString() || 0}
          icon="👥"
          color="blue"
        />
        <MetricCard
          title="部门数量"
          value={statsData.departments || 0}
          icon="🏢"
          color="green"
        />
        <MetricCard
          title="高风险员工"
          value={(riskDist.high || 0) + (riskDist.critical || 0)}
          icon="⚠️"
          color="red"
        />
        <MetricCard
          title="招聘记录"
          value={statsData.recruitment_records?.toLocaleString() || 0}
          icon="📋"
          color="yellow"
        />
      </div>

      {/* 图表区域 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="风险分布">
          <PieChart
            data={[
              { name: "低风险", value: riskDist.low || 0 },
              { name: "中风险", value: riskDist.medium || 0 },
              { name: "高风险", value: riskDist.high || 0 },
              { name: "极高风险", value: riskDist.critical || 0 },
            ]}
            height={280}
          />
        </Card>

        <Card title="招聘渠道分布">
          <BarChart
            data={channelStats
              .slice(0, 8)
              .map((c: { _id: string; total: number }) => ({
                name: c._id,
                value: c.total,
              }))}
            height={280}
          />
        </Card>
      </div>

      {/* 组织健康度 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card title="组织健康度">
          <GaugeChart
            value={orgHealth.health_score || 0}
            title="综合评分"
            height={200}
          />
        </Card>
        <Card title="人员稳定性">
          <GaugeChart
            value={orgHealth.stability_score || 0}
            title="稳定性评分"
            height={200}
          />
        </Card>
        <Card title="编制利用率">
          <GaugeChart
            value={Math.min(orgHealth.utilization_rate || 0, 100)}
            title="利用率"
            height={200}
          />
        </Card>
      </div>

      {/* 快速操作 */}
      <Card title="快速操作">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <button
            onClick={() => dataApi.generateData(10000)}
            className="p-4 bg-blue-50 rounded-lg text-blue-700 hover:bg-blue-100 transition text-sm font-medium"
          >
            🔄 生成测试数据
          </button>
          <a
            href="/recruitment"
            className="p-4 bg-green-50 rounded-lg text-green-700 hover:bg-green-100 transition text-sm font-medium text-center"
          >
            📊 招聘分析
          </a>
          <a
            href="/talent-risk"
            className="p-4 bg-orange-50 rounded-lg text-orange-700 hover:bg-orange-100 transition text-sm font-medium text-center"
          >
            ⚠️ 风险预警
          </a>
          <a
            href="/report"
            className="p-4 bg-purple-50 rounded-lg text-purple-700 hover:bg-purple-100 transition text-sm font-medium text-center"
          >
            📋 生成报告
          </a>
        </div>
      </Card>
    </div>
  );
}
