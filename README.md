# EPUB转TTS工具

一个简洁易用的EPUB电子书转文本语音（TTS）工具，使用Microsoft Edge TTS引擎将EPUB电子书转换为高质量的MP3音频文件。

## ✨ 功能特色

- 🎵 **高质量语音合成** - 使用Microsoft Edge TTS引擎，支持多种中文语音
- 📚 **智能章节识别** - 自动解析EPUB目录结构，支持选择性转换  
- 🖱️ **拖拽操作** - 支持直接拖拽EPUB文件到界面
- ⏸️ **灵活控制** - 支持暂停、继续、重新开始转换
- 📊 **实时进度** - 显示转换进度和每个章节的状态
- 🎯 **批量转换** - 可选择转换特定章节或整本书
- 💾 **自动命名** - 根据章节标题自动生成音频文件名

## 🔧 系统要求

- Windows 10/11
- Python 3.7+
- 网络连接（Microsoft Edge TTS需要在线服务）

## 📦 安装方法

### 1. 克隆项目

```bash
git clone https://github.com/opciuev/epub_tts_gui.git
cd epub_tts_gui
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 运行程序

```bash
python main.py
```

## 🚀 使用方法

### 基本操作

1. **选择EPUB文件**
   - 点击"选择文件"按钮选择EPUB文件
   - 或直接拖拽EPUB文件到输入框

2. **设置输出目录**
   - 点击"选择目录"设置音频文件保存位置

3. **配置语音参数**
   - 选择语音类型（默认：zh-CN-XiaoxiaoNeural）
   - 调整语音速度、音量等参数

4. **选择转换章节**
   - 程序会自动解析并显示所有章节
   - 双击章节可切换选择状态
   - 支持选择性转换特定章节

5. **开始转换**
   - 点击"开始转换"按钮
   - 实时查看转换进度和状态

### 高级功能

- **暂停/继续**: 转换过程中可随时暂停和继续
- **重新开始**: 从头开始转换所有选中章节
- **状态监控**: 实时显示每个章节的转换状态

## 📋 依赖包

- `edge-tts` - Microsoft Edge 文本转语音引擎
- `beautifulsoup4` - HTML/XML解析器
- `tkinterdnd2` - Tkinter拖拽支持

## 🔊 支持的语音

程序支持多种中文语音，包括：
- zh-CN-XiaoxiaoNeural（默认）
- zh-CN-YunyeNeural  
- zh-CN-YunjianNeural
- zh-CN-XiaoyiNeural
- 更多语音选项...

## 📁 文件结构

```
epub_tts_gui/
├── main.py              # 主程序GUI界面
├── epub_converter.py    # EPUB转换核心模块
├── requirements.txt     # Python依赖包列表
├── README.md           # 项目说明文档
└── .gitignore          # Git忽略文件配置
```

## ⚠️ 注意事项

1. **网络要求**: Microsoft Edge TTS需要互联网连接
2. **文件格式**: 仅支持标准EPUB格式电子书
3. **版权说明**: 请确保您有权转换所使用的EPUB文件
4. **存储空间**: 音频文件较大，请确保有足够的磁盘空间

## 🐛 故障排除

### 常见问题

**Q: 程序启动后没有界面显示**
A: 检查Python版本和依赖包是否正确安装

**Q: 转换失败显示网络错误**  
A: 确保网络连接正常，可能需要配置代理

**Q: 某些章节转换失败**
A: 可能是章节内容格式问题，程序会跳过并继续转换其他章节

### 代理配置

如果您使用代理上网，可能需要配置环境变量：

```bash
set HTTP_PROXY=http://127.0.0.1:7890
set HTTPS_PROXY=http://127.0.0.1:7890
```

## 🤝 贡献

欢迎提交Issue和Pull Request来改进这个项目！

## 📄 许可证

本项目采用MIT许可证 - 查看[LICENSE](LICENSE)文件了解详情

## 📞 联系方式

如有问题或建议，请通过GitHub Issues联系我们。

---

⭐ 如果这个项目对您有帮助，请给它一个Star！
