# StreamLens — YouTube 视频元数据 MCP 服务器

StreamLens 是一个基于 MCP 协议的工具服务器，通过 yt-dlp 提取 YouTube 视频元数据，可直接在 Claude Code 中调用。

## 功能

- 提取视频基本信息（标题、作者、时长、描述、缩略图等）
- 自动筛选三种格式：最高画质、最小体积、纯音频
- 10 分钟 TTL 缓存，避免重复请求
- 结构化 JSON 输出，适合 LLM 上下文消费

## 环境搭建

```bash
# 创建 Conda 环境
conda env create -f environment.yml

# 激活环境
conda activate streamlens

# 运行测试
PYTHONNOUSERSITE=1 PYTHONPATH="" python -m pytest tests/ -v
```

## MCP 配置

`~/.claude.json` 中已自动配置：

```json
{
  "streamlens": {
    "command": "/home/as/miniconda3/envs/streamlens/bin/python",
    "args": ["/home/as/StreamLens/video_mcp_server.py"],
    "env": {
      "PYTHONNOUSERSITE": "1",
      "PYTHONPATH": ""
    }
  }
}
```

重启 Claude Code 后，`streamlens` 工具即可使用。

## 配置

通过环境变量控制代理和 cookie 来源：

| 环境变量 | 说明 | 默认值 | 示例 |
|---------|------|--------|------|
| `STREAMLENS_PROXY` | 代理地址 | `""` (不使用代理) | `http://127.0.0.1:7897` |
| `STREAMLENS_COOKIE_SOURCE` | 浏览器 cookie 来源 | `""` (不使用 cookie) | `edge`, `chrome`, `firefox` |
| `STREAMLENS_COOKIE_FILE` | cookies.txt 文件路径 | `""` | `/path/to/cookies.txt` |

优先级：`STREAMLENS_COOKIE_FILE` > `STREAMLENS_COOKIE_SOURCE` > 不使用 cookie

常见场景：

- 服务器有浏览器：`STREAMLENS_COOKIE_SOURCE=edge`
- SSH 转发 + 本机导出 cookies.txt：`STREAMLENS_PROXY=http://127.0.0.1:7897 STREAMLENS_COOKIE_FILE=/path/to/cookies.txt`
- 无需代理无需 cookie（部分地区直连）：不设置任何变量

## 使用方法

在 Claude Code 中直接调用：

```
get_video_info("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
```

## 项目结构

```
video_mcp_server.py   # MCP 入口，工具注册
extractor.py          # yt-dlp 封装、异步桥接、格式筛选、缓存
models.py             # 不可变数据类（VideoFormat, VideoInfo）
validators.py         # URL 校验与视频 ID 提取
cache.py              # TTL 缓存（10 分钟过期）
tests/                # 单元测试
```

## 错误处理

| 错误类型 | 触发条件 | 异常类 |
|---------|---------|--------|
| 无效 URL | 正则不匹配 | `InvalidURLError` |
| 网络超时 | yt-dlp 30s 超时 | `ExtractionError` |
| 地区限制 | 错误信息含 "geo" | `GeoRestrictionError` |
| 视频不可用 | 私密/下架视频 | `VideoUnavailableError` |
