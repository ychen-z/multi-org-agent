import ReactECharts from "echarts-for-react";
import type { EChartsOption } from "echarts";

interface BaseChartProps {
  option: EChartsOption;
  height?: string | number;
  loading?: boolean;
  className?: string;
}

export default function BaseChart({
  option,
  height = 300,
  loading = false,
  className = "",
}: BaseChartProps) {
  return (
    <ReactECharts
      option={option}
      style={{ height }}
      className={className}
      showLoading={loading}
      opts={{ renderer: "svg" }}
    />
  );
}

// 柱状图
interface BarChartProps {
  data: { name: string; value: number }[];
  title?: string;
  height?: number;
  color?: string;
}

export function BarChart({
  data,
  title,
  height = 300,
  color = "#3b82f6",
}: BarChartProps) {
  const option: EChartsOption = {
    title: title
      ? { text: title, left: "center", textStyle: { fontSize: 14 } }
      : undefined,
    tooltip: { trigger: "axis" },
    xAxis: {
      type: "category",
      data: data.map((d) => d.name),
      axisLabel: { rotate: 30 },
    },
    yAxis: { type: "value" },
    series: [
      {
        type: "bar",
        data: data.map((d) => d.value),
        itemStyle: { color, borderRadius: [4, 4, 0, 0] },
      },
    ],
    grid: { left: "3%", right: "4%", bottom: "15%", containLabel: true },
  };
  return <BaseChart option={option} height={height} />;
}

// 饼图
interface PieChartProps {
  data: { name: string; value: number }[];
  title?: string;
  height?: number;
}

export function PieChart({ data, title, height = 300 }: PieChartProps) {
  const option: EChartsOption = {
    title: title
      ? { text: title, left: "center", textStyle: { fontSize: 14 } }
      : undefined,
    tooltip: { trigger: "item", formatter: "{b}: {c} ({d}%)" },
    legend: { bottom: 0, left: "center" },
    series: [
      {
        type: "pie",
        radius: ["40%", "70%"],
        center: ["50%", "45%"],
        data,
        label: { show: false },
        emphasis: { label: { show: true, fontWeight: "bold" } },
      },
    ],
  };
  return <BaseChart option={option} height={height} />;
}

// 折线图
interface LineChartProps {
  data: { name: string; value: number }[];
  title?: string;
  height?: number;
  color?: string;
}

export function LineChart({
  data,
  title,
  height = 300,
  color = "#3b82f6",
}: LineChartProps) {
  const option: EChartsOption = {
    title: title
      ? { text: title, left: "center", textStyle: { fontSize: 14 } }
      : undefined,
    tooltip: { trigger: "axis" },
    xAxis: { type: "category", data: data.map((d) => d.name) },
    yAxis: { type: "value" },
    series: [
      {
        type: "line",
        data: data.map((d) => d.value),
        smooth: true,
        lineStyle: { color },
        areaStyle: { color: `${color}20` },
      },
    ],
    grid: { left: "3%", right: "4%", bottom: "3%", containLabel: true },
  };
  return <BaseChart option={option} height={height} />;
}

// 漏斗图
interface FunnelChartProps {
  data: { name: string; value: number }[];
  title?: string;
  height?: number;
}

export function FunnelChart({ data, title, height = 300 }: FunnelChartProps) {
  const option: EChartsOption = {
    title: title
      ? { text: title, left: "center", textStyle: { fontSize: 14 } }
      : undefined,
    tooltip: { trigger: "item", formatter: "{b}: {c}" },
    series: [
      {
        type: "funnel",
        left: "10%",
        width: "80%",
        label: { formatter: "{b}: {c}" },
        data: data.sort((a, b) => b.value - a.value),
      },
    ],
  };
  return <BaseChart option={option} height={height} />;
}

// 仪表盘
interface GaugeChartProps {
  value: number;
  title?: string;
  height?: number;
  max?: number;
}

export function GaugeChart({
  value,
  title,
  height = 250,
  max = 100,
}: GaugeChartProps) {
  const option: EChartsOption = {
    series: [
      {
        type: "gauge",
        startAngle: 180,
        endAngle: 0,
        min: 0,
        max,
        progress: { show: true, width: 18 },
        pointer: { show: false },
        axisLine: { lineStyle: { width: 18 } },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { show: false },
        title: { show: true, offsetCenter: [0, "20%"], fontSize: 14 },
        detail: {
          valueAnimation: true,
          offsetCenter: [0, "-10%"],
          fontSize: 32,
          fontWeight: "bold",
          formatter: "{value}",
          color: value >= 80 ? "#10b981" : value >= 60 ? "#f59e0b" : "#ef4444",
        },
        data: [{ value, name: title || "" }],
      },
    ],
  };
  return <BaseChart option={option} height={height} />;
}
