# Streamlens

B站视频内容提取与分析工具。提取视频元数据、字幕、弹幕，输出结构化文本供 LLM 分析。

## 功能

- 视频元数据提取（标题、简介、播放量等）
- 字幕提取：yt-dlp 优先获取平台字幕，失败时自动用 whisper 语音转写（支持 GPU 加速）
- 弹幕提取（XML 格式解析）

## 环境要求

- Python >= 3.10
- ffmpeg（whisper 依赖）
- NVIDIA GPU + CUDA（可选，加速 whisper 转写）

## 安装

```bash
cd Streamlens
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac

pip install -e .
# GPU 用户安装 CUDA 版 PyTorch：
pip install torch --index-url https://download.pytorch.org/whl/cu126
```

## 配置 B站 Cookies

yt-dlp 提取字幕需要登录态，按优先级支持三种方式：

### 方式一：cookies.txt 文件（推荐）

1. 安装浏览器扩展 "Get cookies.txt LOCALLY"
2. 登录 B站，用扩展导出 cookies
3. 保存为项目根目录下的 `cookies.txt`

也可通过环境变量指定路径：`BILIBILI_COOKIES_FILE=/path/to/cookies.txt`

### 方式二：SESSDATA

在项目根目录 `.env` 文件中写入：

```
BILIBILI_SESSDATA=你的SESSDATA值
```

或设置环境变量 `BILIBILI_SESSDATA`。

获取方式：浏览器 F12 → Application → Cookies → bilibili.com → 复制 SESSDATA 的值。

### 无 Cookies

不配置也能用，但 yt-dlp 无法获取字幕，会自动回退到 whisper 语音转写（较慢，质量略低）。

## 使用

```bash
# 基本用法
python -m streamlens.cli "https://www.bilibili.com/video/BVxxxxxx/"

# 附带弹幕
python -m streamlens.cli "https://www.bilibili.com/video/BVxxxxxx/" --danmaku
```

## 字幕提取流程

```
yt-dlp 提取平台字幕（需 cookies）
        │
        ├─ 成功 → 返回 SRT 解析结果
        │
        └─ 失败 → yt-dlp 下载音频 → whisper 转写（自动选择 GPU/CPU）
```

## 项目结构

```
Streamlens/
├── src/streamlens/
│   ├── cli.py              # CLI 入口
│   ├── analyzer.py         # LLM 格式化输出
│   └── extractors/
│       └── bilibili.py     # B站提取器
├── cookies.txt             # B站 cookies（不提交到 git）
├── .env                    # SESSDATA 配置（不提交到 git）
└── pyproject.toml
```
