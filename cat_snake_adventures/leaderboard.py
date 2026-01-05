from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class LeaderboardEntry:
	player_name: str
	score: int
	level: int
	skin: str
	iso_time: str


def _leaderboard_path(saves_dir: Path) -> Path:
	return saves_dir / "leaderboard.json"


def load_entries(saves_dir: Path) -> list[LeaderboardEntry]:
	path = _leaderboard_path(saves_dir)
	if not path.exists():
		return []
	data = json.loads(path.read_text(encoding="utf-8"))
	entries: list[LeaderboardEntry] = []
	for item in data if isinstance(data, list) else []:
		if not isinstance(item, dict):
			continue
		try:
			entries.append(
				LeaderboardEntry(
					player_name=str(item.get("player_name", "Player")),
					score=int(item.get("score", 0)),
					level=int(item.get("level", 1)),
					skin=str(item.get("skin", "Classic")),
					iso_time=str(item.get("iso_time", "")),
				)
			)
		except Exception:
			continue
	return entries


def save_entries(saves_dir: Path, entries: list[LeaderboardEntry]) -> None:
	path = _leaderboard_path(saves_dir)
	path.write_text(json.dumps([asdict(e) for e in entries], indent=2), encoding="utf-8")


def add_entry(
	saves_dir: Path,
	*,
	player_name: str,
	score: int,
	level: int,
	skin: str,
	max_entries: int = 200,
) -> None:
	entries = load_entries(saves_dir)
	entries.append(
		LeaderboardEntry(
			player_name=player_name,
			score=int(score),
			level=int(level),
			skin=skin,
			iso_time=datetime.now().isoformat(timespec="seconds"),
		)
	)

	# Keep the file bounded (keep best scores first; stable enough for kids).
	entries.sort(key=lambda e: (e.score, e.level), reverse=True)
	entries = entries[: max(10, int(max_entries))]
	save_entries(saves_dir, entries)


def build_rows(entries: list[LeaderboardEntry]) -> list[tuple[str, int, int, str]]:
	# (name, score, level, skin)
	return [(e.player_name, e.score, e.level, e.skin) for e in entries]
