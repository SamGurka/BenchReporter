"""Discord formatting for standout free agents."""

from __future__ import annotations

from typing import Any

from sleeper_discord_bot.messages.weekly_roundup import format_points


def format_free_agents_message(
    week: int,
    candidates: list[dict[str, Any]],
    projected: bool = False,
) -> str:
    title = f"Week {week} {'Projected ' if projected else ''}Standout Free Agents"
    lines = [f"**{title}**", ""]

    def append_candidate(candidate: dict[str, Any]) -> None:
        suffix = "/".join(part for part in [candidate["position"], candidate.get("team")] if part)
        label = f" — **{candidate['label']}**" if candidate.get("label") else ""
        context = (
            "preseason availability"
            if candidate.get("preseason")
            else f"{format_points(candidate['margin'])} over {candidate['position']} FA avg"
        )
        if candidate.get("prior_average") is not None:
            context += f"; prior avg {format_points(candidate['prior_average'])} ({candidate['prior_games']} games)"
        if candidate.get("injury_context"):
            affected_players = ", ".join(
                f"{injured['name']} ({injured['status']})" for injured in candidate["injury_context"]
            )
            context += f"; backing up {affected_players}"
        score = "" if candidate.get("preseason") else f": {format_points(candidate['points'])} {'projected ' if candidate.get('projected') else ''}pts,"
        lines.append(f"- **{candidate['name']}** ({suffix}){score} {context}{label}")

    positional = [candidate for candidate in candidates if candidate.get("report_section", "standout") == "standout"]
    proven = [candidate for candidate in candidates if candidate.get("report_section") == "proven"]
    injury = [candidate for candidate in candidates if candidate.get("report_section") == "injury"]
    if positional:
        lines.append("**Standout Free Agents**")
        for candidate in positional:
            append_candidate(candidate)
    if proven:
        if positional:
            lines.append("")
        lines.append("**Proven Free Agents**")
        for candidate in proven:
            append_candidate(candidate)
    if injury:
        if positional or proven:
            lines.append("")
        lines.append("**Injury Opportunities**")
        for candidate in injury:
            append_candidate(candidate)
    return "\n".join(lines)
