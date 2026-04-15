from modelscope import snapshot_download

# 指定下载到你的目录
model_dir = snapshot_download('iic/SenseVoiceSmall', cache_dir='D:/ai_models/SenseVoice/')
print(f"模型已完整下载至: {model_dir}")