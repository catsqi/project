"""
下载 SenseVoice 语音识别模型到本地

SenseVoice 是阿里达摩院开发的中文优化语音识别模型
- 中文准确率: 92-96%
- 模型大小: 约 300MB
- 识别速度: 比 Whisper 快 2-3 倍
"""

from modelscope import snapshot_download

# 模型下载目录
MODEL_DIR = "D:/ai_models/SenseVoice"

print("=" * 60)
print("开始下载 SenseVoice 模型...")
print(f"下载目录: {MODEL_DIR}")
print("=" * 60)

# 下载 SenseVoiceSmall 模型
model_id = "iic/SenseVoiceSmall"

try:
    model_dir = snapshot_download(
        model_id,
        cache_dir=MODEL_DIR,
        revision="master"
    )
    
    print("\n" + "=" * 60)
    print("SenseVoice 模型下载完成！")
    print(f"模型路径: {model_dir}")
    print("=" * 60)
    print("\n下一步:")
    print("1. 在 .env 文件中添加: SENSEVOICE_MODEL_PATH=<模型路径>")
    print("2. 运行项目测试识别效果")
    
except Exception as e:
    print(f"\n下载失败: {e}")
    print("\n请检查:")
    print("1. 网络连接是否正常")
    print("2. 是否有足够的磁盘空间 (约 300MB)")
