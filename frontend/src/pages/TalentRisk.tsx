import { useQuery } from "@tanstack/react-query";
import { Card, Loading, RiskBadge } from "../components/cards/Cards";
import { PieChart } from "../components/charts/Charts";
import { analysisApi } from "../services/api";

export default function TalentRisk() {
  const { data, isLoading } = useQuery({
    queryKey: ["talent-risk-full"],
    queryFn: () => analysisApi.talentRisk(),
  });

  if (isLoading) return <Loading />;

  const riskDist = data?.data?.risk_distribution || {};
  const highRiskCount = (riskDist.high || 0) + (riskDist.critical || 0);

  const pieData = [
    { name: "低风险", value: riskDist.low || 0 },
    { name: "中风险", value: riskDist.medium || 0 },
    { name: "高风险", value: riskDist.high || 0 },
    { name: "极高风险", value: riskDist.critical || 0 },
  ];

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-800">人才风险预警</h2>

      {/* 预警卡片 */}
      {highRiskCount > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4">
          <div className="flex items-center gap-3">
            <span className="text-2xl">⚠️</span>
            <div>
              <p className="font-semibold text-red-800">风险预警</p>
              <p className="text-sm text-red-600">
                当前有 {highRiskCount} 名员工存在高离职风险，建议立即关注
              </p>
            </div>
          </div>
        </div>
      )}

      {/* 核心指标 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl p-5 border">
          <p className="text-sm text-gray-500">极高风险</p>
          <p className="text-2xl font-bold text-red-600">
            {riskDist.critical || 0}
          </p>
        </div>
        <div className="bg-white rounded-xl p-5 border">
          <p className="text-sm text-gray-500">高风险</p>
          <p className="text-2xl font-bold text-orange-600">
            {riskDist.high || 0}
          </p>
        </div>
        <div className="bg-white rounded-xl p-5 border">
          <p className="text-sm text-gray-500">中风险</p>
          <p className="text-2xl font-bold text-yellow-600">
            {riskDist.medium || 0}
          </p>
        </div>
        <div className="bg-white rounded-xl p-5 border">
          <p className="text-sm text-gray-500">低风险</p>
          <p className="text-2xl font-bold text-green-600">
            {riskDist.low || 0}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="风险等级分布">
          <PieChart data={pieData} height={300} />
        </Card>

        <Card title="需关注员工">
          <div className="space-y-3">
            {highRiskCount === 0 ? (
              <p className="text-gray-500 text-center py-8">暂无高风险员工</p>
            ) : (
              <div className="text-sm text-gray-600">
                <p>共 {highRiskCount} 名高风险员工需要关注</p>
                <ul className="mt-4 space-y-2">
                  <li className="flex items-center gap-2">
                    <RiskBadge level="critical" />
                    <span>极高风险员工建议立即约谈</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <RiskBadge level="high" />
                    <span>高风险员工建议一周内沟通</span>
                  </li>
                </ul>
              </div>
            )}
          </div>
        </Card>
      </div>

      <Card title="建议行动">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-4 bg-red-50 rounded-lg">
            <h4 className="font-medium text-red-800">紧急行动</h4>
            <p className="text-sm text-red-600 mt-1">
              约谈极高风险员工，了解诉求
            </p>
          </div>
          <div className="p-4 bg-orange-50 rounded-lg">
            <h4 className="font-medium text-orange-800">重点关注</h4>
            <p className="text-sm text-orange-600 mt-1">
              分析高风险员工的共性问题
            </p>
          </div>
          <div className="p-4 bg-blue-50 rounded-lg">
            <h4 className="font-medium text-blue-800">预防措施</h4>
            <p className="text-sm text-blue-600 mt-1">优化薪酬福利和发展通道</p>
          </div>
          <div className="p-4 bg-green-50 rounded-lg">
            <h4 className="font-medium text-green-800">长期建设</h4>
            <p className="text-sm text-green-600 mt-1">
              完善员工关怀和企业文化
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
}
