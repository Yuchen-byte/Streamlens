"""Tests for transcript.py — SRT/VTT parsing and text extraction."""

from transcript import parse_subtitles, segments_to_text


class TestParseSubtitlesVTT:
    """VTT format parsing."""

    def test_basic_vtt(self):
        raw = (
            "WEBVTT\n"
            "\n"
            "00:00:01.000 --> 00:00:04.000\n"
            "Hello world\n"
            "\n"
            "00:00:04.000 --> 00:00:08.000\n"
            "This is a test\n"
        )
        segs = parse_subtitles(raw)
        assert len(segs) == 2
        assert segs[0] == {"start": 1.0, "end": 4.0, "text": "Hello world"}
        assert segs[1] == {"start": 4.0, "end": 8.0, "text": "This is a test"}

    def test_vtt_with_html_tags(self):
        raw = (
            "WEBVTT\n"
            "\n"
            "00:00:01.000 --> 00:00:04.000\n"
            "<c.colorE5E5E5>Hello</c> <c.colorCCCCCC>world</c>\n"
        )
        segs = parse_subtitles(raw)
        assert len(segs) == 1
        assert segs[0]["text"] == "Hello world"

    def test_vtt_with_timestamp_tags(self):
        raw = (
            "WEBVTT\n"
            "\n"
            "00:00:01.000 --> 00:00:04.000\n"
            "Hello <00:00:02.500>world\n"
        )
        segs = parse_subtitles(raw)
        assert segs[0]["text"] == "Hello world"

    def test_vtt_merges_duplicate_text(self):
        raw = (
            "WEBVTT\n"
            "\n"
            "00:00:01.000 --> 00:00:03.000\n"
            "Same line\n"
            "\n"
            "00:00:03.000 --> 00:00:05.000\n"
            "Same line\n"
            "\n"
            "00:00:05.000 --> 00:00:07.000\n"
            "Different line\n"
        )
        segs = parse_subtitles(raw)
        assert len(segs) == 2
        assert segs[0] == {"start": 1.0, "end": 5.0, "text": "Same line"}
        assert segs[1] == {"start": 5.0, "end": 7.0, "text": "Different line"}

    def test_vtt_with_header_metadata(self):
        raw = (
            "WEBVTT\n"
            "Kind: captions\n"
            "Language: en\n"
            "\n"
            "00:00:01.000 --> 00:00:04.000\n"
            "Hello\n"
        )
        segs = parse_subtitles(raw)
        assert len(segs) == 1
        assert segs[0]["text"] == "Hello"


class TestParseSubtitlesSRT:
    """SRT format parsing."""

    def test_basic_srt(self):
        raw = (
            "1\n"
            "00:00:01,000 --> 00:00:04,000\n"
            "Hello world\n"
            "\n"
            "2\n"
            "00:00:04,000 --> 00:00:08,000\n"
            "Second line\n"
        )
        segs = parse_subtitles(raw)
        assert len(segs) == 2
        assert segs[0] == {"start": 1.0, "end": 4.0, "text": "Hello world"}
        assert segs[1] == {"start": 4.0, "end": 8.0, "text": "Second line"}

    def test_srt_multiline_text(self):
        raw = (
            "1\n"
            "00:00:01,000 --> 00:00:04,000\n"
            "Line one\n"
            "Line two\n"
            "\n"
        )
        segs = parse_subtitles(raw)
        assert len(segs) == 1
        assert segs[0]["text"] == "Line one Line two"

    def test_srt_with_hours(self):
        raw = (
            "1\n"
            "01:30:00,000 --> 01:30:05,500\n"
            "Late in the video\n"
        )
        segs = parse_subtitles(raw)
        assert segs[0]["start"] == 5400.0
        assert segs[0]["end"] == 5405.5


class TestParseSubtitlesEdgeCases:
    """Edge cases and invalid input."""

    def test_empty_string(self):
        assert parse_subtitles("") == []

    def test_none_input(self):
        assert parse_subtitles(None) == []

    def test_no_subtitles_content(self):
        assert parse_subtitles("WEBVTT\n\n") == []

    def test_skips_empty_text_segments(self):
        raw = (
            "WEBVTT\n"
            "\n"
            "00:00:01.000 --> 00:00:02.000\n"
            "\n"
            "\n"
            "00:00:02.000 --> 00:00:03.000\n"
            "Actual text\n"
        )
        segs = parse_subtitles(raw)
        assert len(segs) == 1
        assert segs[0]["text"] == "Actual text"


class TestSegmentsToText:
    """Text concatenation from segments."""

    def test_basic_concatenation(self):
        segs = [
            {"start": 0, "end": 1, "text": "Hello"},
            {"start": 1, "end": 2, "text": "world"},
        ]
        assert segments_to_text(segs) == "Hello world"

    def test_custom_separator(self):
        segs = [
            {"start": 0, "end": 1, "text": "Hello"},
            {"start": 1, "end": 2, "text": "world"},
        ]
        assert segments_to_text(segs, separator="\n") == "Hello\nworld"

    def test_empty_segments(self):
        assert segments_to_text([]) == ""
