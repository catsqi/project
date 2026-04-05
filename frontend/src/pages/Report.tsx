import React from 'react';
import { Text } from '../components/ReactBits/Text';
import { Button } from '../components/ReactBits/Button';
import { RadarChartComponent, BarChartComponent } from '../components/ReactBits/Chart';
import { useNavigate } from 'react-router-dom';

const radarData = [
  { subject: 'TECH ACCURACY', A: 85, fullMark: 100 },
  { subject: 'LOGIC & EXPRESSION', A: 70, fullMark: 100 },
  { subject: 'KNOWLEDGE DEPTH', A: 90, fullMark: 100 },
  { subject: 'ROLE MATCH', A: 80, fullMark: 100 },
];

const barData = [
  { name: 'JavaScript', score: 95 },
  { name: 'React', score: 85 },
  { name: 'CSS/Layout', score: 70 },
  { name: 'Performance', score: 60 },
];

const Report: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen text-black p-8 md:p-24 max-w-7xl mx-auto">
      <header className="mb-24 flex flex-col md:flex-row justify-between items-start md:items-end border-b border-black pb-8 gap-8">
        <div>
          <Text variant="h1">EVALUATION REPORT</Text>
          <Text variant="p" className="mt-4 max-w-xl">
            Detailed analysis of your interview performance for FRONTEND ENGINEERING // SENIOR.
          </Text>
        </div>
        <div className="flex gap-4">
          <Button variant="outline" onClick={() => navigate('/jobs')}>RE-TAKE</Button>
          <Button variant="primary" onClick={() => navigate('/profile')}>MY PROFILE</Button>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-24">
        {/* Left Column: Visuals */}
        <div className="space-y-24">
          <section>
            <Text variant="h4" className="mb-12 border-b border-black inline-block pb-2">CORE DIMENSIONS</Text>
            <RadarChartComponent data={radarData} />
          </section>
          
          <section>
            <Text variant="h4" className="mb-12 border-b border-black inline-block pb-2">SKILL BREAKDOWN</Text>
            <BarChartComponent data={barData} />
          </section>
        </div>

        {/* Right Column: Text Feedback */}
        <div className="space-y-16">
          <section>
            <Text variant="caption" className="text-gray-500 mb-2 block">OVERALL SCORE</Text>
            <Text variant="display">82</Text>
            <div className="h-1 w-full bg-black mt-4"></div>
          </section>

          <section className="space-y-6">
            <Text variant="h4">FEEDBACK & ANALYSIS</Text>
            <div>
              <Text variant="caption" className="font-bold border-l-4 border-neon-green pl-4">STRENGTHS</Text>
              <Text variant="p" className="mt-2 pl-4">
                Demonstrated strong understanding of React internals and state management. Logic is clear and concise during problem solving.
              </Text>
            </div>
            <div className="pt-4">
              <Text variant="caption" className="font-bold border-l-4 border-black pl-4">AREAS FOR IMPROVEMENT</Text>
              <Text variant="p" className="mt-2 pl-4">
                Performance optimization answers lacked depth. Needs improvement on explaining exact rendering timeline and memoization trade-offs.
              </Text>
            </div>
          </section>

          <section className="bg-gray-50 p-8 border border-black">
            <Text variant="caption" className="font-bold block mb-4">RECOMMENDED RESOURCES</Text>
            <ul className="space-y-4 list-none m-0 p-0">
              <li>
                <a href="#" className="link-hover font-bold text-lg">Advanced React Patterns</a>
              </li>
              <li>
                <a href="#" className="link-hover font-bold text-lg">Browser Rendering Pipeline Deep Dive</a>
              </li>
            </ul>
          </section>
        </div>
      </div>
    </div>
  );
};

export default Report;
