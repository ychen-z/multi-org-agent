import { Card } from "../components/cards/Cards";
import { GaugeChart } from "../components/charts/Charts";

export default function OrgHealth() {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-800">组织健康度</h2>

      {/* 健康度评分 */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <Card title="综合健康度">
          <GaugeChart value={78} title="综合评分" />
        </Card>
        <Card title="人员稳定性">
          <GaugeChart value={85} title="稳定性" />
        </Card>
        <Card title="编制利用率">
          <GaugeChart value={92} title="利用率" />
        </Card>
        <Card title="组织效能">
          <GaugeChart value={75} title="效能" />
        </Card>
      </div>

      {/* 指标明细 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="人口结构">
          <div className="space-y-4">
            <div className="flex justify-between items-center py-2 border-b">
              <span className="text-gray-600">平均年龄</span>
              <span className="font-semibold">32 岁</span>
            </div>
            <div className="flex justify-between items-center py-2 border-b">
              <span className="text-gray-600">平均司龄</span>
              <span className="font-semibold">3.5 年</span>
            </div>
            <div className="flex justify-between items-center py-2 border-b">
              <span className="text-gray-600">男女比例</span>
              <span className="font-semibold">6:4</span>
            </div>
            <div className="flex justify-between items-center py-2">
              <span className="text-gray-600">本科及以上</span>
              <span className="font-semibold">85%</span>
            </div>
          </div>
        </Card>

        <Card title="组织结构">
          <div className="space-y-4">
            <div className="flex justify-between items-center py-2 border-b">
              <span className="text-gray-600">组织层级</span>
              <span className="font-semibold">5 层</span>
            </div>
            <div className="flex justify-between items-center py-2 border-b">
              <span className="text-gray-600">平均管理幅度</span>
              <span className="font-semibold">7.2 人</span>
            </div>
            <div className="flex justify-between items-center py-2 border-b">
              <span className="text-gray-600">管理者占比</span>
              <span className="font-semibold">12%</span>
            </div>
            <div className="flex justify-between items-center py-2">
              <span className="text-gray-600">离职率</span>
              <span className="font-semibold text-green-600">8%</span>
            </div>
          </div>
        </Card>
      </div>

      <Card title="优化建议">
        <div className="space-y-3">
          <div className="flex items-start gap-3 p-3 bg-green-50 rounded-lg">
            <span className="text-green-600">✓</span>
            <div>
              <p className="font-medium text-green-800">人员稳定性良好</p>
              <p className="text-sm text-green-600">
                离职率低于行业平均，继续保持
              </p>
            </div>
          </div>
          <div className="flex items-start gap-3 p-3 bg-yellow-50 rounded-lg">
            <span className="text-yellow-600">!</span>
            <div>
              <p className="font-medium text-yellow-800">关注新员工占比</p>
              <p className="text-sm text-yellow-600">
                1年内新员工占比较高，建议加强培训和融入
              </p>
            </div>
          </div>
          <div className="flex items-start gap-3 p-3 bg-blue-50 rounded-lg">
            <span className="text-blue-600">→</span>
            <div>
              <p className="font-medium text-blue-800">持续优化组织结构</p>
              <p className="text-sm text-blue-600">
                管理幅度在健康范围内，可适当扁平化
              </p>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}
