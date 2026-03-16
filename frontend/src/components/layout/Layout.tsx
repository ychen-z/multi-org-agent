import { ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";
import clsx from "clsx";

const navItems = [
  { path: "/", label: "总览", icon: "📊" },
  { path: "/recruitment", label: "招聘分析", icon: "👥" },
  { path: "/performance", label: "绩效分析", icon: "📈" },
  { path: "/talent-risk", label: "人才风险", icon: "⚠️" },
  { path: "/org-health", label: "组织健康", icon: "🏢" },
  { path: "/report", label: "战略报告", icon: "📋" },
];

interface LayoutProps {
  children: ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  const location = useLocation();

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
        <div className="px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl">🤖</span>
            <h1 className="text-xl font-bold text-gray-800">
              Multi-Agent 组织智能分析系统
            </h1>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-500">v1.0.0</span>
          </div>
        </div>
      </header>

      <div className="flex">
        {/* Sidebar */}
        <aside className="w-56 bg-white border-r border-gray-200 min-h-[calc(100vh-73px)] sticky top-[73px]">
          <nav className="p-4 space-y-1">
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={clsx(
                  "flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors",
                  location.pathname === item.path
                    ? "bg-blue-50 text-blue-700"
                    : "text-gray-600 hover:bg-gray-50 hover:text-gray-900",
                )}
              >
                <span>{item.icon}</span>
                <span>{item.label}</span>
              </Link>
            ))}
          </nav>
        </aside>

        {/* Main Content */}
        <main className="flex-1 p-6">{children}</main>
      </div>
    </div>
  );
}
