"""Format extracted video data as structured text for LLM consumption."""


def format_for_llm(data: dict, show_danmaku: bool = False) -> str:
    """Format video data as plain text for LLM analysis.

    Always includes: title, description, full subtitles.
    Danmaku is only included when show_danmaku=True.
    """
    lines = [
        f"[标题] {data['title']}",
        "",
        f"[简介] {data['description'] or '(无简介)'}",
        "",
    ]
    if data["subtitles"]:
        full_text = "".join(data["subtitles"])
        lines.append("[字幕内容]")
        lines.append(full_text)
        lines.append("")
    if show_danmaku and data["danmaku"]:
        lines.append(f"[弹幕内容 (共{len(data['danmaku'])}条)]")
        lines.append(" | ".join(data["danmaku"]))
        lines.append("")
    return "\n".join(lines)
