import { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, useLocation } from 'react-router-dom';
import Home from './pages/Home';
import LoginRegister from './pages/LoginRegister';
import JobSelect from './pages/JobSelect';
import InterviewRoom from './pages/InterviewRoom';
import Report from './pages/Report';
import Profile from './pages/Profile';
import Antigravity from './components/ReactBits/Antigravity';

// 粒子背景控制器：根据路由决定是否显示
const BackgroundLayer = ({ mouse }: { mouse: { x: number; y: number } }) => {
  const location = useLocation();
  // 仅在首页、登录、职位选择、个人中心显示粒子
  const showParticles = ['/', '/login', '/jobs', '/profile'].includes(location.pathname);

  if (!showParticles) return null;

  return (
    <Antigravity 
      count={200} // 减少粒子数
      magnetRadius={40}
      ringRadius={20}
      waveSpeed={0.3}
      waveAmplitude={1.5}
      particleSize={0.7} // 稍微再调小一点
      lerpSpeed={0.05}
      color="#000000"
      autoAnimate={false}
      particleVariance={1}
      rotationSpeed={0}
      depthFactor={1}
      pulseSpeed={2}
      particleShape="sphere"
      fieldStrength={15}
      globalMouse={mouse}
    />
  );
};

function App() {
  const [mouse, setMouse] = useState({ x: 0, y: 0 });

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      setMouse({
        x: (e.clientX / window.innerWidth) * 2 - 1,
        y: -(e.clientY / window.innerHeight) * 2 + 1
      });
    };
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  return (
    <Router>
      <div className="relative min-h-screen w-full font-sans overflow-x-hidden">
        {/* 底部纯白保底层 */}
        <div className="fixed inset-0 bg-white z-[-2]" />

        {/* 动态粒子背景层 */}
        <BackgroundLayer mouse={mouse} />

        {/* 核心内容层 */}
        <div className="relative z-10 w-full">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/login" element={<LoginRegister />} />
            <Route path="/jobs" element={<JobSelect />} />
            <Route path="/interview" element={<InterviewRoom />} />
            <Route path="/report" element={<Report />} />
            <Route path="/profile" element={<Profile />} />
          </Routes>
        </div>
      </div>
    </Router>
  );
}

export default App;
