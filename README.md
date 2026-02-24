# StreamLens

基于 MCP 协议的视频信息提取工具，支持 YouTube / TikTok / 抖音，可直接在 Claude Code 中调用。

**核心能力：**
- 提取视频元数据、字幕、音频直链
- 支持 YouTube 关键词搜索与播放列表
- 批量并行提取（最多 10 个 URL）
- 通过 SSH 远程调用 Mac/Windows 上的浏览器 cookie
- 结构化 JSON 输出，适合 LLM 上下文消费

---

## 支持平台

| 平台 | 支持的 URL 格式 |
|------|----------------|
| YouTube | `youtube.com/watch?v=...`、`youtu.be/...`、`/shorts/...`、`/embed/...` |
| TikTok | `tiktok.com/@user/video/ID`、`vm.tiktok.com/CODE` |
| 抖音 | `douyin.com/video/ID`、`v.douyin.com/CODE` |

---

## 工具列表

### `get_video_info` — 视频元数据

提取视频基本信息，并自动筛选三种格式链接。

| 参数 | 类型 | 说明 |
|------|------|------|
| `url` | string | 视频 URL（YouTube / TikTok / 抖音） |

返回示例：
```json
{
  "video_id": "dQw4w9WgXcQ",
  "title": "Rick Astley - Never Gonna Give You Up",
  "uploader": "Rick Astley",
  "duration": 212,
  "best_format": { "url": "https://...", "ext": "mp4", "quality": "1080p" },
  "smallest_format": { "url": "https://...", "ext": "mp4", "quality": "360p" },
  "audio_format": { "url": "https://...", "ext": "m4a", "abr": 128 }
}
```

---

### `get_transcript` — 字幕 / 文字稿

提取视频字幕，优先使用手动字幕，不可用时自动回退到自动生成字幕。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `url` | string | — | 视频 URL |
| `lang` | string | `"en"` | 语言代码，如 `zh`、`ja`、`ko`、`es` |
| `format` | string | `"text"` | `"text"` 纯文本（适合摘要）/ `"segments"` 带时间戳（适合精确引用） |

返回示例（text 模式）：
```json
{
  "video_id": "dQw4w9WgXcQ",
  "language": "en",
  "is_auto_generated": false,
  "full_text": "We're no strangers to love..."
}
```

---

### `search_videos` — YouTube 搜索

按关键词搜索 YouTube 视频。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `query` | string | — | 搜索关键词 |
| `max_results` | int | `5` | 返回数量（1–20） |

返回示例：
```json
[
  {
    "video_id": "dQw4w9WgXcQ",
    "title": "Rick Astley - Never Gonna Give You Up",
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "duration": 212,
    "channel": "Rick Astley"
  }
]
```

---

### `get_audio_url` — 音频直链

提取视频的音频流直链 URL，无需下载。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `url` | string | — | 视频 URL |
| `quality` | string | `"best"` | `"best"` 最高码率 / `"smallest"` 最小体积 |

返回示例：
```json
{
  "url": "https://...",
  "ext": "m4a",
  "abr": 128,
  "filesize": 3407872
}
```

---

### `get_playlist_info` — 播放列表

提取 YouTube 播放列表元数据及视频列表。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `url` | string | — | YouTube 播放列表 URL |
| `max_videos` | int | `20` | 最多返回视频数（1–50） |

返回示例：
```json
{
  "title": "My Playlist",
  "channel": "SomeChannel",
  "video_count": 42,
  "videos": [{ "video_id": "...", "title": "..." }]
}
```

---

### `batch_get_info` — 批量提取

并行提取多个视频的元数据，支持部分成功（单个失败不影响其他）。

| 参数 | 类型 | 说明 |
|------|------|------|
| `urls` | list[string] | 视频 URL 列表（最多 10 个，支持混合平台） |

返回示例：
```json
{
  "total": 3,
  "succeeded": 2,
  "failed": 1,
  "results": [
    { "url": "https://...", "status": "ok", "data": { ... } },
    { "url": "https://...", "status": "error", "error": "VideoUnavailable" }
  ]
}
```

---

### `health_check` — 环境诊断

检查 yt-dlp 和 ffmpeg 是否可用。

无参数。返回示例：
```json
{
  "ytdlp_available": true,
  "ytdlp_version": "2024.11.18",
  "ffmpeg_available": true,
  "ffmpeg_path": "/usr/bin/ffmpeg",
  "ffmpeg_message": "ffmpeg is available"
}
```

---

## 安装与配置

### 环境搭建

```bash
conda env create -f environment.yml
conda activate streamlens

# 验证安装
PYTHONNOUSERSITE=1 PYTHONPATH="" python -m pytest tests/ -v
```

### MCP 注册（`~/.claude.json`）

在 `mcpServers` 块中添加：

```json
{
  "mcpServers": {
    "streamlens": {
      "command": "/home/as/miniconda3/envs/streamlens/bin/python",
      "args": ["/home/as/StreamLens/video_mcp_server.py"],
      "env": {
        "PYTHONNOUSERSITE": "1",
        "PYTHONPATH": "",
        "STREAMLENS_PROXY": "http://127.0.0.1:7897",
        "STREAMLENS_COOKIE_SOURCE": "chrome",
        "STREAMLENS_COOKIE_FILE": "",
        "STREAMLENS_SSH_HOST": "",
        "STREAMLENS_TIKTOK_PROXY": "",
        "STREAMLENS_TIKTOK_COOKIE_SOURCE": "",
        "STREAMLENS_TIKTOK_COOKIE_FILE": "",
        "STREAMLENS_TIKTOK_SSH_HOST": "",
        "STREAMLENS_DOUYIN_PROXY": "",
        "STREAMLENS_DOUYIN_COOKIE_SOURCE": "",
        "STREAMLENS_DOUYIN_COOKIE_FILE": "",
        "STREAMLENS_DOUYIN_SSH_HOST": ""
      }
    }
  }
}
```

