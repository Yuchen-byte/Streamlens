"""CLI entry point for Streamlens."""

import argparse
import asyncio
import io
import sys

from streamlens.analyzer import format_for_llm
from streamlens.extractors.bilibili import extract


async def run(url: str, danmaku: bool) -> None:
    try:
        data = await extract(url)
    except Exception as e:
        print(f"提取失败: {e}", file=sys.stderr)
        sys.exit(1)
    print(format_for_llm(data, show_danmaku=danmaku))


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Streamlens - 视频内容提取工具")
    parser.add_argument("url", help="视频链接")
    parser.add_argument(
        "--danmaku",
        action="store_true",
        help="附加弹幕内容",
    )
    args = parser.parse_args()
    asyncio.run(run(args.url, args.danmaku))


if __name__ == "__main__":
    main()
