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
      {/* 拖拽上传区域 */}
      <motion.div
        initial={{ opacity: 0, scale: 0.98 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.1, duration: 0.4 }}
        className={cn(
          "relative border-2 border-dashed p-16 transition-all duration-300 cursor-pointer",
          isDragging 
            ? "border-black bg-gray-50" 
            : "border-gray-300 hover:border-black hover:bg-gray-50"
        )}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        
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
        
        <div className="flex flex-col items-center text-center space-y-6">
          <motion.div 
            className={cn(
              "p-6 transition-all duration-300",
              isDragging 
                ? "bg-black text-white" 
                : "bg-gray-100 text-black"
            )}
            animate={isDragging ? { scale: 1.1 } : { scale: 1 }}
            transition={{ duration: 0.3 }}
          >
            <Upload size={64} strokeWidth={1.5} />
          </motion.div>
          
          <div>
            <Text variant="h4" className="text-black mb-2 font-semibold">
              {isDragging ? '松开以上传文件' : '拖拽简历文件到此处'}
            </Text>
            <Text variant="p" className="text-gray-500">
              或点击选择文件
            </Text>
          </div>
          
          <div className="flex items-center gap-4 text-gray-500 text-sm">
            <span className="flex items-center gap-2 px-3 py-1.5 bg-gray-100">
              <FileText size={16} className="text-black" />
              支持 PDF, DOCX
            </span>
            <span>|</span>
            <span className="px-3 py-1.5 bg-gray-100">最大 10MB</span>
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
            className="border border-black p-6"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-gray-100 text-black">
                  <FileText size={24} />
                </div>
                <div>
                  <Text variant="p" className="text-black font-medium">{selectedFile.name}</Text>
                  <Text variant="caption" className="text-gray-500">
                    {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                  </Text>
                </div>
              </div>
              <Button 
                variant="primary" 
                onClick={handleUpload}
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
            className="bg-red-50 border border-red-200 p-4 text-red-600 text-center"
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
          className="flex items-center gap-4 px-6 py-3 border border-black"
        >
          <FileText size={24} className="text-black" />
          <Text variant="p" className="text-black">{selectedFile.name}</Text>
        </motion.div>
      )}

      {/* 加载动画 */}
      <div className="relative">
        <motion.div
          className="w-24 h-24 border-4 border-gray-200 border-t-black"
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
        />
      </div>

      {/* 进度文字 */}
      <div className="text-center space-y-4">
        <motion.div
          key={parsingText}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          <Text variant="h4" className="font-semibold">
            {parsingText || '正在解析简历...'}
          </Text>
        </motion.div>
        <div className="w-80 mx-auto">
          <div className="h-2 bg-gray-200 overflow-hidden">
            <motion.div 
              className="h-full bg-black"
              initial={{ width: 0 }}
              animate={{ width: `${uploadProgress}%` }}
              transition={{ duration: 0.3 }}
            />
          </div>
        </div>
        <Text variant="caption" className="text-gray-500">{uploadProgress}%</Text>
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
      {/* 加载动画 */}
      <div className="relative">
        <motion.div
          className="w-24 h-24 border-4 border-gray-200 border-t-black"
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
        />
      </div>

      {/* 文字提示 */}
      <div className="text-center space-y-4">
        <Text variant="h4" className="font-semibold">
          正在建立语音连接...
        </Text>
        <Text variant="p" className="text-gray-500 max-w-md">
          请稍候，我们正在为您准备面试环境。首次连接可能需要几秒钟时间。
        </Text>
      </div>

      {/* 进度条 */}
      <div className="w-80">
        <div className="h-1 bg-gray-200 overflow-hidden">
          <motion.div 
            className="h-full bg-black"
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
        {/* 候选人姓名 */}
        <motion.div variants={itemVariants}>
          <Card className="border border-black p-8">
            <CardHeader>
              <div className="flex items-center gap-3 text-black mb-3">
                <div className="p-2 bg-gray-100">
                  <User size={20} />
                </div>
                <Text variant="caption" className="uppercase tracking-wider">候选人</Text>
              </div>
              <Text variant="h2" className="font-bold">
                {resume.candidate_name}
              </Text>
            </CardHeader>
          </Card>
        </motion.div>

        {/* 技能标签 */}
        <motion.div variants={itemVariants}>
          <Card className="border border-black p-8">
            <CardHeader>
              <div className="flex items-center gap-3 text-black mb-4">
                <div className="p-2 bg-gray-100">
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
                    className="px-4 py-2 border border-black text-sm font-medium hover:bg-black hover:text-white transition-all duration-300 cursor-default"
                  >
                    {skill}
                  </motion.span>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* 行为标签 */}
        <motion.div variants={itemVariants}>
          <Card className="border border-black p-8">
            <CardHeader>
              <div className="flex items-center gap-3 text-black mb-4">
                <div className="p-2 bg-gray-100">
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
                    className="px-4 py-2 border border-black text-sm hover:bg-black hover:text-white transition-all duration-300 cursor-default"
                  >
                    {tag}
                  </motion.span>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* 项目经历 */}
        <motion.div variants={itemVariants}>
          <Card className="border border-black p-8">
            <CardHeader>
              <div className="flex items-center gap-3 text-black mb-6">
                <div className="p-2 bg-gray-100">
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
                    className="relative pl-6 py-3 border-l-4 border-black"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <Text variant="h4" className="text-black font-semibold">{project.name}</Text>
                      <Text variant="caption" className="text-gray-500 bg-gray-100 px-3 py-1">{project.time}</Text>
                    </div>
                    <Text variant="caption" className="text-black block mb-2 font-medium">{project.role}</Text>
                    <Text variant="p" className="text-gray-600 text-sm leading-relaxed">{project.description}</Text>
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
            className="flex-1"
            onClick={handleReupload}
          >
            <RefreshCw size={18} className="mr-2" />
            重新上传
          </Button>
          <Button
            variant="primary"
            className="flex-1"
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
              className="bg-red-50 border border-red-200 p-4 text-red-600 text-center"
            >
              {error}
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    );
  };

  return (
    <div className="min-h-screen text-black p-8 md:p-24 max-w-7xl mx-auto">
      <div className="max-w-4xl mx-auto">
        {/* 页面头部 */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="mb-12"
        >
          <Text variant="caption" className="text-gray-500 mb-2 uppercase tracking-widest text-sm">当前岗位</Text>
          <Text variant="h2" className="font-bold">
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
                  isActive ? "text-black" : isCompleted ? "text-black" : "text-gray-400"
                )}>
                  <motion.div 
                    className={cn(
                      "w-10 h-10 flex items-center justify-center text-sm font-bold transition-all duration-300",
                      isActive && "border-2 border-black",
                      isCompleted && "bg-black text-white",
                      !isActive && !isCompleted && "border border-gray-300"
                    )}
                    whileHover={isActive ? { scale: 1.05 } : {}}
                  >
                    {isCompleted ? <Check size={18} /> : index + 1}
                  </motion.div>
                  <Text variant="caption" className={cn(
                    "hidden sm:block font-medium",
                    isActive ? "text-black" : isCompleted ? "text-black" : "text-gray-400"
                  )}>{step}</Text>
                </div>
                {index < 2 && (
                  <div className={cn(
                    "w-8 sm:w-16 h-0.5 mx-3",
                    index < stepIndex 
                      ? "bg-black" 
                      : "bg-gray-200"
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
