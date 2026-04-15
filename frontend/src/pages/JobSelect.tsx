import React from 'react';
import { Text } from '../components/ui/Text';
import { Button } from '../components/ui/Button';
import { useNavigate } from 'react-router-dom';

const jobs = [
  { id: 'frontend', title: 'WEB FRONTEND', tech: 'React, Vue, TypeScript, CSS', type: 'Technical / Whiteboard' },
  { id: 'backend', title: 'JAVA BACKEND', tech: 'Spring Boot, MySQL, Redis, JVM', type: 'System Design / Algorithm' },
];

const JobSelect: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen text-black p-8 md:p-24 max-w-7xl mx-auto">
      <div className="mb-24 flex justify-between items-end">
        <div>
          <Text variant="h1">SELECT ROLE</Text>
          <Text variant="p" className="mt-4 max-w-xl">
            Choose the position you want to apply for. The AI Interviewer will adapt the questions and difficulty accordingly.
          </Text>
        </div>
        <Button variant="ghost" size="sm" onClick={() => navigate('/profile')}>MY PROFILE</Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
        {jobs.map((job) => (
          <div key={job.id} className="border border-black p-12 hover:bg-black hover:text-white group transition-colors duration-300">
            <div className="space-y-6">
              <Text variant="h3" className="group-hover:text-neon-green">{job.title}</Text>
              <div>
                <Text variant="caption" className="block text-gray-500 group-hover:text-gray-300">TECH STACK</Text>
                <Text variant="p">{job.tech}</Text>
              </div>
              <div>
                <Text variant="caption" className="block text-gray-500 group-hover:text-gray-300">INTERVIEW TYPE</Text>
                <Text variant="p">{job.type}</Text>
              </div>
              
              <div className="pt-8">
                <Button 
                  variant="outline" 
                  className="group-hover:border-white group-hover:text-white group-hover:bg-transparent hover:!bg-neon-green hover:!text-black hover:!border-neon-green"
                  onClick={() => navigate('/resume-upload', { state: { jobTitle: job.title } })}
                >
                  SELECT & CONTINUE
                </Button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default JobSelect;
