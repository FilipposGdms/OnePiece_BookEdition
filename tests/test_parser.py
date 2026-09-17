from app.parser import LongSummaryParseError, parse_long_summary


SAMPLE_HTML = """
<div class="mw-parser-output">
  <h2><span>Romance Dawn —The Dawn of the Adventure—</span></h2>
  <h2><span id="Chapter_Info">Chapter Info</span></h2>
  <p>Metadata that must not be returned.</p>
  <h2><span id="Short_Summary">Short Summary</span></h2>
  <p>This short summary must not be returned.</p>
  <h2><span id="Long_Summary">Long Summary</span></h2>
  <p>Gold Roger inspired the beginning of the Great Pirate Era.</p>
  <p>Twelve years later, Luffy meets the Red Hair Pirates.</p>
  <h3><span id="Nested">A nested heading</span></h3>
  <p>This paragraph is still part of the long summary.</p>
  <h2><span id="Quick_Reference">Quick Reference</span></h2>
  <p>This must not leak into the reader.</p>
</div>
"""


def test_extracts_only_long_summary_and_title() -> None:
    parsed = parse_long_summary(SAMPLE_HTML, 1)

    assert parsed.title == "Romance Dawn —The Dawn of the Adventure—"
    assert parsed.paragraphs == [
        "Gold Roger inspired the beginning of the Great Pirate Era.",
        "Twelve years later, Luffy meets the Red Hair Pirates.",
        "This paragraph is still part of the long summary.",
    ]


def test_missing_long_summary_raises() -> None:
    html = "<h2>Short Summary</h2><p>Only short text.</p>"

    try:
        parse_long_summary(html, 2)
    except LongSummaryParseError:
        pass
    else:
        raise AssertionError("Expected LongSummaryParseError")
