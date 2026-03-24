'use client';

import { Card, CardContent } from '@/components/ui/card';
import type { LucideIcon } from 'lucide-react';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  trend?: number;
  color?: string;
}

export function MetricCard({ title, value, subtitle, icon: Icon, trend, color = 'text-indigo-400' }: MetricCardProps) {
  return (
    <Card className="bg-zinc-900/80 border-zinc-800 hover:border-zinc-700 transition-all">
      <CardContent className="p-4">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <p className="text-[11px] font-medium text-zinc-500 uppercase tracking-wider">{title}</p>
            <p className="text-2xl font-bold text-zinc-100 mt-1">{value}</p>
            <div className="flex items-center gap-2 mt-1.5">
              {subtitle && <span className="text-[11px] text-zinc-500">{subtitle}</span>}
              {trend !== undefined && trend !== 0 && (
                <span className={`text-[11px] font-medium ${trend > 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {trend > 0 ? '+' : ''}{trend}%
                </span>
              )}
            </div>
          </div>
          <div className={`p-2 rounded-lg bg-zinc-800/80 ${color}`}>
            <Icon className="h-4 w-4" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
