import React from 'react';
import { Text } from '../components/ui/Text';
import { Button } from '../components/ui/Button';
import { useNavigate } from 'react-router-dom';

const Home: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen text-black p-8 md:p-24 flex flex-col justify-center max-w-7xl mx-auto space-y-16">
      <div className="space-y-6 max-w-4xl">
        <Text variant="display">AI EXAMINER</Text>
        <Text variant="h3" className="text-gray-500 font-normal">
          Simulate real-world interviews. Track your growth. No noise.
        </Text>
      </div>

      <div className="flex flex-col sm:flex-row gap-6">
        <Button variant="neon" size="xl" onClick={() => navigate('/login')}>
          Start Journey
        </Button>
        <Button variant="outline" size="xl" onClick={() => navigate('/jobs')}>
          View Roles
        </Button>
      </div>

      <div className="pt-24 border-t border-black mt-24">
        <Text variant="h4">System Status: <span className="text-neon-green ml-2">ONLINE</span></Text>
      </div>
    </div>
  );
};

export default Home;
