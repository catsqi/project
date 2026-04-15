import React from 'react';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, BarChart, Bar, XAxis, YAxis } from 'recharts';
import { cn } from './Button';

interface ChartProps {
  data: any[];
  className?: string;
}

export const RadarChartComponent: React.FC<ChartProps> = ({ data, className }) => {
  return (
    <div className={cn("w-full h-80", className)}>
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart cx="50%" cy="50%" outerRadius="80%" data={data}>
          {/* Black and White minimal styling */}
          <PolarGrid stroke="#000000" strokeWidth={1} />
          <PolarAngleAxis dataKey="subject" stroke="#000000" tick={{ fill: '#000000', fontSize: 14, fontWeight: 'bold' }} />
          <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
          <Radar name="Score" dataKey="A" stroke="#000000" strokeWidth={2} fill="transparent" />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
};

export const BarChartComponent: React.FC<ChartProps> = ({ data, className }) => {
  return (
    <div className={cn("w-full h-80", className)}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 20, right: 0, left: -20, bottom: 5 }}>
          {/* Strict minimal styling */}
          <XAxis dataKey="name" stroke="#000000" tickLine={false} axisLine={{ strokeWidth: 2 }} tick={{ fill: '#000000', fontSize: 12, fontWeight: 'bold' }} />
          <YAxis stroke="#000000" tickLine={false} axisLine={false} tick={{ fill: '#000000', fontSize: 12 }} />
          <Bar dataKey="score" fill="#000000" barSize={30} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
