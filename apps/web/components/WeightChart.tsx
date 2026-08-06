"use client";
import { Bar, BarChart, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export interface WeightPoint { name: string; current: number; target: number }

export function WeightChart({ data }: { data: WeightPoint[] }) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data}>
        <XAxis dataKey="name" fontSize={12} />
        <YAxis tickFormatter={(v) => `${v}%`} fontSize={12} />
        <Tooltip formatter={(v) => `${Number(v).toFixed(1)}%`} />
        <Legend />
        <Bar dataKey="current" name="当前权重" fill="#2563eb" />
        <Bar dataKey="target" name="目标权重" fill="#93c5fd" />
      </BarChart>
    </ResponsiveContainer>
  );
}
