import React, { useState } from 'react';
import { Text } from '../components/ReactBits/Text';
import { Input } from '../components/ReactBits/Input';
import { Button } from '../components/ReactBits/Button';
import { useNavigate } from 'react-router-dom';

const LoginRegister: React.FC = () => {
  const navigate = useNavigate();
  const [isLogin, setIsLogin] = useState(true);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    navigate('/jobs'); // Mock login success, bypass to jobs route
  };

  return (
    <div className="min-h-screen text-black flex flex-col md:flex-row">
      <div className="flex-1 p-8 md:p-24 flex flex-col justify-center border-b md:border-b-0 md:border-r border-black">
        <Text variant="display" className="mb-8">
          {isLogin ? "SIGN IN" : "REGISTER"}
        </Text>
        <Text variant="p">
          Access your personalized interview room.
        </Text>
      </div>

      <div className="flex-1 p-8 md:p-24 flex flex-col justify-center">
        <form onSubmit={handleSubmit} className="space-y-12 max-w-md w-full">
          <Input 
            type="email" 
            placeholder="EMAIL ADDRESS" 
            required 
          />
          <Input 
            type="password" 
            placeholder="PASSWORD" 
            required 
          />

          <div className="pt-8 flex flex-col gap-6">
            <Button type="submit" variant="primary" size="lg" className="w-full">
              {isLogin ? 'ENTER' : 'CREATE ACCOUNT'}
            </Button>
            
            <button 
              type="button"
              className="text-left text-sm font-bold uppercase tracking-widest link-hover"
              onClick={() => setIsLogin(!isLogin)}
            >
              {isLogin ? "Need an account? Register" : "Already have an account? Sign In"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default LoginRegister;
