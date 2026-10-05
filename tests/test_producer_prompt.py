"""Keep the producer's sibling table aligned with the verified registry."""

from __future__ import annotations

from pathlib import Path

from ux_creator.sisters import SISTERS

PROMPT = Path(__file__).resolve().parents[1] / "plugins/ux/agents/ux-producer.md"


def test_producer_prompt_declares_task_tool_and_all_sister_agents() -> None:
    text = PROMPT.read_text(encoding="utf-8")
    frontmatter = text.split("---", 2)[1]
    assert "  - task_tool_set" in frontmatter
    for target, sister in SISTERS.items():
        agents = ", ".join(sister.agents)
        rows = [line for line in text.splitlines() if line.startswith(f"| {target} |")]
        assert len(rows) == 1
        cells = [cell.strip() for cell in rows[0].strip("|").split("|")]
        assert cells[1] == agents
        assert cells[2].casefold() == sister.delivers.casefold()
    assert "If task errors because the sister agent is not loaded" in text
    assert "ux_delegate" in text
    assert "ux_liaison_status" in text
