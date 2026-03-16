import clsx from "clsx";

interface MetricCardProps {
  title: string;
  value: string | number;
  change?: number;
  icon?: string;
  color?: "blue" | "green" | "yellow" | "red";
}

export function MetricCard({
  title,
  value,
  change,
  icon,
  color = "blue",
}: MetricCardProps) {
  const colorClasses = {
    blue: "bg-blue-50 text-blue-600",
    green: "bg-green-50 text-green-600",
    yellow: "bg-yellow-50 text-yellow-600",
    red: "bg-red-50 text-red-600",
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-500">{title}</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
          {change !== undefined && (
            <p
              className={clsx(
                "text-sm mt-1",
                change >= 0 ? "text-green-600" : "text-red-600",
              )}
            >
              {change >= 0 ? "↑" : "↓"} {Math.abs(change)}%
            </p>
          )}
        </div>
        {icon && (
          <div
            className={clsx(
              "w-12 h-12 rounded-lg flex items-center justify-center text-2xl",
              colorClasses[color],
            )}
          >
            {icon}
          </div>
        )}
      </div>
    </div>
  );
}

interface RiskBadgeProps {
  level: "critical" | "high" | "medium" | "low";
}

export function RiskBadge({ level }: RiskBadgeProps) {
  const labels = { critical: "极高", high: "高", medium: "中", low: "低" };
  return <span className={`risk-badge ${level}`}>{labels[level]}</span>;
}

interface CardProps {
  title?: string;
  children: React.ReactNode;
  className?: string;
  action?: React.ReactNode;
}

export function Card({ title, children, className, action }: CardProps) {
  return (
    <div
      className={clsx(
        "bg-white rounded-xl shadow-sm border border-gray-100 p-6",
        className,
      )}
    >
      {(title || action) && (
        <div className="flex items-center justify-between mb-4">
          {title && (
            <h3 className="text-lg font-semibold text-gray-800">{title}</h3>
          )}
          {action}
        </div>
      )}
      {children}
    </div>
  );
}

interface LoadingProps {
  text?: string;
}

export function Loading({ text = "加载中..." }: LoadingProps) {
  return (
    <div className="flex items-center justify-center py-12">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      <span className="ml-3 text-gray-500">{text}</span>
    </div>
  );
}
