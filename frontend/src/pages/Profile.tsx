import React from 'react';
import { Text } from '../components/ui/Text';
import { Button } from '../components/ui/Button';
import { useNavigate } from 'react-router-dom';

const history = [
  { id: 'T-001', role: 'Frontend Engineering', date: '2026.04.05', score: 82 },
  { id: 'T-002', role: 'Frontend Engineering', date: '2026.04.01', score: 65 },
  { id: 'J-001', role: 'Java Backend', date: '2026.03.15', score: 78 },
];

const Profile: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen text-black p-8 md:p-24 max-w-5xl mx-auto">
      <header className="mb-24 flex justify-between items-start border-b border-black pb-8">
        <Text variant="display">CANDIDATE: YAN</Text>
        <Button variant="ghost" onClick={() => navigate('/jobs')}>BACK TO HUB</Button>
      </header>

      <section className="mb-24">
        <Text variant="h4" className="mb-12">HISTORY NOTEBOOK</Text>
        <div className="border border-black">
          {history.map((record, idx) => (
            <div 
              key={record.id} 
              className={`flex flex-col sm:flex-row justify-between p-6 sm:items-center hover:bg-black hover:text-white transition-colors cursor-pointer ${idx !== history.length -1 ? 'border-b border-black' : ''}`}
              onClick={() => navigate('/report')}
            >
              <div className="flex flex-col sm:flex-row sm:gap-12 gap-2">
                <Text variant="caption">{record.date}</Text>
                <Text variant="caption">{record.id}</Text>
                <Text variant="p" className="font-bold">{record.role}</Text>
              </div>
              <div className="mt-4 sm:mt-0 flex items-center gap-4">
                <Text variant="caption">SCORE</Text>
                <Text variant="h3" className="w-16 text-right">{record.score}</Text>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="grid grid-cols-1 md:grid-cols-2 gap-12">
        <div className="border p-8 border-black hover:bg-neon-green hover:border-neon-green transition-colors cursor-pointer group">
          <Text variant="h4" className="mb-4">REVIEW MISTAKES</Text>
          <Text variant="p" className="text-gray-700 group-hover:text-black">
            Access your curated list of weak points and related questions.
          </Text>
        </div>
        <div className="border p-8 border-black hover:bg-neon-green hover:border-neon-green transition-colors cursor-pointer group">
          <Text variant="h4" className="mb-4">GROWTH PATH</Text>
          <Text variant="p" className="text-gray-700 group-hover:text-black">
            View your personal skill progression algorithm.
          </Text>
        </div>
      </section>
    </div>
  );
};

export default Profile;
