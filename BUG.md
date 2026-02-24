# StreamLens 已知问题

## BUG-1: ROS pytest 插件污染 Conda 环境

- 现象：使用 `streamlens` conda 环境运行 pytest 时，系统级 ROS 2 Humble 的 pytest 插件（`launch_testing_ros`、`ament_*`、`colcon_core`）被自动加载，导致 `PluginValidationError` 或 `ModuleNotFoundError: No module named 'yaml'`
- 原因：系统 `PYTHONPATH` 包含 `/opt/ros/humble/lib/python3.10/site-packages`，conda 环境未完全隔离
- 解决方案：运行测试时设置环境变量隔离
  ```bash
  PYTHONNOUSERSITE=1 PYTHONPATH="" python -m pytest tests/ -v
  ```
- 状态：已解决（workaround）

## BUG-2: 真实 YouTube URL 提取超时

- 现象：调用 `extract_video_info()` 访问真实 YouTube URL 时，请求超过 120 秒无响应
- 原因：网络环境无法直接访问 YouTube（需要代理）
- 解决方案：已在 `extractor.py` 的 `_YDL_OPTS` 中添加 `"proxy": "http://127.0.0.1:7897"`，并在 MCP `env` 中配置 `http_proxy` / `https_proxy`
- 状态：已解决

## BUG-4: YouTube 反爬要求 cookie 验证

- 现象：代理配通后，yt-dlp 报 "Sign in to confirm you're not a bot"
- 原因：YouTube 对未登录/无 cookie 的请求触发人机验证
- 已尝试：`cookiesfrombrowser: ("edge",)` — Edge cookies 读取成功但未包含 YouTube 登录态
- 解决方案：
  1. 在 Edge 浏览器中登录 YouTube 账号，然后 yt-dlp 自动读取 cookie
  2. 或手动导出 cookies.txt 文件，配置 `"cookiefile": "/path/to/cookies.txt"`
- 状态：已解决（通过 `config.py` 支持环境变量配置 `STREAMLENS_COOKIE_SOURCE` 和 `STREAMLENS_COOKIE_FILE`）

## BUG-3: `~/.claude.json` 编辑竞争

- 现象：使用 Edit 工具修改 `~/.claude.json` 时反复报 `File has been modified since read`
- 原因：Claude Code 运行时会持续写入该文件（更新统计数据等），导致编辑竞争
- 解决方案：改用 Python 脚本原子性读写 JSON 文件
- 状态：已解决
