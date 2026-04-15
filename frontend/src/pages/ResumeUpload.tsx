import React, { useState, useCallback, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Upload, FileText, Check, RefreshCw, Loader2, User, Briefcase, Tag, Code, Sparkles, FileCheck } from 'lucide-react';
import { Text } from '../components/ui/Text';
import { Button } from '../components/ui/Button';
import { Card, CardHeader, CardContent } from '../components/ui/Card';
import { Progress } from '../components/ui/Progress';
import { cn } from '../components/ui/Button';
import { useWebRTCStore } from '../store/webrtcStore';

// 简历数据类型定义
interface Project {
  name: string;
  role: string;
  time: string;
  description: string;
}

interface GlobalProfile {
  summary: string;
  all_technical_skills: string[];
  all_behavioral_tags: string[];
}

interface ResumeData {
  candidate_name: string;
  global_profile: GlobalProfile;
  projects: Project[];
}

interface UploadResponse {
  candidate_id: string;
  resume: ResumeData;
}

type Stage = 'upload' | 'parsing' | 'confirm' | 'connecting';

const ResumeUpload: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const jobTitle = location.state?.jobTitle || '未选择岗位';
  
  // 获取 WebRTC store
  const { connect } = useWebRTCStore();
  
  const [stage, setStage] = useState<Stage>('upload');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [parsingText, setParsingText] = useState('');
  const [resumeData, setResumeData] = useState<UploadResponse | null>(null);
  const [candidateId, setCandidateId] = useState<string>('');
  const [error, setError] = useState<string>('');
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const parsingTexts = [
    '正在解析简历...',
    'AI 正在分析您的项目经历...',
    '提取技术技能标签...',
    '生成候选人画像...',
    '即将完成...'
  ];

  // 处理文件选择
  const handleFileSelect = useCallback((file: File) => {
    const validTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
    if (!validTypes.includes(file.type)) {
      setError('请上传 PDF 或 DOCX 格式的文件');
      return;
    }
    
    if (file.size > 10 * 1024 * 1024) {
      setError('文件大小不能超过 10MB');
      return;
    }
    
    setSelectedFile(file);
    setError('');
  }, []);

  // 拖拽处理
  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    
    const file = e.dataTransfer.files[0];
    if (file) {
      handleFileSelect(file);
    }
  }, [handleFileSelect]);

  // 上传并解析简历
  const handleUpload = async () => {
    if (!selectedFile) return;
    
    setStage('parsing');
    setUploadProgress(0);
    
    // 模拟进度更新
    let textIndex = 0;
    const textInterval = setInterval(() => {
      textIndex = (textIndex + 1) % parsingTexts.length;
      setParsingText(parsingTexts[textIndex]);
    }, 2000);
    
    // 模拟进度
    const progressInterval = setInterval(() => {
      setUploadProgress(prev => Math.min(prev + 10, 90));
    }, 500);

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      
      const response = await fetch('/api/resume/upload', {
        method: 'POST',
        body: formData,
      });
      
      if (!response.ok) {
        throw new Error('上传失败，请重试');
      }
      
      const data: UploadResponse = await response.json();
      
      clearInterval(textInterval);
      clearInterval(progressInterval);
      setUploadProgress(100);
      setParsingText('解析完成！');
      
      setTimeout(() => {
        setResumeData(data);
        setCandidateId(data.candidate_id);
        setStage('confirm');
      }, 500);
      
    } catch (err: any) {
      clearInterval(textInterval);
      clearInterval(progressInterval);
      setError(err.message || '上传失败，请重试');
      setStage('upload');
    }
  };

  // 确认并开始面试
  const handleConfirm = async () => {
    if (!resumeData || !candidateId) return;
    
    try {
      // 1. 先调用后端确认 API
      const response = await fetch('/api/resume/confirm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          candidate_id: candidateId, 
          resume: resumeData.resume 
        }),
      });
      
      if (!response.ok) {
        throw new Error('确认失败，请重试');
      }
      
      // 2. 预连接 WebRTC（在进入房间前就开始连接）
      setStage('connecting');
      
      try {
        await connect();
        console.log('[Frontend] WebRTC 预连接成功');
      } catch (webrtcErr: any) {
        console.warn('[Frontend] WebRTC 预连接失败，将在房间内重试:', webrtcErr);
        // 即使预连接失败，也允许进入房间，InterviewRoom 会再次尝试
      }
      
      // 3. 跳转到面试房间
      navigate('/interview', {
        state: {
          candidateId: candidateId,
          jobTitle: jobTitle
        }
      });
    } catch (err: any) {
      setError(err.message || '确认失败，请重试');
      setStage('confirm');
    }
  };

  // 重新上传
  const handleReupload = () => {
    setSelectedFile(null);
    setResumeData(null);
    setCandidateId('');
    setUploadProgress(0);
    setParsingText('');
    setError('');
    setStage('upload');
  };

  // 阶段1: 上传
  const renderUploadStage = () => (
    <motion.div
      key="upload"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className="space-y-8"
    >
      {/* 拖拽上传区域 - Glassmorphism 风格 */}
      <motion.div
        initial={{ opacity: 0, scale: 0.98 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.1, duration: 0.4 }}
        className={cn(
          "relative border-2 border-dashed rounded-2xl p-16 transition-all duration-500 cursor-pointer overflow-hidden",
          isDragging 
            ? "border-cyan-400/60 bg-cyan-400/10 shadow-[0_0_40px_rgba(34,211,238,0.2)]" 
            : "border-purple-500/30 bg-white/[0.03] backdrop-blur-md hover:border-purple-400/50 hover:bg-white/[0.06] hover:shadow-[0_0_30px_rgba(168,85,247,0.15)]"
        )}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        {/* 背景装饰 */}
        <div className="absolute inset-0 bg-gradient-to-br from-purple-500/5 via-transparent to-cyan-500/5 pointer-events-none" />
        
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFileSelect(file);
          }}
        />
        
        <div className="flex flex-col items-center text-center space-y-6 relative z-10">
          <motion.div 
            className={cn(
              "p-6 rounded-2xl transition-all duration-500",
              isDragging 
                ? "bg-gradient-to-br from-cyan-400/20 to-blue-500/20 text-cyan-300 shadow-[0_0_30px_rgba(34,211,238,0.3)]" 
                : "bg-gradient-to-br from-purple-500/10 to-blue-500/10 text-purple-300"
            )}
            animate={isDragging ? { scale: 1.1 } : { scale: 1 }}
            transition={{ duration: 0.3 }}
          >
            <Upload size={64} strokeWidth={1.5} />
          </motion.div>
          
          <div>
            <Text variant="h4" className="text-white mb-2 font-semibold">
              {isDragging ? '松开以上传文件' : '拖拽简历文件到此处'}
            </Text>
            <Text variant="p" className="text-gray-400">
              或点击选择文件
            </Text>
          </div>
          
          <div className="flex items-center gap-4 text-gray-500 text-sm">
            <span className="flex items-center gap-2 px-3 py-1.5 bg-white/5 rounded-full">
              <FileText size={16} className="text-purple-400" />
              支持 PDF, DOCX
            </span>
            <span className="text-gray-600">|</span>
            <span className="px-3 py-1.5 bg-white/5 rounded-full">最大 10MB</span>
          </div>
        </div>
      </motion.div>

      {/* 已选择的文件 */}
      <AnimatePresence>
        {selectedFile && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.95 }}
            transition={{ duration: 0.3 }}
            className="bg-gradient-to-r from-gray-800/60 to-gray-900/60 backdrop-blur-md border border-purple-500/20 rounded-xl p-6 shadow-lg"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-gradient-to-br from-cyan-400/20 to-blue-500/20 rounded-xl text-cyan-300">
                  <FileText size={24} />
                </div>
                <div>
                  <Text variant="p" className="text-white font-medium">{selectedFile.name}</Text>
                  <Text variant="caption" className="text-gray-400">
                    {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                  </Text>
                </div>
              </div>
              <Button 
                variant="neon" 
                onClick={handleUpload}
                className="bg-gradient-to-r from-cyan-400 to-blue-500 hover:from-cyan-300 hover:to-blue-400 text-black font-semibold shadow-[0_0_20px_rgba(34,211,238,0.3)] hover:shadow-[0_0_30px_rgba(34,211,238,0.5)] transition-all duration-300"
              >
                <Sparkles size={18} className="mr-2" />
                开始解析
              </Button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* 错误提示 */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-300 text-center backdrop-blur-sm"
          >
            {error}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );

  // 阶段2: 解析中
  const renderParsingStage = () => (
    <motion.div
      key="parsing"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.4 }}
      className="flex flex-col items-center justify-center py-24 space-y-8"
    >
      {/* 文件信息 */}
      {selectedFile && (
        <motion.div 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="flex items-center gap-4 px-6 py-3 bg-white/5 backdrop-blur-sm rounded-full border border-purple-500/20"
        >
          <FileText size={24} className="text-cyan-400" />
          <Text variant="p" className="text-gray-200">{selectedFile.name}</Text>
        </motion.div>
      )}

      {/* 加载动画 - 渐变旋转环 */}
      <div className="relative">
        {/* 外圈渐变 */}
        <motion.div
          className="w-24 h-24 rounded-full"
          style={{
            background: 'conic-gradient(from 0deg, transparent, rgba(34,211,238,0.8), rgba(168,85,247,0.8), transparent)',
          }}
          animate={{ rotate: 360 }}
          transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
        />
        {/* 内圈背景 */}
        <div className="absolute inset-2 rounded-full bg-gradient-to-br from-gray-900 to-gray-800 flex items-center justify-center">
          <motion.div
            animate={{ scale: [1, 1.2, 1], opacity: [0.5, 1, 0.5] }}
            transition={{ duration: 1.5, repeat: Infinity }}
          >
            <Sparkles size={32} className="text-cyan-400" />
          </motion.div>
        </div>
      </div>

      {/* 进度文字 */}
      <div className="text-center space-y-4">
        <motion.div
          key={parsingText}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          <Text variant="h4" className="bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent font-semibold">
            {parsingText || '正在解析简历...'}
          </Text>
        </motion.div>
        <div className="w-80 mx-auto">
          <div className="h-2 bg-gray-700/50 rounded-full overflow-hidden">
            <motion.div 
              className="h-full bg-gradient-to-r from-cyan-400 to-purple-500 rounded-full"
              initial={{ width: 0 }}
              animate={{ width: `${uploadProgress}%` }}
              transition={{ duration: 0.3 }}
            />
          </div>
        </div>
        <Text variant="caption" className="text-gray-500 font-mono">{uploadProgress}%</Text>
      </div>
    </motion.div>
  );

  // 阶段3.5: 连接中（预连接 WebRTC）
  const renderConnectingStage = () => (
    <motion.div
      key="connecting"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.4 }}
      className="flex flex-col items-center justify-center py-24 space-y-8"
    >
      {/* 加载动画 - 脉冲效果 */}
      <div className="relative">
        <motion.div
          className="w-32 h-32 rounded-full bg-gradient-to-br from-cyan-400/30 to-purple-500/30"
          animate={{ 
            scale: [1, 1.2, 1],
            opacity: [0.5, 0.8, 0.5]
          }}
          transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
        />
        <div className="absolute inset-0 flex items-center justify-center">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
          >
            <Loader2 size={48} className="text-cyan-400" />
          </motion.div>
        </div>
      </div>

      {/* 文字提示 */}
      <div className="text-center space-y-4">
        <Text variant="h4" className="bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent font-semibold">
          正在建立语音连接...
        </Text>
        <Text variant="p" className="text-gray-400 max-w-md">
          请稍候，我们正在为您准备面试环境。首次连接可能需要几秒钟时间。
        </Text>
      </div>

      {/* 进度条 */}
      <div className="w-80">
        <div className="h-1 bg-gray-700/50 rounded-full overflow-hidden">
          <motion.div 
            className="h-full bg-gradient-to-r from-cyan-400 to-purple-500 rounded-full"
            initial={{ width: "0%", x: "-100%" }}
            animate={{ width: "100%", x: ["-100%", "100%"] }}
            transition={{ 
              x: { duration: 1.5, repeat: Infinity, ease: "linear" },
              width: { duration: 0.3 }
            }}
          />
        </div>
      </div>
    </motion.div>
  );

  // 阶段3: 确认
  const renderConfirmStage = () => {
    if (!resumeData) return null;
    
    const { resume } = resumeData;
    
    const containerVariants = {
      hidden: { opacity: 0 },
      show: {
        opacity: 1,
        transition: { staggerChildren: 0.1 }
      }
    };
    
    const itemVariants = {
      hidden: { opacity: 0, y: 20 },
      show: { opacity: 1, y: 0 }
    };
    
    return (
      <motion.div
        key="confirm"
        variants={containerVariants}
        initial="hidden"
        animate="show"
        exit={{ opacity: 0, y: -20 }}
        className="space-y-6"
      >
        {/* 候选人姓名 - Glassmorphism Card */}
        <motion.div variants={itemVariants}>
          <Card className="bg-gradient-to-br from-gray-800/50 to-gray-900/50 backdrop-blur-md border border-purple-500/20 rounded-xl p-8 shadow-lg hover:shadow-purple-500/10 transition-shadow duration-300">
            <CardHeader>
              <div className="flex items-center gap-3 text-purple-400 mb-3">
                <div className="p-2 bg-purple-500/10 rounded-lg">
                  <User size={20} />
                </div>
                <Text variant="caption" className="uppercase tracking-wider">候选人</Text>
              </div>
              <Text variant="h2" className="bg-gradient-to-r from-white to-gray-300 bg-clip-text text-transparent font-bold">
                {resume.candidate_name}
              </Text>
            </CardHeader>
          </Card>
        </motion.div>

        {/* 技能标签 - 渐变色彩 */}
        <motion.div variants={itemVariants}>
          <Card className="bg-gradient-to-br from-gray-800/50 to-gray-900/50 backdrop-blur-md border border-cyan-500/20 rounded-xl p-8 shadow-lg">
            <CardHeader>
              <div className="flex items-center gap-3 text-cyan-400 mb-4">
                <div className="p-2 bg-cyan-500/10 rounded-lg">
                  <Code size={20} />
                </div>
                <Text variant="caption" className="uppercase tracking-wider">技术技能</Text>
              </div>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-3">
                {resume.global_profile.all_technical_skills.map((skill, index) => (
                  <motion.span
                    key={index}
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 0.3 + index * 0.05 }}
                    whileHover={{ scale: 1.05 }}
                    className="px-4 py-2 bg-gradient-to-r from-cyan-500/10 to-blue-500/10 border border-cyan-400/30 text-cyan-300 text-sm font-medium rounded-lg hover:from-cyan-500/20 hover:to-blue-500/20 hover:border-cyan-400/50 transition-all duration-300 cursor-default"
                  >
                    {skill}
                  </motion.span>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* 行为标签 - 紫色渐变 */}
        <motion.div variants={itemVariants}>
          <Card className="bg-gradient-to-br from-gray-800/50 to-gray-900/50 backdrop-blur-md border border-purple-500/20 rounded-xl p-8 shadow-lg">
            <CardHeader>
              <div className="flex items-center gap-3 text-purple-400 mb-4">
                <div className="p-2 bg-purple-500/10 rounded-lg">
                  <Tag size={20} />
                </div>
                <Text variant="caption" className="uppercase tracking-wider">行为标签</Text>
              </div>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-3">
                {resume.global_profile.all_behavioral_tags.map((tag, index) => (
                  <motion.span
                    key={index}
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 0.4 + index * 0.05 }}
                    whileHover={{ scale: 1.05 }}
                    className="px-4 py-2 bg-gradient-to-r from-purple-500/10 to-pink-500/10 border border-purple-400/30 text-purple-300 text-sm rounded-lg hover:from-purple-500/20 hover:to-pink-500/20 hover:border-purple-400/50 transition-all duration-300 cursor-default"
                  >
                    {tag}
                  </motion.span>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* 项目经历 - 彩色边条装饰 */}
        <motion.div variants={itemVariants}>
          <Card className="bg-gradient-to-br from-gray-800/50 to-gray-900/50 backdrop-blur-md border border-gray-700/50 rounded-xl p-8 shadow-lg">
            <CardHeader>
              <div className="flex items-center gap-3 text-gray-400 mb-6">
                <div className="p-2 bg-gray-500/10 rounded-lg">
                  <Briefcase size={20} />
                </div>
                <Text variant="caption" className="uppercase tracking-wider">项目经历</Text>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                {resume.projects.map((project, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.5 + index * 0.1 }}
                    className="relative pl-6 py-3"
                  >
                    {/* 彩色渐变边条 */}
                    <div 
                      className="absolute left-0 top-0 bottom-0 w-1 rounded-full"
                      style={{
                        background: `linear-gradient(to bottom, ${index % 2 === 0 ? '#22d3ee' : '#a855f7'}, ${index % 2 === 0 ? '#3b82f6' : '#ec4899'})`
                      }}
                    />
                    <div className="flex items-start justify-between mb-2">
                      <Text variant="h4" className="text-white font-semibold">{project.name}</Text>
                      <Text variant="caption" className="text-gray-500 bg-gray-800/50 px-3 py-1 rounded-full">{project.time}</Text>
                    </div>
                    <Text variant="caption" className="text-cyan-400 block mb-2 font-medium">{project.role}</Text>
                    <Text variant="p" className="text-gray-400 text-sm leading-relaxed">{project.description}</Text>
                  </motion.div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* 操作按钮 */}
        <motion.div
          variants={itemVariants}
          className="flex gap-4 pt-4"
        >
          <Button
            variant="outline"
            className="flex-1 border-gray-600 text-gray-300 hover:bg-gray-800/50 hover:text-white hover:border-gray-500 rounded-lg transition-all duration-300"
            onClick={handleReupload}
          >
            <RefreshCw size={18} className="mr-2" />
            重新上传
          </Button>
          <Button
            variant="neon"
            className="flex-1 bg-gradient-to-r from-cyan-400 to-blue-500 hover:from-cyan-300 hover:to-blue-400 text-black font-semibold rounded-lg shadow-[0_0_20px_rgba(34,211,238,0.3)] hover:shadow-[0_0_30px_rgba(34,211,238,0.5)] transition-all duration-300"
            onClick={handleConfirm}
          >
            <FileCheck size={18} className="mr-2" />
            确认开始面试
          </Button>
        </motion.div>

        {/* 错误提示 */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-300 text-center backdrop-blur-sm"
            >
              {error}
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    );
  };

  return (
    <div className="min-h-screen text-white p-8 md:p-16 relative overflow-hidden"
      style={{
        background: 'linear-gradient(135deg, #0f172a 0%, #1e1b4b 25%, #0f172a 50%, #1e1b4b 75%, #0f172a 100%)'
      }}
    >
      {/* 背景装饰 */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {/* 渐变光晕 */}
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl" />
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl" />
        {/* 网格纹理 */}
        <div 
          className="absolute inset-0 opacity-[0.02]"
          style={{
            backgroundImage: `linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px),
                              linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)`,
            backgroundSize: '50px 50px'
          }}
        />
      </div>

      <div className="max-w-4xl mx-auto relative z-10">
        {/* 页面头部 */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="mb-12"
        >
          <Text variant="caption" className="text-purple-400 mb-2 uppercase tracking-widest text-sm">当前岗位</Text>
          <Text variant="h2" className="bg-gradient-to-r from-white via-gray-200 to-gray-400 bg-clip-text text-transparent font-bold">
            {jobTitle}
          </Text>
        </motion.div>

        {/* 阶段指示器 */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2, duration: 0.5 }}
          className="flex items-center gap-4 mb-12"
        >
          {['上传简历', 'AI 解析', '确认信息'].map((step, index) => {
            const stepIndex = ['upload', 'parsing', 'confirm', 'connecting'].indexOf(stage);
            const isActive = index === stepIndex;
            const isCompleted = index < stepIndex;
            
            return (
              <div key={step} className="flex items-center">
                <div className={cn(
                  "flex items-center gap-2 transition-all duration-300",
                  isActive ? "text-cyan-400" : isCompleted ? "text-purple-400" : "text-gray-600"
                )}>
                  <motion.div 
                    className={cn(
                      "w-10 h-10 flex items-center justify-center rounded-xl text-sm font-bold transition-all duration-300",
                      isActive && "bg-gradient-to-br from-cyan-400/20 to-blue-500/20 border border-cyan-400/50 shadow-[0_0_20px_rgba(34,211,238,0.2)]",
                      isCompleted && "bg-gradient-to-br from-purple-500/20 to-pink-500/20 border border-purple-400/50",
                      !isActive && !isCompleted && "bg-gray-800/50 border border-gray-700"
                    )}
                    whileHover={isActive ? { scale: 1.05 } : {}}
                  >
                    {isCompleted ? <Check size={18} /> : index + 1}
                  </motion.div>
                  <Text variant="caption" className={cn(
                    "hidden sm:block font-medium",
                    isActive ? "text-cyan-400" : isCompleted ? "text-purple-400" : "text-gray-500"
                  )}>{step}</Text>
                </div>
                {index < 2 && (
                  <div className={cn(
                    "w-8 sm:w-16 h-0.5 mx-3 rounded-full transition-all duration-500",
                    index < stepIndex 
                      ? "bg-gradient-to-r from-purple-400 to-cyan-400" 
                      : "bg-gray-800"
                  )} />
                )}
              </div>
            );
          })}
        </motion.div>

        {/* 内容区域 */}
        <AnimatePresence mode="wait">
          {stage === 'upload' && renderUploadStage()}
          {stage === 'parsing' && renderParsingStage()}
          {stage === 'confirm' && renderConfirmStage()}
          {stage === 'connecting' && renderConnectingStage()}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default ResumeUpload;