配置完成后重启 Claude Code 即可使用。

### 环境变量说明

#### 全局变量

| 变量 | 说明 | 示例 |
|------|------|------|
| `STREAMLENS_PROXY` | 全局代理地址 | `http://127.0.0.1:7897` |
| `STREAMLENS_COOKIE_SOURCE` | 从浏览器读取 cookie | `chrome` / `edge` / `firefox` |
| `STREAMLENS_COOKIE_FILE` | Netscape 格式 cookies.txt 路径 | `/path/to/cookies.txt` |
| `STREAMLENS_SSH_HOST` | SSH 远程执行主机 | `user@192.168.1.10` |

#### TikTok 专用覆盖

| 变量 | 说明 |
|------|------|
| `STREAMLENS_TIKTOK_PROXY` | TikTok 专用代理 |
| `STREAMLENS_TIKTOK_COOKIE_SOURCE` | TikTok 专用浏览器 cookie |
| `STREAMLENS_TIKTOK_COOKIE_FILE` | TikTok 专用 cookies.txt |
| `STREAMLENS_TIKTOK_SSH_HOST` | TikTok 专用 SSH 主机 |

#### 抖音专用覆盖

| 变量 | 说明 |
|------|------|
| `STREAMLENS_DOUYIN_PROXY` | 抖音专用代理 |
| `STREAMLENS_DOUYIN_COOKIE_SOURCE` | 抖音专用浏览器 cookie |
| `STREAMLENS_DOUYIN_COOKIE_FILE` | 抖音专用 cookies.txt |
| `STREAMLENS_DOUYIN_SSH_HOST` | 抖音专用 SSH 主机 |

**优先级规则：**
- 平台专用变量 > 全局变量
- `COOKIE_FILE` > `COOKIE_SOURCE`（两者同时设置时，文件优先）

### 常见场景

| 场景 | 推荐配置 |
|------|---------|
| 本机有 Chrome（macOS/Windows） | `STREAMLENS_COOKIE_SOURCE=chrome` |
| Linux 服务器 + 代理直连 | `STREAMLENS_PROXY=http://127.0.0.1:7897` |
| Linux 服务器 + Mac 的浏览器 cookie | `STREAMLENS_SSH_HOST=user@mac-ip`（见下方 SSH 章节） |
| 手动导出 cookies.txt | `STREAMLENS_COOKIE_FILE=/path/to/cookies.txt` |
| TikTok 需要单独代理 | `STREAMLENS_TIKTOK_PROXY=http://...` |

---

## SSH 远程执行模式

### 为什么需要 SSH 模式

Linux 服务器通常没有图形界面浏览器，无法直接读取 cookie。SSH 模式让 StreamLens 在远程机器（如你的 Mac）上执行 yt-dlp，利用那台机器的浏览器 cookie，再将结果通过 SSH 管道传回。

### 配置步骤

**1. Mac 开启远程登录**

系统设置 → 通用 → 共享 → 开启「远程登录」

**2. 从 Linux 服务器配置免密登录**

```bash
# 在 Linux 服务器上生成密钥（如已有可跳过）
ssh-keygen -t ed25519

# 将公钥复制到 Mac
ssh-copy-id user@mac-ip

# 验证免密登录
ssh user@mac-ip "yt-dlp --version"
```

**3. 设置环境变量**

```json
"STREAMLENS_SSH_HOST": "user@mac-ip"
```

**4. 验证**

在 Claude Code 中调用 `health_check`，确认工具正常响应。

### SSH 模式工作原理

StreamLens 将 yt-dlp 命令序列化为 CLI 参数，通过 `ssh -o BatchMode=yes` 在远程主机执行，JSON 结果通过 stdout 管道传回本地解析。字幕提取时会在远程创建临时目录，提取完成后自动清理。

---

## 错误类型速查

| 错误类型 | 触发条件 | 处理建议 |
|---------|---------|---------|
| `InvalidURL` | URL 格式不匹配任何支持平台 | 检查 URL 是否完整、平台是否支持 |
| `GeoRestriction` | 视频有地区限制 | 配置代理 `STREAMLENS_PROXY` |
| `VideoUnavailable` | 视频私密、下架或需要登录 | 配置 cookie（`COOKIE_SOURCE` 或 `COOKIE_FILE`） |
| `ExtractionError` | yt-dlp 提取失败（网络超时等） | 检查网络连接或代理配置 |
| `SearchError` | YouTube 搜索失败 | 检查网络或代理 |
| `BatchError` | 批量/播放列表提取失败 | 检查 URL 格式，单个失败不影响其他 |
| `SSHError` | SSH 连接或远程执行失败 | 验证免密登录、检查远程 yt-dlp 是否安装 |
| `UnexpectedError` | 未预期异常 | 查看 message 字段获取详情 |

---

## 项目结构

```
video_mcp_server.py   # MCP 入口，7 个工具注册
extractor.py          # yt-dlp 封装、异步桥接、格式筛选、缓存
transcript.py         # 字幕提取与解析
search.py             # YouTube 搜索
batch.py              # 批量提取与播放列表
ssh.py                # SSH 远程执行模式
platforms.py          # 平台识别（YouTube / TikTok / 抖音）
validators.py         # URL 校验与视频 ID 提取
config.py             # 环境变量加载，支持平台专用覆盖
health.py             # yt-dlp / ffmpeg 环境检查
models.py             # 不可变数据类（VideoFormat, VideoInfo 等）
cache.py              # TTL 缓存（10 分钟过期）
tests/                # 单元测试（覆盖率 80%+）
environment.yml       # Conda 环境定义
```
