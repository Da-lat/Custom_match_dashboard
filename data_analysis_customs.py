from __future__ import annotations

import argparse
import json
import math
import os
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from html import escape
from itertools import combinations
from pathlib import Path
from typing import Callable, Iterable, Sequence
from zoneinfo import ZoneInfo


ROLE_ORDER = ("TOP", "JUNGLE", "MID", "BOT", "SUPP")
WEEKDAY_ORDER = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
LOCAL_TZ_NAME = "Europe/London"
LOCAL_TZ = ZoneInfo(LOCAL_TZ_NAME)
DEFAULT_INPUT = "match_history.json"
DEFAULT_OUTPUT = "index.html"
DEFAULT_MATCHES_API_URL = "http://193.123.187.108/v1/matches"
MATCHES_API_KEY_ENV = "MATCHES_API_KEY"
MIN_PLAYER_GAMES = 10
WINRATE_CHART_MIN_GAMES = 5
MIN_CHAMPION_GAMES = 5
MIN_COMBO_GAMES = 3
TARGET_BAN_MIN_GAMES = 3
TARGET_BAN_RELIABILITY_GAMES = 5
PRACTICE_PICK_MIN_GAMES = 2
PRACTICE_PICK_MAX_WINRATE = 0.45
PRACTICE_PICK_BASELINE_GAP = 0.05
PRACTICE_PICK_RELIABILITY_GAMES = 6
ROLE_RELIABILITY_GAMES = 8
GAME_SCORE_TARGET = 20
TEAM_COMBO_MIN_GAMES = {
    2: 10,
    3: 5,
    4: 3,
    5: 2,
}
MVP_WEIGHTS = {
    "Net Wins": 0.40,
    "KDA": 0.15,
    "Kill Participation": 0.20,
    "Champion Pool": 0.20,
    "Games": 0.05,
}
ROLE_SCORE_WEIGHTS = {
    "Role Net Wins": 0.15,
    "Role KDA": 0.10,
    "Role Kill Participation": 0.10,
    "Role Champion Pool": 0.05,
    "Role Games": 0.05,
    "Overall MVP": 0.55,
}
SPOTLIGHT_EXCLUDED_PLAYERS: set[str] = set()
ANONYMOUS_PLAYER_PREFIXES = ("anonymous", "anon")
MOST_CONTESTED_EXCLUDED_CHAMPIONS = {"qiyana"}
TEAM_TIERS = ("S", "A", "B", "C", "D", "F")
CHAMPION_ROSTER_VERSION = "16.10.1"
CHAMPION_ASSET_OVERRIDES = {
    "Bel'Veth": "Belveth",
    "Cho'Gath": "Chogath",
    "Fiddlesticks": "FiddleSticks",
    "Kai'Sa": "Kaisa",
    "Kha'Zix": "Khazix",
    "K'Sante": "KSante",
    "LeBlanc": "Leblanc",
    "Nunu & Willump": "Nunu",
    "Renata Glasc": "Renata",
    "Vel'Koz": "Velkoz",
    "Wukong": "MonkeyKing",
}
CHAMPION_ROSTER_SOURCE_URL = (
    f"https://ddragon.leagueoflegends.com/cdn/{CHAMPION_ROSTER_VERSION}/"
    "data/en_US/champion.json"
)
CHAMPION_ROSTER = (
    "Aatrox",
    "Ahri",
    "Akali",
    "Akshan",
    "Alistar",
    "Ambessa",
    "Amumu",
    "Anivia",
    "Annie",
    "Aphelios",
    "Ashe",
    "Aurelion Sol",
    "Aurora",
    "Azir",
    "Bard",
    "Bel'Veth",
    "Blitzcrank",
    "Brand",
    "Braum",
    "Briar",
    "Caitlyn",
    "Camille",
    "Cassiopeia",
    "Cho'Gath",
    "Corki",
    "Darius",
    "Diana",
    "Dr. Mundo",
    "Draven",
    "Ekko",
    "Elise",
    "Evelynn",
    "Ezreal",
    "Fiddlesticks",
    "Fiora",
    "Fizz",
    "Galio",
    "Gangplank",
    "Garen",
    "Gnar",
    "Gragas",
    "Graves",
    "Gwen",
    "Hecarim",
    "Heimerdinger",
    "Hwei",
    "Illaoi",
    "Irelia",
    "Ivern",
    "Janna",
    "Jarvan IV",
    "Jax",
    "Jayce",
    "Jhin",
    "Jinx",
    "K'Sante",
    "Kai'Sa",
    "Kalista",
    "Karma",
    "Karthus",
    "Kassadin",
    "Katarina",
    "Kayle",
    "Kayn",
    "Kennen",
    "Kha'Zix",
    "Kindred",
    "Kled",
    "Kog'Maw",
    "LeBlanc",
    "Lee Sin",
    "Leona",
    "Lillia",
    "Lissandra",
    "Lucian",
    "Lulu",
    "Lux",
    "Malphite",
    "Malzahar",
    "Maokai",
    "Master Yi",
    "Mel",
    "Milio",
    "Miss Fortune",
    "Mordekaiser",
    "Morgana",
    "Naafiri",
    "Nami",
    "Nasus",
    "Nautilus",
    "Neeko",
    "Nidalee",
    "Nilah",
    "Nocturne",
    "Nunu & Willump",
    "Olaf",
    "Orianna",
    "Ornn",
    "Pantheon",
    "Poppy",
    "Pyke",
    "Qiyana",
    "Quinn",
    "Rakan",
    "Rammus",
    "Rek'Sai",
    "Rell",
    "Renata Glasc",
    "Renekton",
    "Rengar",
    "Riven",
    "Rumble",
    "Ryze",
    "Samira",
    "Sejuani",
    "Senna",
    "Seraphine",
    "Sett",
    "Shaco",
    "Shen",
    "Shyvana",
    "Singed",
    "Sion",
    "Sivir",
    "Skarner",
    "Smolder",
    "Sona",
    "Soraka",
    "Swain",
    "Sylas",
    "Syndra",
    "Tahm Kench",
    "Taliyah",
    "Talon",
    "Taric",
    "Teemo",
    "Thresh",
    "Tristana",
    "Trundle",
    "Tryndamere",
    "Twisted Fate",
    "Twitch",
    "Udyr",
    "Urgot",
    "Varus",
    "Vayne",
    "Veigar",
    "Vel'Koz",
    "Vex",
    "Vi",
    "Viego",
    "Viktor",
    "Vladimir",
    "Volibear",
    "Warwick",
    "Wukong",
    "Xayah",
    "Xerath",
    "Xin Zhao",
    "Yasuo",
    "Yone",
    "Yorick",
    "Yunara",
    "Yuumi",
    "Zaahen",
    "Zac",
    "Zed",
    "Zeri",
    "Ziggs",
    "Zilean",
    "Zoe",
    "Zyra",
)


def teams_page_path(output_path: Path) -> Path:
    return output_path.with_name(f"{output_path.stem}_teams{output_path.suffix}")


def draft_coach_page_path(output_path: Path) -> Path:
    return output_path.with_name(f"{output_path.stem}_draft_coach{output_path.suffix}")


def showcases_page_path(output_path: Path) -> Path:
    return output_path.with_name(f"{output_path.stem}_showcases{output_path.suffix}")


def head_to_head_page_path(output_path: Path) -> Path:
    return output_path.with_name(f"{output_path.stem}_head_to_head{output_path.suffix}")


def experimental_page_path(output_path: Path) -> Path:
    return output_path.with_name(f"{output_path.stem}_experimental{output_path.suffix}")


@dataclass(frozen=True)
class Appearance:
    match_id: int
    timestamp: str
    date_label: str
    weekday_label: str
    side: str
    player: str
    name: str
    role: str
    champion: str
    kills: int
    deaths: int
    assists: int
    team_kills: int

    @property
    def win(self) -> int:
        return 1 if self.side == "win" else 0

    @property
    def result(self) -> str:
        return "Win" if self.win else "Loss"

    @property
    def takedowns(self) -> int:
        return self.kills + self.assists

    @property
    def kda_ratio(self) -> float:
        return self.takedowns / max(1, self.deaths)

    @property
    def kill_participation(self) -> float:
        return self.takedowns / self.team_kills if self.team_kills else 0.0


def parse_kda(raw: str) -> tuple[int, int, int]:
    parts = str(raw).strip().split("/")
    if len(parts) != 3:
        raise ValueError(f"Expected K/D/A, got {raw!r}")
    try:
        return int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError as exc:
        raise ValueError(f"Expected numeric K/D/A, got {raw!r}") from exc


def parse_datetime(raw: str | None) -> datetime | None:
    if not raw:
        return None
    value = raw.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def local_datetime(raw: str | None) -> datetime | None:
    parsed = parse_datetime(raw)
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        return parsed
    return parsed.astimezone(LOCAL_TZ)


def format_date(raw: str | None) -> str:
    parsed = local_datetime(raw)
    if parsed is None:
        return "Unknown date"
    return parsed.strftime("%d %b %Y")


def format_weekday(raw: str | None) -> str:
    parsed = local_datetime(raw)
    if parsed is None:
        return "Unknown"
    return parsed.strftime("%A")


def ordinal_day(day: int) -> str:
    if 10 <= day % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    return f"{day}{suffix}"


def format_refresh_timestamp(moment: datetime) -> str:
    local_moment = moment.astimezone(LOCAL_TZ)
    return (
        f"{local_moment.strftime('%A')} "
        f"{ordinal_day(local_moment.day)} "
        f"{local_moment.strftime('%H:%M')}"
    )


def load_matches_from_api(url: str, api_key: str) -> list[dict]:
    from urllib.error import HTTPError, URLError
    from urllib.request import Request, urlopen

    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "X-API-Key": api_key,
            "User-Agent": "custom-games-dashboard/1.0",
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=30) as response:
            payload = response.read().decode("utf-8")
    except HTTPError as exc:
        raise RuntimeError(f"API request failed with HTTP {exc.code}: {exc.reason}") from exc
    except URLError as exc:
        raise RuntimeError(f"API request failed: {exc.reason}") from exc

    data = json.loads(payload)
    if isinstance(data, dict) and isinstance(data.get("matches"), list):
        return data["matches"]
    if isinstance(data, list):
        return data
    raise ValueError("API response must be a match list or an object with a 'matches' list.")


def load_appearances(
    path: Path, *, api_url: str = "", api_key: str = ""
) -> tuple[list[dict], list[Appearance]]:
    if api_url:
        if not api_key:
            raise ValueError(
                f"{MATCHES_API_KEY_ENV} must be set when loading matches from the API."
            )
        matches = load_matches_from_api(api_url, api_key)
    else:
        with path.open("r", encoding="utf-8") as file:
            matches = json.load(file)

    appearances: list[Appearance] = []
    for match_id, match in enumerate(matches, start=1):
        timestamp = match.get("timestamp") or match.get("date") or ""
        date_label = format_date(timestamp)
        weekday_label = format_weekday(timestamp)
        for side in ("win", "lose"):
            players = match.get(side, [])
            if len(players) != 5:
                raise ValueError(
                    f"Match {match_id} has {len(players)} players on {side}, expected 5"
                )
            parsed_players = [
                (player_data, parse_kda(player_data.get("kda", "0/0/0")))
                for player_data in players
            ]
            team_kills = sum(kills for _player_data, (kills, _deaths, _assists) in parsed_players)
            for player_data, (kills, deaths, assists) in parsed_players:
                appearances.append(
                    Appearance(
                        match_id=match_id,
                        timestamp=timestamp,
                        date_label=date_label,
                        weekday_label=weekday_label,
                        side=side,
                        player=str(player_data.get("player", "")).strip() or "Unknown",
                        name=str(player_data.get("name", "")).strip() or "Unknown",
                        role=str(player_data.get("role", "")).strip().upper() or "UNKNOWN",
                        champion=str(player_data.get("champion", "")).strip()
                        or "Unknown",
                        kills=kills,
                        deaths=deaths,
                        assists=assists,
                        team_kills=team_kills,
                    )
                )
    return matches, appearances


def safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def signed_pct(value: float) -> str:
    sign = "+" if value >= 0 else ""
    return f"{sign}{value * 100:.1f}%"


def one_decimal(value: float) -> str:
    return f"{value:.1f}"


def two_decimal(value: float) -> str:
    return f"{value:.2f}"


def integer(value: float | int) -> str:
    return f"{int(value)}"


def signed_integer(value: float | int) -> str:
    number = int(value)
    sign = "+" if number >= 0 else ""
    return f"{sign}{number}"


def score(value: float | int) -> str:
    return f"{float(value):.1f}"


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def metric_bounds(rows: Sequence[dict[str, object]], key: str) -> tuple[float, float]:
    values = [float(row.get(key, 0)) for row in rows]
    if not values:
        return 0.0, 1.0
    return min(values), max(values)


def normalized_metric(
    value: float, low: float, high: float, *, invert: bool = False
) -> float:
    if high == low:
        normalized = 1.0
    else:
        normalized = (value - low) / (high - low)
    if invert:
        normalized = 1.0 - normalized
    return clamp(normalized)


def game_sample_score(games: int) -> float:
    return clamp((max(0, games) / GAME_SCORE_TARGET) ** 0.5)


def top_counter(counter: Counter, limit: int = 3) -> str:
    if not counter:
        return "-"
    return ", ".join(f"{name} ({count})" for name, count in counter.most_common(limit))


def full_counter(counter: Counter) -> str:
    if not counter:
        return "-"
    items = sorted(counter.items(), key=lambda item: (-item[1], str(item[0])))
    return ", ".join(f"{name} ({count})" for name, count in items)


def role_sort(role: str) -> int:
    try:
        return ROLE_ORDER.index(role)
    except ValueError:
        return len(ROLE_ORDER)


def role_fit_label(rank: int) -> str:
    if rank == 1:
        return "Primary"
    if rank == 2:
        return "Secondary"
    return {
        3: "Third choice",
        4: "Fourth choice",
        5: "Fifth choice",
    }.get(rank, f"Role #{rank}")


def role_fit_score(rank: int) -> float:
    return {
        1: 1.0,
        2: 0.55,
        3: 0.30,
        4: 0.14,
        5: 0.06,
    }.get(rank, 0.02)


@lru_cache(maxsize=None)
def champion_key(name: str) -> str:
    value = name.casefold().replace("&", "and")
    return "".join(character for character in value if character.isalnum())


def is_most_contested_excluded_champion(name: object) -> bool:
    return champion_key(str(name)) in MOST_CONTESTED_EXCLUDED_CHAMPIONS


@lru_cache(maxsize=None)
def champion_asset_id(name: str) -> str:
    if name in CHAMPION_ASSET_OVERRIDES:
        return CHAMPION_ASSET_OVERRIDES[name]
    return "".join(character for character in name if character.isalnum())


@lru_cache(maxsize=None)
def champion_icon_url(name: str) -> str:
    asset_id = champion_asset_id(name)
    return (
        f"https://ddragon.leagueoflegends.com/cdn/{CHAMPION_ROSTER_VERSION}/"
        f"img/champion/{asset_id}.png"
    )


def unplayed_champion_rows(appearances: Iterable[Appearance]) -> list[dict[str, object]]:
    played = {champion_key(appearance.champion) for appearance in appearances}
    return [
        {"champion": champion}
        for champion in sorted(CHAMPION_ROSTER)
        if champion_key(champion) not in played
    ]


def aggregate(
    appearances: Iterable[Appearance], keys: Sequence[str]
) -> list[dict[str, object]]:
    groups: dict[tuple[object, ...], dict[str, object]] = {}

    for appearance in appearances:
        key = tuple(getattr(appearance, key_name) for key_name in keys)
        group = groups.setdefault(
            key,
            {
                "games": 0,
                "wins": 0,
                "kills": 0,
                "deaths": 0,
                "assists": 0,
                "team_kills": 0,
                "kill_participation": 0.0,
                "champions": Counter(),
                "roles": Counter(),
                "summoners": Counter(),
                "matches": set(),
                "last_timestamp": "",
            },
        )
        group["games"] = int(group["games"]) + 1
        group["wins"] = int(group["wins"]) + appearance.win
        group["kills"] = int(group["kills"]) + appearance.kills
        group["deaths"] = int(group["deaths"]) + appearance.deaths
        group["assists"] = int(group["assists"]) + appearance.assists
        group["team_kills"] = int(group["team_kills"]) + appearance.team_kills
        group["kill_participation"] = (
            float(group["kill_participation"]) + appearance.kill_participation
        )
        group["champions"][appearance.champion] += 1
        group["roles"][appearance.role] += 1
        group["summoners"][appearance.player] += 1
        group["matches"].add(appearance.match_id)
        if appearance.timestamp > str(group["last_timestamp"]):
            group["last_timestamp"] = appearance.timestamp

    rows: list[dict[str, object]] = []
    for key_values, group in groups.items():
        row = {key_name: key_values[index] for index, key_name in enumerate(keys)}
        games = int(group["games"])
        wins = int(group["wins"])
        kills = int(group["kills"])
        deaths = int(group["deaths"])
        assists = int(group["assists"])
        team_kills = int(group["team_kills"])
        kill_participation = float(group["kill_participation"])
        unique_champions = len(group["champions"])
        row.update(
            {
                "games": games,
                "wins": wins,
                "losses": games - wins,
                "net_wins": wins - (games - wins),
                "winrate": safe_div(wins, games),
                "kills": kills,
                "deaths": deaths,
                "assists": assists,
                "team_kills": team_kills,
                "avg_kills": safe_div(kills, games),
                "avg_deaths": safe_div(deaths, games),
                "avg_assists": safe_div(assists, games),
                "avg_takedowns": safe_div(kills + assists, games),
                "kill_participation": safe_div(kill_participation, games),
                "kda_ratio": safe_div(kills + assists, max(1, deaths)),
                "unique_champions": unique_champions,
                "champion_pool_rate": safe_div(unique_champions, games),
                "unique_roles": len(group["roles"]),
                "most_played_champion": top_counter(group["champions"], 3),
                "top_roles": top_counter(group["roles"], 3),
                "summoners": top_counter(group["summoners"], 3),
                "last_timestamp": group["last_timestamp"],
            }
        )
        rows.append(row)
    return rows


def mvp_score_rows(player_rows: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    eligible_rows = qualify(
        without_spotlight_excluded_players(player_rows), MIN_PLAYER_GAMES
    )
    net_win_low, net_win_high = metric_bounds(eligible_rows, "net_wins")
    kda_low, kda_high = metric_bounds(eligible_rows, "kda_ratio")
    kp_low, kp_high = metric_bounds(eligible_rows, "kill_participation")
    rows = []
    for player in eligible_rows:
        winrate = float(player.get("winrate", 0))
        reliability = 1.0
        games = int(player.get("games", 0))
        winrate_score = clamp(winrate)
        net_win_score = normalized_metric(
            float(player.get("net_wins", 0)), net_win_low, net_win_high
        )
        kda_score = normalized_metric(float(player.get("kda_ratio", 0)), kda_low, kda_high)
        kill_participation_score = normalized_metric(
            float(player.get("kill_participation", 0)), kp_low, kp_high
        )
        champion_pool_score = float(player.get("champion_pool_rate", 0)) ** 0.5
        games_score = game_sample_score(games)
        total_score = 100 * (
            MVP_WEIGHTS["Net Wins"] * net_win_score
            + MVP_WEIGHTS["KDA"] * kda_score
            + MVP_WEIGHTS["Kill Participation"] * kill_participation_score
            + MVP_WEIGHTS["Champion Pool"] * champion_pool_score
            + MVP_WEIGHTS["Games"] * games_score
        )
        row = dict(player)
        row.update(
            {
                "mvp_score": total_score,
                "adjusted_winrate": winrate_score,
                "winrate_score": winrate_score,
                "net_win_score": net_win_score,
                "reliability": reliability,
                "kda_score": kda_score,
                "kill_participation_score": kill_participation_score,
                "champion_pool_score": champion_pool_score,
                "games_score": games_score,
            }
        )
        rows.append(row)
    rows.sort(
        key=lambda row: (
            -float(row["mvp_score"]),
            -int(row["net_wins"]),
            -int(row["games"]),
            str(row["name"]),
        )
    )
    for index, row in enumerate(rows, start=1):
        row["mvp_rank"] = index
    return rows


def player_role_score_rows(
    player_rows: Sequence[dict[str, object]],
    player_role_rows: Sequence[dict[str, object]],
    mvp_rows: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    eligible_role_rows = without_spotlight_excluded_players(player_role_rows)
    mvp_by_name = {str(row["name"]): row for row in mvp_rows}
    role_rows_by_player: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in eligible_role_rows:
        role = str(row.get("role", ""))
        if role in ROLE_ORDER:
            role_rows_by_player[str(row.get("name", ""))].append(row)
    role_rank_by_player_role: dict[tuple[str, str], int] = {}
    for name, rows in role_rows_by_player.items():
        ranked_rows = sorted(
            rows,
            key=lambda row: (
                -int(row.get("games", 0)),
                -float(row.get("winrate", 0)),
                -int(row.get("net_wins", 0)),
                role_sort(str(row.get("role", ""))),
            ),
        )
        for rank, row in enumerate(ranked_rows, start=1):
            role_rank_by_player_role[(name, str(row.get("role", "")))] = rank

    net_win_low, net_win_high = metric_bounds(eligible_role_rows, "net_wins")
    kda_low, kda_high = metric_bounds(eligible_role_rows, "kda_ratio")
    kp_low, kp_high = metric_bounds(eligible_role_rows, "kill_participation")
    rows = []
    for role_row in eligible_role_rows:
        role = str(role_row.get("role", ""))
        if role not in ROLE_ORDER:
            continue
        name = str(role_row["name"])
        games = int(role_row.get("games", 0))
        winrate = float(role_row.get("winrate", 0))
        reliability = clamp(games / ROLE_RELIABILITY_GAMES)
        adjusted_winrate = 0.5 + ((winrate - 0.5) * reliability)
        role_net_win_score = normalized_metric(
            float(role_row.get("net_wins", 0)), net_win_low, net_win_high
        )
        role_kda_raw_score = normalized_metric(
            float(role_row.get("kda_ratio", 0)), kda_low, kda_high
        )
        role_kda_score = 0.5 + ((role_kda_raw_score - 0.5) * reliability)
        role_kp_raw_score = normalized_metric(
            float(role_row.get("kill_participation", 0)), kp_low, kp_high
        )
        role_kp_score = 0.5 + ((role_kp_raw_score - 0.5) * reliability)
        role_pool_score = (
            float(role_row.get("champion_pool_rate", 0)) * reliability
        ) ** 0.5
        role_games_score = game_sample_score(games)
        role_rank = role_rank_by_player_role.get((name, role), len(ROLE_ORDER))
        role_fit_component = role_fit_score(role_rank)
        overall_mvp_score = safe_div(
            float(mvp_by_name.get(name, {}).get("mvp_score", 0)), 100
        )
        role_score = 100 * (
            ROLE_SCORE_WEIGHTS["Role Net Wins"] * role_net_win_score
            + ROLE_SCORE_WEIGHTS["Role KDA"] * role_kda_score
            + ROLE_SCORE_WEIGHTS["Role Kill Participation"] * role_kp_score
            + ROLE_SCORE_WEIGHTS["Role Champion Pool"] * role_pool_score
            + ROLE_SCORE_WEIGHTS["Role Games"] * role_games_score
            + ROLE_SCORE_WEIGHTS["Overall MVP"] * overall_mvp_score
        )
        row = dict(role_row)
        row.update(
            {
                "role_score": role_score,
                "adjusted_winrate": adjusted_winrate,
                "role_net_win_score": role_net_win_score,
                "reliability": reliability,
                "role_kda_score": role_kda_score,
                "role_kp_score": role_kp_score,
                "role_pool_score": role_pool_score,
                "role_games_score": role_games_score,
                "role_fit": role_fit_label(role_rank),
                "role_rank": role_rank,
                "role_fit_score": role_fit_component,
                "overall_mvp_score": overall_mvp_score,
            }
        )
        rows.append(row)
    return sorted(
        rows,
        key=lambda row: (
            role_sort(str(row["role"])),
            -float(row["role_score"]),
            int(row["role_rank"]),
            -int(row["games"]),
            str(row["name"]),
        ),
    )


def build_tiered_teams(
    player_rows: Sequence[dict[str, object]],
    role_score_rows: Sequence[dict[str, object]],
) -> tuple[list[dict[str, object]], list[str]]:
    all_players = {
        str(row["name"]) for row in without_spotlight_excluded_players(player_rows)
    }
    candidates_by_role = {
        role: sorted(
            [row for row in role_score_rows if str(row["role"]) == role],
            key=lambda row: (
                -float(row["role_score"]),
                int(row.get("role_rank", len(ROLE_ORDER))),
                -int(row["games"]),
                str(row["name"]),
            ),
        )
        for role in ROLE_ORDER
    }
    max_teams = len(all_players) // len(ROLE_ORDER)

    def assignment_for_team_count(
        team_count: int,
    ) -> list[tuple[str, dict[str, object]]] | None:
        if any(len(candidates_by_role[role]) < team_count for role in ROLE_ORDER):
            return None
        player_names = sorted(all_players)
        player_index = {name: index for index, name in enumerate(player_names)}
        source = 0
        player_start = 1
        role_start = player_start + len(player_names)
        sink = role_start + len(ROLE_ORDER)
        graph: list[list[dict[str, object]]] = [[] for _ in range(sink + 1)]

        def add_edge(
            from_node: int,
            to_node: int,
            capacity: int,
            cost: int,
            payload: tuple[str, str, dict[str, object]] | None = None,
        ) -> None:
            forward = {
                "to": to_node,
                "rev": len(graph[to_node]),
                "cap": capacity,
                "cost": cost,
                "payload": payload,
                "original": capacity,
            }
            backward = {
                "to": from_node,
                "rev": len(graph[from_node]),
                "cap": 0,
                "cost": -cost,
                "payload": None,
                "original": 0,
            }
            graph[from_node].append(forward)
            graph[to_node].append(backward)

        for name in player_names:
            add_edge(source, player_start + player_index[name], 1, 0)
        for role_index, role in enumerate(ROLE_ORDER):
            add_edge(role_start + role_index, sink, team_count, 0)
            for row in candidates_by_role[role]:
                name = str(row["name"])
                if name not in player_index:
                    continue
                player_node = player_start + player_index[name]
                role_node = role_start + role_index
                role_score = float(row["role_score"])
                role_games = int(row["games"])
                role_rank = int(row.get("role_rank", len(ROLE_ORDER)))
                fit_component = float(row.get("role_fit_score", role_fit_score(role_rank)))
                cost = -round(
                    (role_score * 100_000)
                    + (fit_component * 1_000)
                    + (role_games * 10)
                    + (float(row.get("winrate", 0)) * 10)
                )
                add_edge(player_node, role_node, 1, cost, (role, name, row))

        required_flow = team_count * len(ROLE_ORDER)
        flow = 0
        while flow < required_flow:
            distance = [float("inf")] * len(graph)
            in_queue = [False] * len(graph)
            previous_node = [-1] * len(graph)
            previous_edge = [-1] * len(graph)
            distance[source] = 0
            queue = [source]
            in_queue[source] = True
            while queue:
                node = queue.pop(0)
                in_queue[node] = False
                for edge_index, edge in enumerate(graph[node]):
                    if int(edge["cap"]) <= 0:
                        continue
                    next_node = int(edge["to"])
                    next_distance = distance[node] + int(edge["cost"])
                    if next_distance < distance[next_node]:
                        distance[next_node] = next_distance
                        previous_node[next_node] = node
                        previous_edge[next_node] = edge_index
                        if not in_queue[next_node]:
                            queue.append(next_node)
                            in_queue[next_node] = True
            if previous_node[sink] == -1:
                break
            node = sink
            while node != source:
                parent = previous_node[node]
                edge_index = previous_edge[node]
                edge = graph[parent][edge_index]
                edge["cap"] = int(edge["cap"]) - 1
                reverse = graph[int(edge["to"])][int(edge["rev"])]
                reverse["cap"] = int(reverse["cap"]) + 1
                node = parent
            flow += 1

        if flow < required_flow:
            return None

        assignment = []
        for player_node in range(player_start, role_start):
            for edge in graph[player_node]:
                payload = edge.get("payload")
                if payload is None:
                    continue
                if int(edge["original"]) - int(edge["cap"]) <= 0:
                    continue
                role, _name, row = payload
                assignment.append((str(role), row))
        return assignment

    selected_assignment: list[tuple[str, dict[str, object]]] | None = None
    selected_team_count = 0
    for team_count in range(max_teams, 0, -1):
        selected_assignment = assignment_for_team_count(team_count)
        if selected_assignment:
            selected_team_count = team_count
            break
    if not selected_assignment:
        return [], sorted(all_players)

    selected_names = {str(row["name"]) for _role, row in selected_assignment}
    by_role: dict[str, list[dict[str, object]]] = {role: [] for role in ROLE_ORDER}
    for role, row in selected_assignment:
        by_role[role].append(row)
    for rows in by_role.values():
        rows.sort(
            key=lambda row: (
                -float(row["role_score"]),
                int(row.get("role_rank", len(ROLE_ORDER))),
                -int(row["games"]),
                str(row["name"]),
            )
        )

    teams = []
    for team_index in range(selected_team_count):
        assignments = []
        for role in ROLE_ORDER:
            row = by_role[role][team_index]
            assignments.append(
                {
                    "role": role,
                    "name": str(row["name"]),
                    "score": float(row["role_score"]),
                    "games": int(row["games"]),
                    "winrate": float(row["winrate"]),
                    "net_wins": int(row["net_wins"]),
                    "fit": str(row.get("role_fit", "")),
                    "role_rank": int(row.get("role_rank", len(ROLE_ORDER))),
                    "champions": str(row.get("most_played_champion", "-")),
                }
            )
        teams.append(
            {
                "tier": TEAM_TIERS[min(team_index, len(TEAM_TIERS) - 1)],
                "score": sum(float(row["score"]) for row in assignments)
                / len(assignments),
                "assignments": assignments,
            }
        )
    return teams, sorted(all_players - selected_names)


def meta_tier_label(value: float) -> str:
    if value >= 70:
        return "S"
    if value >= 60:
        return "A"
    if value >= 50:
        return "B"
    if value >= 40:
        return "C"
    if value >= 30:
        return "D"
    if value >= 20:
        return "E"
    return "F"


def format_meta_pilot(row: dict[str, object] | None) -> str:
    if not row:
        return "-"
    return (
        f"{row.get('name', '-')} "
        f"({pct(float(row.get('winrate', 0)))}, {integer(row.get('games', 0))}g)"
    )


def custom_meta_tier_rows(
    champion_role_rows: Sequence[dict[str, object]],
    player_champion_role_rows: Sequence[dict[str, object]],
    *,
    minimum_games: int = 2,
) -> list[dict[str, object]]:
    visible_player_combo_rows = without_spotlight_excluded_players(player_champion_role_rows)
    pilot_rows_by_pair: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in visible_player_combo_rows:
        role = str(row.get("role", ""))
        if role in ROLE_ORDER:
            pilot_rows_by_pair[(str(row.get("champion", "")), role)].append(row)

    visible_champion_role_rows = [
        row
        for row in champion_role_rows
        if str(row.get("role", "")) in ROLE_ORDER
        and int(row.get("games", 0)) >= minimum_games
    ]
    max_games_by_role: dict[str, int] = defaultdict(int)
    max_pilots_by_role: dict[str, int] = defaultdict(int)
    for row in visible_champion_role_rows:
        role = str(row.get("role", ""))
        games = int(row.get("games", 0))
        pilots = len(pilot_rows_by_pair.get((str(row.get("champion", "")), role), []))
        max_games_by_role[role] = max(max_games_by_role[role], games)
        max_pilots_by_role[role] = max(max_pilots_by_role[role], pilots)

    kda_low, kda_high = metric_bounds(visible_champion_role_rows, "kda_ratio")
    rows = []
    for row in visible_champion_role_rows:
        champion = str(row.get("champion", ""))
        role = str(row.get("role", ""))
        games = int(row.get("games", 0))
        winrate = float(row.get("winrate", 0))
        reliability = clamp(games / 8)
        adjusted_winrate = 0.5 + ((winrate - 0.5) * reliability)
        pilots = pilot_rows_by_pair.get((champion, role), [])
        unique_players = len(pilots)
        presence_score = (
            0.65 * safe_div(games, max_games_by_role[role])
            + 0.35 * safe_div(unique_players, max_pilots_by_role[role])
        )
        kda_score = normalized_metric(float(row.get("kda_ratio", 0)), kda_low, kda_high)
        contested_score = 100 * (
            (0.45 * presence_score)
            + (0.35 * adjusted_winrate)
            + (0.20 * kda_score)
        )

        pilot_pool = [pilot for pilot in pilots if int(pilot.get("games", 0)) >= 2] or list(pilots)
        best_pilot = find_first(
            sorted(
                pilot_pool,
                key=lambda pilot: (
                    -float(pilot.get("winrate", 0)),
                    -int(pilot.get("wins", 0)),
                    -float(pilot.get("kda_ratio", 0)),
                    -int(pilot.get("games", 0)),
                    str(pilot.get("name", "")),
                ),
            )
        )
        worst_pilot = (
            find_first(
                sorted(
                    pilot_pool,
                    key=lambda pilot: (
                        float(pilot.get("winrate", 0)),
                        -int(pilot.get("losses", 0)),
                        -int(pilot.get("games", 0)),
                        str(pilot.get("name", "")),
                    ),
                )
            )
            if len(pilot_pool) > 1
            else {}
        )
        output_row = dict(row)
        output_row.update(
            {
                "tier": meta_tier_label(contested_score),
                "unique_players": unique_players,
                "presence_score": presence_score,
                "adjusted_winrate": adjusted_winrate,
                "contested_score": contested_score,
                "best_pilot": format_meta_pilot(best_pilot),
                "worst_pilot": format_meta_pilot(worst_pilot),
            }
        )
        rows.append(output_row)
    return sorted(
        rows,
        key=lambda row: (
            role_sort(str(row.get("role", ""))),
            -float(row.get("contested_score", 0)),
            -int(row.get("games", 0)),
            str(row.get("champion", "")),
        ),
    )


def population_std(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return variance ** 0.5


def fingerprint_score_label(value: float) -> str:
    return score(value * 100)


def player_fingerprint_rows(
    appearances: Sequence[Appearance],
    player_rows: Sequence[dict[str, object]],
    player_champion_role_rows: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    visible_player_rows = without_spotlight_excluded_players(player_rows)
    visible_combo_rows = without_spotlight_excluded_players(player_champion_role_rows)
    appearances_by_player: dict[str, list[Appearance]] = defaultdict(list)
    for appearance in appearances:
        if not is_spotlight_excluded_player(appearance.name):
            appearances_by_player[appearance.name].append(appearance)

    kills_low, kills_high = metric_bounds(visible_player_rows, "avg_kills")
    kda_low, kda_high = metric_bounds(visible_player_rows, "kda_ratio")
    kp_low, kp_high = metric_bounds(visible_player_rows, "kill_participation")
    deaths_low, deaths_high = metric_bounds(visible_player_rows, "avg_deaths")
    combo_kda_low, combo_kda_high = metric_bounds(visible_combo_rows, "kda_ratio")

    combos_by_player: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in visible_combo_rows:
        combos_by_player[str(row.get("name", ""))].append(row)

    rows = []
    for player in visible_player_rows:
        name = str(player.get("name", ""))
        games = int(player.get("games", 0))
        carry_score = (
            0.5 * normalized_metric(float(player.get("avg_kills", 0)), kills_low, kills_high)
            + 0.5 * normalized_metric(float(player.get("kda_ratio", 0)), kda_low, kda_high)
        )
        teamfight_score = normalized_metric(
            float(player.get("kill_participation", 0)), kp_low, kp_high
        )
        survivability_score = normalized_metric(
            float(player.get("avg_deaths", 0)), deaths_low, deaths_high, invert=True
        )
        versatility_score = (
            0.75 * (float(player.get("champion_pool_rate", 0)) ** 0.5)
            + 0.25 * safe_div(float(player.get("unique_roles", 0)), len(ROLE_ORDER))
        )

        player_appearances = appearances_by_player.get(name, [])
        kp_values = [appearance.kill_participation for appearance in player_appearances]
        consistency_score = 1.0 - clamp(population_std(kp_values) / 0.25)
        reliability_score = (
            0.65 * game_sample_score(games)
            + 0.35 * consistency_score
        )

        player_combos = combos_by_player.get(name, [])
        combo_pool = [
            combo for combo in player_combos if int(combo.get("games", 0)) >= 2
        ] or list(player_combos)
        best_combo: dict[str, object] = {}
        best_combo_score = 0.0
        for combo in combo_pool:
            combo_games = int(combo.get("games", 0))
            combo_reliability = clamp(combo_games / 6)
            combo_adjusted_winrate = 0.5 + (
                (float(combo.get("winrate", 0)) - 0.5) * combo_reliability
            )
            combo_score = 100 * (
                0.50 * combo_adjusted_winrate
                + 0.30
                * normalized_metric(
                    float(combo.get("kda_ratio", 0)), combo_kda_low, combo_kda_high
                )
                + 0.20 * game_sample_score(combo_games)
            )
            if combo_score > best_combo_score:
                best_combo_score = combo_score
                best_combo = combo
        comfort_score = safe_div(best_combo_score, 100)
        comfort_label = (
            f"{best_combo.get('champion', '-')} {best_combo.get('role', '-')}"
            f" ({integer(best_combo.get('games', 0))}g, {pct(float(best_combo.get('winrate', 0)))})"
            if best_combo
            else "-"
        )

        fingerprint_score = (
            carry_score
            + teamfight_score
            + survivability_score
            + versatility_score
            + reliability_score
            + comfort_score
        ) / 6
        rows.append(
            {
                "name": name,
                "games": games,
                "fingerprint_score": fingerprint_score,
                "carry_score": carry_score,
                "teamfight_score": teamfight_score,
                "survivability_score": survivability_score,
                "versatility_score": versatility_score,
                "reliability_score": reliability_score,
                "comfort_score": comfort_score,
                "comfort_label": comfort_label,
                "search_text": (
                    f"{name} {player.get('most_played_champion', '')} "
                    f"{player.get('top_roles', '')} {comfort_label}"
                ),
            }
        )
    return sorted(
        rows,
        key=lambda row: (
            -float(row.get("fingerprint_score", 0)),
            -int(row.get("games", 0)),
            str(row.get("name", "")),
        ),
    )


def recent_form_rows(
    appearances: Sequence[Appearance],
    player_rows: Sequence[dict[str, object]],
    mvp_rows: Sequence[dict[str, object]],
    *,
    limit: int = 10,
) -> list[dict[str, object]]:
    visible_players = without_spotlight_excluded_players(player_rows)
    player_by_name = {str(row.get("name", "")): row for row in visible_players}
    mvp_by_name = {str(row.get("name", "")): row for row in mvp_rows}
    records_by_name: dict[str, list[Appearance]] = defaultdict(list)
    for appearance in appearances:
        if appearance.name in player_by_name and not is_spotlight_excluded_player(appearance.name):
            records_by_name[appearance.name].append(appearance)
    for records in records_by_name.values():
        records.sort(key=lambda row: (row.timestamp, row.match_id))

    raw_rows = []
    for name, player in player_by_name.items():
        records = records_by_name.get(name, [])
        recent = records[-limit:]
        if not recent:
            continue
        wins = sum(row.win for row in recent)
        losses = len(recent) - wins
        kills = sum(row.kills for row in recent)
        deaths = sum(row.deaths for row in recent)
        assists = sum(row.assists for row in recent)
        recent_kda = safe_div(kills + assists, max(1, deaths))
        recent_kp = safe_div(sum(row.kill_participation for row in recent), len(recent))
        recent_winrate = safe_div(wins, len(recent))
        streaks = player_streaks(records)
        active_result = str(streaks.get("active_result", ""))
        active_length = int(streaks.get("active_length", 0))
        raw_rows.append(
            {
                "name": name,
                "games": int(player.get("games", 0)),
                "recent_games": len(recent),
                "recent_wins": wins,
                "recent_losses": losses,
                "recent_record": f"{wins}-{losses}",
                "recent_winrate": recent_winrate,
                "overall_winrate": float(player.get("winrate", 0)),
                "recent_kda": recent_kda,
                "overall_kda": float(player.get("kda_ratio", 0)),
                "recent_kp": recent_kp,
                "active_result": active_result,
                "active_length": active_length,
                "streak_label": (
                    f"{active_length} {active_result.lower()} streak"
                    if active_length
                    else "No streak"
                ),
                "season_score": float(
                    mvp_by_name.get(name, {}).get(
                        "mvp_score", float(player.get("winrate", 0.5)) * 100
                    )
                ),
                "timeline": [
                    {
                        "match_id": row.match_id,
                        "result": row.result,
                        "champion": row.champion,
                        "role": row.role,
                        "kda": f"{row.kills}/{row.deaths}/{row.assists}",
                    }
                    for row in recent
                ],
                "search_text": (
                    f"{name} {player.get('most_played_champion', '')} "
                    f"{player.get('top_roles', '')}"
                ),
            }
        )

    kda_low, kda_high = metric_bounds(raw_rows, "recent_kda")
    kp_low, kp_high = metric_bounds(raw_rows, "recent_kp")
    rows = []
    for row in raw_rows:
        active_result = str(row.get("active_result", ""))
        active_length = int(row.get("active_length", 0))
        streak_score = 0.5
        if active_result == "Win":
            streak_score = 0.5 + clamp(active_length / 6) * 0.5
        elif active_result == "Loss":
            streak_score = 0.5 - clamp(active_length / 6) * 0.5
        sample_score = clamp(int(row.get("recent_games", 0)) / limit)
        recent_score = 100 * (
            0.35 * float(row.get("recent_winrate", 0))
            + 0.25
            * normalized_metric(float(row.get("recent_kda", 0)), kda_low, kda_high)
            + 0.20
            * normalized_metric(float(row.get("recent_kp", 0)), kp_low, kp_high)
            + 0.10 * streak_score
            + 0.10 * sample_score
        )
        movement = recent_score - float(row.get("season_score", 0))
        if int(row.get("recent_games", 0)) < 4:
            status = "Small Sample"
        elif movement >= 8:
            status = "Heating Up"
        elif movement <= -8:
            status = "Cooling Down"
        elif float(row.get("recent_winrate", 0)) >= 0.7:
            status = "Hot Form"
        elif float(row.get("recent_winrate", 0)) <= 0.3:
            status = "Cold Spell"
        else:
            status = "Stable"
        updated = dict(row)
        updated.update(
            {
                "recent_score": recent_score,
                "mvp_movement": movement,
                "status": status,
            }
        )
        rows.append(updated)
    return sorted(
        rows,
        key=lambda row: (
            -float(row.get("recent_score", 0)),
            -int(row.get("recent_games", 0)),
            str(row.get("name", "")),
        ),
    )


def appearance_match_label(appearance: Appearance) -> str:
    return f"Match {appearance.match_id} - {appearance.weekday_label} {appearance.date_label}"


def appearance_kda_line(appearance: Appearance) -> str:
    return f"{appearance.kills}/{appearance.deaths}/{appearance.assists}"


def experimental_hall_rows(
    appearances: Sequence[Appearance],
    champion_rows: Sequence[dict[str, object]],
    player_role_rows: Sequence[dict[str, object]],
    player_champion_rows: Sequence[dict[str, object]],
    player_champion_role_rows: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    rows = [
        appearance
        for appearance in appearances
        if not is_spotlight_excluded_player(appearance.name)
    ]
    hall_rows: list[dict[str, object]] = []

    def add_appearance_award(
        *,
        title: str,
        appearance: Appearance,
        stat: str,
        detail: str,
        theme: str,
        badge: str,
    ) -> None:
        hall_rows.append(
            {
                "title": title,
                "winner": f"{appearance.name} on {appearance.champion}",
                "stat": stat,
                "detail": f"{appearance_match_label(appearance)}. {detail}",
                "champion": appearance.champion,
                "match_id": appearance.match_id,
                "theme": theme,
                "badge": badge,
            }
        )

    if rows:
        best_kda = max(
            rows,
            key=lambda row: (
                row.kda_ratio,
                row.takedowns,
                row.kills,
                row.kill_participation,
                -row.deaths,
            ),
        )
        add_appearance_award(
            title="Best Single-Game KDA",
            appearance=best_kda,
            stat=f"{appearance_kda_line(best_kda)} ({two_decimal(best_kda.kda_ratio)} KDA)",
            detail=f"{pct(best_kda.kill_participation)} KP.",
            theme="gold",
            badge="KDA",
        )

        loss_rows = [row for row in rows if not row.win]
        if loss_rows:
            tragic = max(
                loss_rows,
                key=lambda row: (
                    row.kda_ratio * 7
                    + row.kill_participation * 45
                    + row.kills * 2.2
                    + row.assists
                    - row.deaths * 1.4,
                    row.takedowns,
                ),
            )
            add_appearance_award(
                title="Most Tragic Loss Performance",
                appearance=tragic,
                stat=f"{appearance_kda_line(tragic)} in a loss",
                detail=f"{pct(tragic.kill_participation)} KP and {tragic.takedowns} takedowns.",
                theme="red",
                badge="LOSS",
            )
            kp_loss = max(loss_rows, key=lambda row: (row.kill_participation, row.takedowns))
            add_appearance_award(
                title="Highest Kill Participation Loss",
                appearance=kp_loss,
                stat=f"{pct(kp_loss.kill_participation)} KP",
                detail=f"{appearance_kda_line(kp_loss)} with {kp_loss.team_kills} team kills.",
                theme="purple",
                badge="KP",
            )

        win_rows = [row for row in rows if row.win]
        if win_rows:
            carry = max(
                win_rows,
                key=lambda row: (
                    row.kill_participation * 55
                    + row.kills * 4
                    + row.assists * 1.8
                    + row.kda_ratio * 3,
                    row.takedowns,
                ),
            )
            add_appearance_award(
                title="Biggest Carry Win",
                appearance=carry,
                stat=f"{appearance_kda_line(carry)} win",
                detail=f"{pct(carry.kill_participation)} KP on {carry.team_kills} team kills.",
                theme="green",
                badge="WIN",
            )
            death_win = max(
                win_rows,
                key=lambda row: (row.deaths, row.takedowns, row.kill_participation),
            )
            add_appearance_award(
                title="Most Deaths In A Win",
                appearance=death_win,
                stat=f"{death_win.deaths} deaths and still won",
                detail=f"{appearance_kda_line(death_win)} with {pct(death_win.kill_participation)} KP.",
                theme="blue",
                badge="D",
            )

    cursed_champion = find_first(
        sorted(
            [row for row in champion_rows if int(row.get("games", 0)) >= 5],
            key=lambda row: (
                float(row.get("winrate", 0)),
                -int(row.get("losses", 0)),
                -int(row.get("games", 0)),
                str(row.get("champion", "")),
            ),
        )
    )
    if cursed_champion:
        hall_rows.append(
            {
                "title": "Most Cursed Champion",
                "winner": str(cursed_champion.get("champion", "-")),
                "stat": f"{pct(float(cursed_champion.get('winrate', 0)))} WR",
                "detail": (
                    f"{integer(cursed_champion.get('wins', 0))}-"
                    f"{integer(cursed_champion.get('losses', 0))}, "
                    f"{integer(cursed_champion.get('games', 0))} games, "
                    f"{two_decimal(float(cursed_champion.get('kda_ratio', 0)))} KDA."
                ),
                "champion": str(cursed_champion.get("champion", "")),
                "theme": "red",
                "badge": "CURSE",
            }
        )

    pocket_pool = [
        row
        for row in player_champion_role_rows
        if 2 <= int(row.get("games", 0)) <= 4 and str(row.get("role", "")) in ROLE_ORDER
    ]
    if not pocket_pool:
        pocket_pool = [
            row
            for row in player_champion_role_rows
            if 1 <= int(row.get("games", 0)) <= 5 and str(row.get("role", "")) in ROLE_ORDER
        ]
    pocket = find_first(
        sorted(
            pocket_pool,
            key=lambda row: (
                -float(row.get("winrate", 0)),
                -int(row.get("wins", 0)),
                -float(row.get("kda_ratio", 0)),
                -int(row.get("games", 0)),
                str(row.get("name", "")),
            ),
        )
    )
    if pocket:
        hall_rows.append(
            {
                "title": "Best Pocket Pick",
                "winner": f"{pocket.get('name', '-')} {pocket.get('champion', '-')}",
                "stat": f"{pct(float(pocket.get('winrate', 0)))} WR",
                "detail": (
                    f"{pocket.get('role', '-')}, {integer(pocket.get('games', 0))} games, "
                    f"{two_decimal(float(pocket.get('kda_ratio', 0)))} KDA."
                ),
                "champion": str(pocket.get("champion", "")),
                "theme": "green",
                "badge": "POCKET",
            }
        )

    comfort = find_first(
        sorted(
            [row for row in player_champion_rows if int(row.get("games", 0)) >= 5],
            key=lambda row: (
                float(row.get("winrate", 0)),
                -int(row.get("losses", 0)),
                -int(row.get("games", 0)),
                str(row.get("name", "")),
            ),
        )
    )
    if comfort:
        hall_rows.append(
            {
                "title": "Worst Comfort Pick",
                "winner": f"{comfort.get('name', '-')} {comfort.get('champion', '-')}",
                "stat": f"{pct(float(comfort.get('winrate', 0)))} WR",
                "detail": (
                    f"{integer(comfort.get('wins', 0))}-{integer(comfort.get('losses', 0))}, "
                    f"{integer(comfort.get('games', 0))} games, "
                    f"{two_decimal(float(comfort.get('kda_ratio', 0)))} KDA."
                ),
                "champion": str(comfort.get("champion", "")),
                "theme": "red",
                "badge": "PAIN",
            }
        )

    role_pool = [
        row
        for row in player_role_rows
        if int(row.get("games", 0)) >= 4 and str(row.get("role", "")) in ROLE_ORDER
    ]
    terrorist = find_first(
        sorted(
            role_pool,
            key=lambda row: (
                float(row.get("winrate", 0)),
                -float(row.get("avg_deaths", 0)),
                -int(row.get("losses", 0)),
                -int(row.get("games", 0)),
                str(row.get("name", "")),
            ),
        )
    )
    if terrorist:
        hall_rows.append(
            {
                "title": "Biggest Role Terrorist",
                "winner": f"{terrorist.get('name', '-')} {terrorist.get('role', '-')}",
                "stat": f"{pct(float(terrorist.get('winrate', 0)))} WR",
                "detail": (
                    f"{integer(terrorist.get('games', 0))} games, "
                    f"{two_decimal(float(terrorist.get('avg_deaths', 0)))} deaths/game, "
                    f"{two_decimal(float(terrorist.get('kda_ratio', 0)))} KDA."
                ),
                "theme": "purple",
                "badge": "ROLE",
            }
        )

    return hall_rows


def team_side_sets(appearances: Sequence[Appearance]) -> dict[tuple[int, str], set[str]]:
    grouped: dict[tuple[int, str], set[str]] = defaultdict(set)
    for appearance in appearances:
        if not is_spotlight_excluded_player(appearance.name):
            grouped[(appearance.match_id, appearance.side)].add(appearance.name)
    return grouped


def experimental_chemistry_data(
    appearances: Sequence[Appearance],
    player_rows: Sequence[dict[str, object]],
) -> dict[str, object]:
    visible_players = without_spotlight_excluded_players(player_rows)
    player_stats = {
        str(row.get("name", "")): {
            "games": int(row.get("games", 0)),
            "wins": int(row.get("wins", 0)),
            "winrate": float(row.get("winrate", 0)),
        }
        for row in visible_players
    }
    grouped = team_side_sets(appearances)
    pair_stats: dict[tuple[str, str], dict[str, int]] = defaultdict(
        lambda: {"games": 0, "wins": 0}
    )
    for (_match_id, side), names in grouped.items():
        if len(names) < 2:
            continue
        for pair in combinations(sorted(names), 2):
            pair_stats[pair]["games"] += 1
            pair_stats[pair]["wins"] += 1 if side == "win" else 0

    links = []
    directed = []
    for pair, values in pair_stats.items():
        games = int(values["games"])
        if games < 3:
            continue
        wins = int(values["wins"])
        winrate = safe_div(wins, games)
        base = sum(player_stats.get(name, {}).get("winrate", 0.5) for name in pair) / 2
        lift = winrate - base
        link = {
            "players": pair,
            "label": " + ".join(pair),
            "games": games,
            "wins": wins,
            "losses": games - wins,
            "winrate": winrate,
            "base_winrate": base,
            "lift": lift,
            "lift_points": lift * 100,
        }
        links.append(link)
        for source, target in ((pair[0], pair[1]), (pair[1], pair[0])):
            target_stats = player_stats.get(target, {})
            target_games = int(target_stats.get("games", 0))
            target_wins = int(target_stats.get("wins", 0))
            without_games = target_games - games
            without_wins = target_wins - wins
            if without_games < 3:
                continue
            without_winrate = safe_div(without_wins, without_games)
            directed.append(
                {
                    "source": source,
                    "target": target,
                    "label": f"{source} + {target}",
                    "games": games,
                    "winrate": winrate,
                    "without_winrate": without_winrate,
                    "lift": winrate - without_winrate,
                    "lift_points": (winrate - without_winrate) * 100,
                }
            )

    best_links = sorted(
        [row for row in links if row["games"] >= 4],
        key=lambda row: (-float(row["lift"]), -float(row["winrate"]), -int(row["games"])),
    )
    worst_links = sorted(
        [row for row in links if row["games"] >= 4],
        key=lambda row: (float(row["lift"]), float(row["winrate"]), -int(row["games"])),
    )
    do_not_separate = find_first(
        sorted(directed, key=lambda row: (-float(row["lift"]), -int(row["games"])))
    )
    avoid_pairing = find_first(
        sorted(directed, key=lambda row: (float(row["lift"]), -int(row["games"])))
    )
    best_five = find_first(team_combo_rows(appearances, 5, TEAM_COMBO_MIN_GAMES[5]))
    network_links = best_links[:5] + worst_links[:5]
    return {
        "links": links,
        "network_links": network_links,
        "best_links": best_links[:5],
        "worst_links": worst_links[:5],
        "do_not_separate": do_not_separate,
        "avoid_pairing": avoid_pairing,
        "best_five": best_five,
    }


def experimental_upset_rows(
    appearances: Sequence[Appearance],
    player_rows: Sequence[dict[str, object]],
    mvp_rows: Sequence[dict[str, object]],
    role_score_rows: Sequence[dict[str, object]],
    player_champion_role_rows: Sequence[dict[str, object]],
) -> dict[str, list[dict[str, object]]]:
    visible = [
        appearance
        for appearance in appearances
        if not is_spotlight_excluded_player(appearance.name)
    ]
    player_by_name = {str(row.get("name", "")): row for row in player_rows}
    mvp_by_name = {str(row.get("name", "")): row for row in mvp_rows}
    role_score_by_key = {
        (str(row.get("name", "")), str(row.get("role", ""))): row
        for row in role_score_rows
    }
    combo_by_key = {
        (
            str(row.get("name", "")),
            str(row.get("champion", "")),
            str(row.get("role", "")),
        ): row
        for row in player_champion_role_rows
    }
    grouped: dict[int, list[Appearance]] = defaultdict(list)
    for appearance in visible:
        grouped[appearance.match_id].append(appearance)

    def player_expected_strength(appearance: Appearance) -> float:
        player = player_by_name.get(appearance.name, {})
        mvp_score = float(
            mvp_by_name.get(appearance.name, {}).get(
                "mvp_score", float(player.get("winrate", 0.5)) * 100
            )
        )
        role_score = float(
            role_score_by_key.get((appearance.name, appearance.role), {}).get(
                "role_score", 50
            )
        )
        combo = combo_by_key.get((appearance.name, appearance.champion, appearance.role), {})
        combo_games = int(combo.get("games", 0))
        combo_reliability = clamp(combo_games / 5)
        combo_winrate = float(combo.get("winrate", 0.5))
        combo_kda = clamp(float(combo.get("kda_ratio", 0)) / 5)
        comfort_score = 100 * (
            0.65 * (0.5 + ((combo_winrate - 0.5) * combo_reliability))
            + 0.35 * combo_kda
        )
        return 0.45 * mvp_score + 0.35 * role_score + 0.20 * comfort_score

    rows = []
    for match_id, match_rows in grouped.items():
        by_side = {
            "win": [row for row in match_rows if row.win],
            "lose": [row for row in match_rows if not row.win],
        }
        if not by_side["win"] or not by_side["lose"]:
            continue
        side_scores = {
            side: safe_div(
                sum(player_expected_strength(row) for row in side_rows), len(side_rows)
            )
            for side, side_rows in by_side.items()
        }
        expected_side = "win" if side_scores["win"] >= side_scores["lose"] else "lose"
        expected_margin = abs(side_scores["win"] - side_scores["lose"])
        winner_names = ", ".join(row.name for row in by_side["win"])
        loser_names = ", ".join(row.name for row in by_side["lose"])
        win_kills = sum(row.kills for row in by_side["win"])
        lose_kills = sum(row.kills for row in by_side["lose"])
        first = match_rows[0]
        rows.append(
            {
                "match_id": match_id,
                "label": appearance_match_label(first),
                "date_label": first.date_label,
                "winner_names": winner_names,
                "loser_names": loser_names,
                "win_score": side_scores["win"],
                "lose_score": side_scores["lose"],
                "expected_side": expected_side,
                "expected_margin": expected_margin,
                "actual_margin": win_kills - lose_kills,
                "win_kills": win_kills,
                "lose_kills": lose_kills,
                "upset": expected_side == "lose",
                "detail": (
                    f"Expected {'losing' if expected_side == 'lose' else 'winning'} side by "
                    f"{score(expected_margin)} model points. Kills: {win_kills}-{lose_kills}."
                ),
            }
        )

    upsets = sorted(
        [row for row in rows if row["upset"]],
        key=lambda row: (-float(row["expected_margin"]), -int(row["actual_margin"])),
    )
    stomps = sorted(
        [row for row in rows if not row["upset"]],
        key=lambda row: (-float(row["expected_margin"]), -int(row["actual_margin"])),
    )
    throws = sorted(
        [row for row in rows if row["upset"]],
        key=lambda row: (-float(row["expected_margin"]), int(row["lose_kills"])),
    )
    return {"upsets": upsets[:5], "stomps": stomps[:5], "throws": throws[:5]}


def champion_ownership_rows(
    appearances: Sequence[Appearance],
    champion_rows: Sequence[dict[str, object]],
    champion_role_rows: Sequence[dict[str, object]],
    player_champion_rows: Sequence[dict[str, object]],
    target_ban_rows: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    pilot_rows_by_champion: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in player_champion_rows:
        pilot_rows_by_champion[str(row.get("champion", ""))].append(row)
    role_rows_by_champion: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in champion_role_rows:
        role_rows_by_champion[str(row.get("champion", ""))].append(row)
    ban_rows_by_champion: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in target_ban_rows:
        ban_rows_by_champion[str(row.get("champion", ""))].append(row)
    recent_by_champion: dict[str, Appearance] = {}
    for appearance in appearances:
        if is_spotlight_excluded_player(appearance.name):
            continue
        champion = appearance.champion
        current = recent_by_champion.get(champion)
        if current is None or (appearance.timestamp, appearance.match_id) > (
            current.timestamp,
            current.match_id,
        ):
            recent_by_champion[champion] = appearance

    rows = []
    for champion in sorted(champion_rows, key=lambda row: str(row.get("champion", ""))):
        champion_name = str(champion.get("champion", ""))
        pilots = pilot_rows_by_champion.get(champion_name, [])
        pilot_pool = [row for row in pilots if int(row.get("games", 0)) >= 2] or pilots
        best_pilot = find_first(
            sorted(
                pilot_pool,
                key=lambda row: (
                    -float(row.get("winrate", 0)),
                    -int(row.get("wins", 0)),
                    -float(row.get("kda_ratio", 0)),
                    -int(row.get("games", 0)),
                    str(row.get("name", "")),
                ),
            )
        )
        cursed_pilot = find_first(
            sorted(
                pilot_pool,
                key=lambda row: (
                    float(row.get("winrate", 0)),
                    -int(row.get("losses", 0)),
                    -int(row.get("games", 0)),
                    str(row.get("name", "")),
                ),
            )
        )
        best_role = find_first(
            sorted(
                role_rows_by_champion.get(champion_name, []),
                key=lambda row: (
                    -float(row.get("winrate", 0)),
                    -int(row.get("wins", 0)),
                    -int(row.get("games", 0)),
                    role_sort(str(row.get("role", ""))),
                ),
            )
        )
        ban_row = find_first(
            sorted(
                ban_rows_by_champion.get(champion_name, []),
                key=lambda row: (
                    -float(row.get("ban_score", 0)),
                    -int(row.get("games", 0)),
                ),
            )
        )
        recent = recent_by_champion.get(champion_name)
        rows.append(
            {
                "champion": champion_name,
                "games": int(champion.get("games", 0)),
                "wins": int(champion.get("wins", 0)),
                "losses": int(champion.get("losses", 0)),
                "winrate": float(champion.get("winrate", 0)),
                "owner": str(best_pilot.get("name", "-")) if best_pilot else "-",
                "owner_detail": (
                    f"{pct(float(best_pilot.get('winrate', 0)))} WR, "
                    f"{integer(best_pilot.get('games', 0))}g"
                    if best_pilot
                    else "-"
                ),
                "cursed_pilot": (
                    str(cursed_pilot.get("name", "-")) if cursed_pilot else "-"
                ),
                "cursed_detail": (
                    f"{pct(float(cursed_pilot.get('winrate', 0)))} WR, "
                    f"{integer(cursed_pilot.get('games', 0))}g"
                    if cursed_pilot
                    else "-"
                ),
                "best_role": str(best_role.get("role", "-")) if best_role else "-",
                "best_role_detail": (
                    f"{pct(float(best_role.get('winrate', 0)))} WR, "
                    f"{integer(best_role.get('games', 0))}g"
                    if best_role
                    else "-"
                ),
                "recent": (
                    f"Match {recent.match_id}: {recent.name} {recent.role}"
                    if recent
                    else "No recent games"
                ),
                "ban_priority": float(ban_row.get("ban_score", 0)) if ban_row else 0.0,
                "ban_detail": (
                    f"{ban_row.get('name', '-')} {score(float(ban_row.get('ban_score', 0)))}"
                    if ban_row
                    else "No target signal"
                ),
                "search_text": (
                    f"{champion_name} {best_pilot.get('name', '') if best_pilot else ''} "
                    f"{cursed_pilot.get('name', '') if cursed_pilot else ''} "
                    f"{best_role.get('role', '') if best_role else ''}"
                ),
            }
        )
    return sorted(
        rows,
        key=lambda row: (
            -float(row.get("ban_priority", 0)),
            -int(row.get("games", 0)),
            str(row.get("champion", "")),
        ),
    )


def target_ban_score_rows(
    player_champion_rows: Sequence[dict[str, object]],
    player_rows: Sequence[dict[str, object]],
    mvp_rows: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    player_by_name = {str(row["name"]): row for row in player_rows}
    mvp_by_name = {str(row["name"]): row for row in mvp_rows}
    max_games = max(
        (int(row.get("games", 0)) for row in player_champion_rows), default=1
    )
    rows = []
    for row in player_champion_rows:
        games = int(row.get("games", 0))
        if games <= 0:
            continue
        wins = int(row.get("wins", 0))
        winrate = float(row.get("winrate", 0))
        reliability = clamp(games / TARGET_BAN_RELIABILITY_GAMES)
        adjusted_winrate = 0.5 + ((winrate - 0.5) * reliability)
        games_score = safe_div(games, max_games) ** 0.5
        kda_score = clamp(float(row.get("kda_ratio", 0)) / 6)
        takedown_score = clamp(float(row.get("avg_takedowns", 0)) / 14)
        name = str(row.get("name", ""))
        player = player_by_name.get(name, {})
        mvp = mvp_by_name.get(name, {})
        player_games = int(player.get("games", games)) or games
        player_winrate = float(player.get("winrate", 0.5))
        player_reliability = clamp(player_games / MIN_PLAYER_GAMES)
        player_adjusted_winrate = float(
            mvp.get(
                "adjusted_winrate",
                0.5 + ((player_winrate - 0.5) * player_reliability),
            )
        )
        display_mvp_score = float(mvp.get("mvp_score", player_adjusted_winrate * 100))
        mvp_rating = clamp(display_mvp_score / 100)
        player_threat = clamp(0.62 * mvp_rating + 0.38 * player_adjusted_winrate)
        lift = adjusted_winrate - player_winrate
        lift_score = clamp((lift + 0.08) / 0.28)
        ban_score = 100 * (
            0.34 * player_threat
            + 0.28 * adjusted_winrate
            + 0.16 * games_score
            + 0.10 * kda_score
            + 0.07 * takedown_score
            + 0.05 * lift_score
        )
        confidence = "High" if games >= 5 else "Medium" if games >= 3 else "Low"
        mvp_detail = (
            f"{score(display_mvp_score)} MVP"
            if mvp
            else f"below {MIN_PLAYER_GAMES}-game MVP board"
        )
        scored_row = dict(row)
        scored_row.update(
            {
                "ban_score": ban_score,
                "adjusted_winrate": adjusted_winrate,
                "reliability": reliability,
                "player_winrate": player_winrate,
                "player_adjusted_winrate": player_adjusted_winrate,
                "player_threat": player_threat,
                "mvp_score": display_mvp_score if mvp else 0,
                "lift": lift,
                "confidence": confidence,
                "target_detail": (
                    f"{wins}-{games - wins}, {games} games, {pct(winrate)} WR, "
                    f"{two_decimal(float(row.get('kda_ratio', 0)))} KDA, "
                    f"{mvp_detail}"
                ),
            }
        )
        rows.append(scored_row)
    return sorted(
        rows,
        key=lambda row: (
            -float(row["ban_score"]),
            -float(row["adjusted_winrate"]),
            -int(row["games"]),
            str(row["name"]),
            str(row["champion"]),
        ),
    )


def practice_pick_score_rows(
    player_champion_rows: Sequence[dict[str, object]],
    player_rows: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    player_by_name = {str(row["name"]): row for row in player_rows}
    eligible_rows = []
    for row in player_champion_rows:
        games = int(row.get("games", 0))
        winrate = float(row.get("winrate", 0))
        name = str(row.get("name", ""))
        player = player_by_name.get(name, {})
        player_winrate = float(player.get("winrate", 0.5))
        if games < PRACTICE_PICK_MIN_GAMES:
            continue
        if winrate >= PRACTICE_PICK_MAX_WINRATE:
            continue
        if winrate > player_winrate - PRACTICE_PICK_BASELINE_GAP:
            continue
        eligible_rows.append(row)
    max_games = max((int(row.get("games", 0)) for row in eligible_rows), default=1)
    max_losses = max(
        (int(row.get("games", 0)) - int(row.get("wins", 0)) for row in eligible_rows),
        default=1,
    )
    rows = []
    for row in eligible_rows:
        games = int(row.get("games", 0))
        wins = int(row.get("wins", 0))
        losses = games - wins
        winrate = float(row.get("winrate", 0))
        reliability = clamp(
            (games - 1) / max(1, PRACTICE_PICK_RELIABILITY_GAMES - 1)
        )
        adjusted_winrate = 0.5 + ((winrate - 0.5) * reliability)
        low_winrate_score = clamp((0.5 - winrate) / 0.5)
        games_score = safe_div(games, max_games) ** 0.5
        loss_volume_score = safe_div(losses, max_losses) ** 0.5
        name = str(row.get("name", ""))
        player = player_by_name.get(name, {})
        player_winrate = float(player.get("winrate", 0.5))
        lift = winrate - player_winrate
        under_baseline_score = clamp((player_winrate - winrate) / 0.35)
        practice_score = 100 * (
            0.60 * low_winrate_score
            + 0.24 * loss_volume_score
            + 0.10 * games_score
            + 0.06 * under_baseline_score
        )
        confidence = "High" if games >= 6 else "Medium" if games >= 3 else "Low"
        scored_row = dict(row)
        scored_row.update(
            {
                "practice_score": practice_score,
                "adjusted_winrate": adjusted_winrate,
                "reliability": reliability,
                "player_winrate": player_winrate,
                "lift": lift,
                "confidence": confidence,
                "practice_detail": (
                    f"{wins}-{losses}, {games} games, {pct(winrate)} WR, "
                    f"{signed_pct(lift)} vs player WR"
                ),
            }
        )
        rows.append(scored_row)
    return sorted(
        rows,
        key=lambda row: (
            -float(row["practice_score"]),
            float(row["winrate"]),
            -int(row["games"]),
            str(row["name"]),
            str(row["champion"]),
            str(row.get("role", "")),
        ),
    )


def match_summaries(appearances: Sequence[Appearance]) -> list[dict[str, object]]:
    grouped: dict[int, list[Appearance]] = defaultdict(list)
    for appearance in appearances:
        grouped[appearance.match_id].append(appearance)

    matches = []
    for match_id, rows in grouped.items():
        win_rows = [row for row in rows if row.win]
        lose_rows = [row for row in rows if not row.win]
        matches.append(
            {
                "match_id": match_id,
                "date_label": rows[0].date_label,
                "weekday": rows[0].weekday_label,
                "timestamp": rows[0].timestamp,
                "kills": sum(row.kills for row in rows),
                "deaths": sum(row.deaths for row in rows),
                "assists": sum(row.assists for row in rows),
                "win_kills": sum(row.kills for row in win_rows),
                "lose_kills": sum(row.kills for row in lose_rows),
                "win_deaths": sum(row.deaths for row in win_rows),
                "lose_deaths": sum(row.deaths for row in lose_rows),
                "winner_names": ", ".join(row.name for row in win_rows),
                "loser_names": ", ".join(row.name for row in lose_rows),
            }
        )
    return sorted(matches, key=lambda item: int(item["match_id"]))


def role_champion_pool_rows(appearances: Sequence[Appearance]) -> list[dict[str, object]]:
    stats: dict[str, dict[str, object]] = defaultdict(
        lambda: {"games": 0, "champions": Counter()}
    )
    for appearance in appearances:
        stats[appearance.role]["games"] = int(stats[appearance.role]["games"]) + 1
        stats[appearance.role]["champions"][appearance.champion] += 1

    rows = []
    for role, values in stats.items():
        games = int(values["games"])
        champions = values["champions"]
        unique_champions = len(champions)
        rows.append(
            {
                "role": role,
                "games": games,
                "unique_champions": unique_champions,
                "champion_pool_rate": safe_div(unique_champions, games),
                "champion_counts": champions,
                "champions": full_counter(champions),
            }
        )
    return sorted(rows, key=lambda row: role_sort(str(row["role"])))


def player_role_champion_pool_rows(
    appearances: Sequence[Appearance],
) -> list[dict[str, object]]:
    stats: dict[tuple[str, str], dict[str, object]] = defaultdict(
        lambda: {"games": 0, "wins": 0, "champions": Counter()}
    )
    for appearance in appearances:
        key = (appearance.name, appearance.role)
        stats[key]["games"] = int(stats[key]["games"]) + 1
        stats[key]["wins"] = int(stats[key]["wins"]) + appearance.win
        stats[key]["champions"][appearance.champion] += 1

    rows = []
    for (name, role), values in stats.items():
        games = int(values["games"])
        wins = int(values["wins"])
        champions = values["champions"]
        unique_champions = len(champions)
        rows.append(
            {
                "name": name,
                "role": role,
                "games": games,
                "wins": wins,
                "winrate": safe_div(wins, games),
                "unique_champions": unique_champions,
                "champion_pool_rate": safe_div(unique_champions, games),
                "champions": full_counter(champions),
            }
        )
    return sorted(
        rows,
        key=lambda row: (
            -float(row["winrate"]),
            -int(row["unique_champions"]),
            -int(row["games"]),
            str(row["name"]),
            role_sort(str(row["role"])),
        ),
    )


def find_first(rows: Sequence[dict[str, object]]) -> dict[str, object]:
    if not rows:
        return {}
    return rows[0]


def qualify(rows: Iterable[dict[str, object]], minimum_games: int) -> list[dict[str, object]]:
    return [row for row in rows if int(row.get("games", 0)) >= minimum_games]


@lru_cache(maxsize=None)
def spotlight_exclusion_tokens(value: str) -> tuple[str, ...]:
    tokens = []
    current = []
    for character in value.casefold():
        if character.isalnum():
            current.append(character)
        elif current:
            tokens.append("".join(current))
            current = []
    if current:
        tokens.append("".join(current))
    return tuple(tokens)


def is_anonymous_player_token(token: str) -> bool:
    return any(token.startswith(prefix) for prefix in ANONYMOUS_PLAYER_PREFIXES)


@lru_cache(maxsize=None)
def is_spotlight_excluded_player_name(name: str) -> bool:
    tokens = spotlight_exclusion_tokens(name)
    return any(
        token in SPOTLIGHT_EXCLUDED_PLAYERS or is_anonymous_player_token(token)
        for token in tokens
    )


def is_spotlight_excluded_player(name: object) -> bool:
    return is_spotlight_excluded_player_name(str(name))


def text_mentions_spotlight_excluded_player(value: object) -> bool:
    return is_spotlight_excluded_player(value)


def award_mentions_spotlight_excluded_player(award: dict[str, object]) -> bool:
    return text_mentions_spotlight_excluded_player(award.get("winner", ""))


def without_spotlight_excluded_players(
    rows: Iterable[dict[str, object]],
) -> list[dict[str, object]]:
    return [
        row
        for row in rows
        if not is_spotlight_excluded_player(row.get("name", ""))
    ]


def appearance_context(appearance: Appearance) -> str:
    return (
        f"{appearance.name} on {appearance.champion} ({appearance.role}) - "
        f"Match {appearance.match_id}, {appearance.date_label}, {appearance.result}"
    )


def build_awards(
    appearances: Sequence[Appearance],
    player_rows: Sequence[dict[str, object]],
    champion_rows: Sequence[dict[str, object]],
    player_role_rows: Sequence[dict[str, object]],
    player_champion_rows: Sequence[dict[str, object]],
    player_champion_role_rows: Sequence[dict[str, object]],
    matches: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    award_player_rows = without_spotlight_excluded_players(player_rows)
    award_player_role_rows = without_spotlight_excluded_players(player_role_rows)
    award_player_champion_rows = without_spotlight_excluded_players(player_champion_rows)
    award_player_champion_role_rows = without_spotlight_excluded_players(
        player_champion_role_rows
    )
    award_appearances = [
        row for row in appearances if not is_spotlight_excluded_player(row.name)
    ] or list(appearances)

    player_pool = qualify(award_player_rows, MIN_PLAYER_GAMES) or list(award_player_rows)
    champion_pool = qualify(champion_rows, MIN_CHAMPION_GAMES) or list(champion_rows)
    combo_pool = qualify(award_player_champion_role_rows, MIN_COMBO_GAMES) or list(
        award_player_champion_role_rows
    )
    player_champion_pool = qualify(award_player_champion_rows, MIN_COMBO_GAMES) or list(
        award_player_champion_rows
    )
    role_pool = qualify(award_player_role_rows, MIN_COMBO_GAMES) or list(
        award_player_role_rows
    )

    best_winrate = find_first(
        sorted(player_pool, key=lambda row: (-float(row["winrate"]), -int(row["games"])))
    )
    best_kda = find_first(
        sorted(player_pool, key=lambda row: (-float(row["kda_ratio"]), -int(row["games"])))
    )
    best_avg_kills = find_first(
        sorted(player_pool, key=lambda row: (-float(row["avg_kills"]), -int(row["games"])))
    )
    most_games = find_first(sorted(award_player_rows, key=lambda row: -int(row["games"])))
    most_champs = find_first(
        sorted(
            award_player_rows,
            key=lambda row: (-int(row["unique_champions"]), -int(row["games"])),
        )
    )
    most_deaths_per_game = find_first(
        sorted(
            player_pool,
            key=lambda row: (-float(row["avg_deaths"]), -int(row["games"])),
        )
    )
    least_deaths_per_game = find_first(
        sorted(
            player_pool,
            key=lambda row: (float(row["avg_deaths"]), -int(row["games"])),
        )
    )
    best_champion = find_first(
        sorted(
            champion_pool,
            key=lambda row: (-float(row["winrate"]), -int(row["games"])),
        )
    )
    most_played_champion = find_first(
        sorted(
            [
                row
                for row in champion_rows
                if not is_most_contested_excluded_champion(row.get("champion", ""))
            ],
            key=lambda row: -int(row["games"]),
        )
    )
    best_combo = find_first(
        sorted(combo_pool, key=lambda row: (-float(row["winrate"]), -int(row["games"])))
    )
    most_played_combo = find_first(
        sorted(player_champion_pool, key=lambda row: -int(row["games"]))
    )
    best_role = find_first(
        sorted(role_pool, key=lambda row: (-float(row["winrate"]), -int(row["games"])))
    )

    highest_kills = max(
        award_appearances, key=lambda row: (row.kills, row.assists, -row.deaths)
    )
    highest_deaths = max(award_appearances, key=lambda row: (row.deaths, row.kills))
    highest_assists = max(award_appearances, key=lambda row: (row.assists, row.kills))
    zero_death_rows = [row for row in award_appearances if row.deaths == 0]
    perfect_game = max(
        zero_death_rows or award_appearances,
        key=lambda row: (row.takedowns, row.kills, row.assists),
    )
    bloodiest_game = max(matches, key=lambda row: (int(row["kills"]), int(row["assists"])))
    cleanest_win = min(matches, key=lambda row: (int(row["win_deaths"]), -int(row["win_kills"])))

    awards = [
        {
            "title": "Winrate Crown",
            "winner": str(best_winrate.get("name", "-")),
            "stat": f"{pct(float(best_winrate.get('winrate', 0)))} over {best_winrate.get('games', 0)} games",
            "detail": "Best player winrate among regulars.",
            "theme": "gold",
            "badge": "WR",
        },
        {
            "title": "KDA King",
            "winner": str(best_kda.get("name", "-")),
            "stat": f"{two_decimal(float(best_kda.get('kda_ratio', 0)))} KDA",
            "detail": f"{one_decimal(float(best_kda.get('avg_kills', 0)))} / {one_decimal(float(best_kda.get('avg_deaths', 0)))} / {one_decimal(float(best_kda.get('avg_assists', 0)))} per game.",
            "theme": "violet",
            "badge": "KDA",
        },
        {
            "title": "Kill Threat",
            "winner": str(best_avg_kills.get("name", "-")),
            "stat": f"{one_decimal(float(best_avg_kills.get('avg_kills', 0)))} kills per game",
            "detail": "Highest average kills among regulars.",
            "theme": "red",
            "badge": "K",
        },
        {
            "title": "Single Game Kill Record",
            "winner": highest_kills.name,
            "stat": f"{highest_kills.kills} kills",
            "detail": appearance_context(highest_kills),
            "theme": "red",
            "champion": highest_kills.champion,
            "match_id": highest_kills.match_id,
        },
        {
            "title": "Single Game Death Record",
            "winner": highest_deaths.name,
            "stat": f"{highest_deaths.deaths} deaths",
            "detail": appearance_context(highest_deaths),
            "theme": "red",
            "champion": highest_deaths.champion,
            "match_id": highest_deaths.match_id,
        },
        {
            "title": "Assist Record",
            "winner": highest_assists.name,
            "stat": f"{highest_assists.assists} assists",
            "detail": appearance_context(highest_assists),
            "theme": "green",
            "champion": highest_assists.champion,
            "match_id": highest_assists.match_id,
        },
        {
            "title": "Most Played",
            "winner": str(most_games.get("name", "-")),
            "stat": f"{most_games.get('games', 0)} games",
            "detail": f"Most common champions: {most_games.get('most_played_champion', '-')}",
            "theme": "blue",
            "badge": "GP",
        },
        {
            "title": "Champion Ocean",
            "winner": str(most_champs.get("name", "-")),
            "stat": f"{most_champs.get('unique_champions', 0)} champions",
            "detail": (
                f"{pct(float(most_champs.get('champion_pool_rate', 0)))} unique-pick rate."
            ),
            "theme": "blue",
            "badge": "POOL",
        },
        {
            "title": "Death Magnet",
            "winner": str(most_deaths_per_game.get("name", "-")),
            "stat": f"{one_decimal(float(most_deaths_per_game.get('avg_deaths', 0)))} deaths per game",
            "detail": f"Across {most_deaths_per_game.get('games', 0)} games.",
            "theme": "red",
            "badge": "D",
        },
        {
            "title": "Hardest To Kill",
            "winner": str(least_deaths_per_game.get("name", "-")),
            "stat": f"{one_decimal(float(least_deaths_per_game.get('avg_deaths', 0)))} deaths per game",
            "detail": f"Across {least_deaths_per_game.get('games', 0)} games.",
            "theme": "green",
            "badge": "SAFE",
        },
        {
            "title": "Best Champion",
            "winner": str(best_champion.get("champion", "-")),
            "stat": f"{pct(float(best_champion.get('winrate', 0)))} winrate",
            "detail": f"{best_champion.get('games', 0)} games. Main roles: {best_champion.get('top_roles', '-')}",
            "theme": "gold",
            "champion": str(best_champion.get("champion", "")),
        },
        {
            "title": "Most Contested Champion",
            "winner": str(most_played_champion.get("champion", "-")),
            "stat": f"{most_played_champion.get('games', 0)} games",
            "detail": f"{pct(float(most_played_champion.get('winrate', 0)))} winrate overall.",
            "theme": "blue",
            "champion": str(most_played_champion.get("champion", "")),
        },
        {
            "title": "Pocket Pick",
            "winner": f"{best_combo.get('name', '-')} {best_combo.get('champion', '-')} {best_combo.get('role', '-')}",
            "stat": f"{pct(float(best_combo.get('winrate', 0)))} winrate",
            "detail": f"{best_combo.get('games', 0)} games in that champion-role slot.",
            "theme": "gold",
            "champion": str(best_combo.get("champion", "")),
        },
        {
            "title": "One Trick Candidate",
            "winner": f"{most_played_combo.get('name', '-')} {most_played_combo.get('champion', '-')}",
            "stat": f"{most_played_combo.get('games', 0)} games",
            "detail": f"{pct(float(most_played_combo.get('winrate', 0)))} winrate on the pick.",
            "theme": "violet",
            "champion": str(most_played_combo.get("champion", "")),
        },
        {
            "title": "Role Specialist",
            "winner": f"{best_role.get('name', '-')} {best_role.get('role', '-')}",
            "stat": f"{pct(float(best_role.get('winrate', 0)))} winrate",
            "detail": f"{best_role.get('games', 0)} games in role.",
            "theme": "green",
            "badge": str(best_role.get("role", "-"))[:4],
        },
        {
            "title": "Clean Game",
            "winner": perfect_game.name,
            "stat": f"{perfect_game.kills}/{perfect_game.deaths}/{perfect_game.assists}",
            "detail": appearance_context(perfect_game),
            "theme": "green",
            "champion": perfect_game.champion,
            "match_id": perfect_game.match_id,
        },
        {
            "title": "Bloodiest Game",
            "winner": f"Match {bloodiest_game.get('match_id')}",
            "stat": f"{bloodiest_game.get('kills')} total kills",
            "detail": f"{bloodiest_game.get('date_label')} - winners: {bloodiest_game.get('winner_names')}",
            "theme": "red",
            "badge": "VS",
            "match_id": bloodiest_game.get("match_id"),
        },
        {
            "title": "Cleanest Team Win",
            "winner": f"Match {cleanest_win.get('match_id')}",
            "stat": f"{cleanest_win.get('win_deaths')} team deaths",
            "detail": f"{cleanest_win.get('date_label')} - winners: {cleanest_win.get('winner_names')}",
            "theme": "green",
            "badge": "WIN",
            "match_id": cleanest_win.get("match_id"),
        },
    ]
    return [
        award
        for award in awards
        if not award_mentions_spotlight_excluded_player(award)
    ]


def html_attr(value: object) -> str:
    return escape(str(value), quote=True)


def svg_id_token(value: object) -> str:
    token = "".join(
        character.lower() if character.isascii() and character.isalnum() else "-"
        for character in str(value)
    ).strip("-")
    return token or "item"


def table_cell(
    value: object,
    sort_value: object | None = None,
    class_name: str = "",
    style: str = "",
) -> str:
    sort = value if sort_value is None else sort_value
    class_attr = f' class="{html_attr(class_name)}"' if class_name else ""
    style_attr = f' style="{html_attr(style)}"' if style else ""
    return f'<td{class_attr}{style_attr} data-sort="{html_attr(sort)}">{escape(str(value))}</td>'


def heat_text_color(winrate: float) -> str:
    return "#17212b" if 0.38 <= winrate <= 0.68 else "#ffffff"


def heat_table_cell(
    value: object,
    winrate: float,
    sort_value: object | None = None,
) -> str:
    style = (
        f"background: {heat_color(winrate)}; "
        f"color: {heat_text_color(winrate)}; font-weight: 900;"
    )
    sort = winrate if sort_value is None else sort_value
    return table_cell(value, sort, "table-heat-cell number-cell", style)


def role_breakdown_winrate(value: object) -> float | None:
    text = str(value)
    if "%" not in text:
        return None
    percent_text = text.rsplit("/", 1)[-1].strip().rstrip("%")
    try:
        return float(percent_text) / 100
    except ValueError:
        return None


def mvp_rank_cell(value: object, row: dict[str, object]) -> str:
    rank = int(row.get("mvp_rank", 999))
    if rank > 10:
        return table_cell(value, value)
    amount = 1.0 - ((rank - 1) / 9)
    color = interpolate_color((98, 168, 255), (240, 201, 106), amount)
    style = (
        f"color: {color}; font-weight: 950; "
        f"text-shadow: 0 0 {10 + round(amount * 10)}px rgba(240, 201, 106, {0.10 + amount * 0.16:.2f});"
    )
    return table_cell(value, value, "mvp-name-cell", style)


Column = tuple[str, str, Callable[[object], str], str]


def render_table(
    table_id: str,
    title: str,
    rows: Sequence[dict[str, object]],
    columns: Sequence[Column],
    *,
    limit: int | None = None,
    searchable: bool = True,
    controls_html: str = "",
) -> str:
    table_rows = without_spotlight_excluded_players(rows)
    visible_rows = list(table_rows if limit is None else table_rows[:limit])
    search_html = (
        f'<input class="table-search" type="search" placeholder="Filter {html_attr(title)}" '
        f'data-table-filter="{html_attr(table_id)}">'
        if searchable
        else ""
    )
    controls = f'<div class="table-controls">{controls_html}{search_html}</div>' if (controls_html or search_html) else ""
    header = "".join(
        f'<th data-type="{html_attr(data_type)}">{escape(label)}</th>'
        for label, _key, _formatter, data_type in columns
    )
    body_parts = []
    for row in visible_rows:
        cells = []
        for _label, key, formatter, data_type in columns:
            raw = row.get(key, "")
            value = formatter(raw)
            sort_value = raw if data_type == "number" else value
            if table_id == "mvp-scoreboard" and key == "name":
                cells.append(mvp_rank_cell(value, row))
            elif table_id != "mvp-scoreboard" and key in {"winrate", "adjusted_winrate"}:
                cells.append(heat_table_cell(value, float(raw), sort_value))
            elif table_id == "player-summary" and key.startswith("role_"):
                role_winrate = role_breakdown_winrate(value)
                if role_winrate is None:
                    cells.append(table_cell(value, sort_value))
                else:
                    cells.append(heat_table_cell(value, role_winrate, role_winrate))
            elif key == "name":
                cells.append(table_cell(value, sort_value, "name-cell"))
            elif data_type == "number":
                cells.append(table_cell(value, sort_value, "number-cell"))
            else:
                cells.append(table_cell(value, sort_value))
        body_parts.append(f"<tr>{''.join(cells)}</tr>")
    body = "\n".join(body_parts)
    return f"""
    <section class="table-panel">
      <div class="section-heading">
        <h3>{escape(title)}</h3>
        {controls}
      </div>
      <div class="table-wrap">
        <table id="{html_attr(table_id)}" class="sortable-table">
          <thead><tr>{header}</tr></thead>
          <tbody>{body}</tbody>
        </table>
      </div>
    </section>
    """


def render_metric_card(label: str, value: str, detail: str) -> str:
    return f"""
    <article class="metric-card">
      <span>{escape(label)}</span>
      <strong>{escape(value)}</strong>
      <small>{escape(detail)}</small>
    </article>
    """


def render_popular_champions_strip(rows: Sequence[dict[str, object]], *, limit: int = 10) -> str:
    items = []
    for index, row in enumerate(rows[:limit], start=1):
        champion = str(row.get("champion", "-"))
        winrate = float(row.get("winrate", 0))
        items.append(
            f"""
            <div class="popular-champion-item" title="{html_attr(champion)}">
              <span>#{index}</span>
              <img src="{html_attr(champion_icon_url(champion))}" alt="{html_attr(champion)}">
              <small>{integer(row.get("games", 0))} games</small>
              <b>{pct(winrate)} WR</b>
            </div>
            """
        )
    return f"""
    <section class="popular-champions-panel">
      <div class="section-heading">
        <h3>Most Popular Champions</h3>
        <small>Across all roles, excluding Qiyana</small>
      </div>
      <div class="popular-champion-row">{''.join(items)}</div>
    </section>
    """


def render_award_symbol(icon_name: str) -> str:
    symbols = {
        "crown": """
          <svg class="award-symbol-svg" viewBox="0 0 64 64" aria-hidden="true" focusable="false">
            <path d="M12 25l10 9 10-17 10 17 10-9-4 25H16z" fill="none" stroke="currentColor" stroke-width="4" stroke-linejoin="round"/>
            <path d="M18 50h28" fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="round"/>
          </svg>
        """,
        "diamond": """
          <svg class="award-symbol-svg" viewBox="0 0 64 64" aria-hidden="true" focusable="false">
            <path d="M18 12h28l10 15-24 28L8 27z" fill="none" stroke="currentColor" stroke-width="4" stroke-linejoin="round"/>
            <path d="M18 12l14 43 14-43M8 27h48" fill="none" stroke="currentColor" stroke-width="3" stroke-linejoin="round"/>
          </svg>
        """,
        "crosshair": """
          <svg class="award-symbol-svg" viewBox="0 0 64 64" aria-hidden="true" focusable="false">
            <circle cx="32" cy="32" r="18" fill="none" stroke="currentColor" stroke-width="4"/>
            <circle cx="32" cy="32" r="5" fill="currentColor"/>
            <path d="M32 8v12M32 44v12M8 32h12M44 32h12" fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="round"/>
          </svg>
        """,
        "wheel": """
          <svg class="award-symbol-svg" viewBox="0 0 64 64" aria-hidden="true" focusable="false">
            <circle cx="32" cy="32" r="20" fill="none" stroke="currentColor" stroke-width="4"/>
            <circle cx="32" cy="32" r="5" fill="currentColor"/>
            <path d="M32 12v15M32 37v15M12 32h15M37 32h15M18 18l11 11M35 35l11 11M46 18L35 29M29 35L18 46" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
          </svg>
        """,
        "fan": """
          <svg class="award-symbol-svg" viewBox="0 0 64 64" aria-hidden="true" focusable="false">
            <path d="M32 52V16" fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round"/>
            <path d="M32 52c-9-8-16-17-15-29 10 1 16 10 15 29zM32 52c9-8 16-17 15-29-10 1-16 10-15 29z" fill="none" stroke="currentColor" stroke-width="4" stroke-linejoin="round"/>
            <path d="M19 52h26" fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="round"/>
          </svg>
        """,
        "warning": """
          <svg class="award-symbol-svg" viewBox="0 0 64 64" aria-hidden="true" focusable="false">
            <path d="M32 10l25 44H7z" fill="none" stroke="currentColor" stroke-width="4" stroke-linejoin="round"/>
            <path d="M32 25v14" fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round"/>
            <circle cx="32" cy="47" r="3" fill="currentColor"/>
          </svg>
        """,
        "shield": """
          <svg class="award-symbol-svg" viewBox="0 0 64 64" aria-hidden="true" focusable="false">
            <path d="M32 8l21 8v16c0 13-8 22-21 26-13-4-21-13-21-26V16z" fill="none" stroke="currentColor" stroke-width="4" stroke-linejoin="round"/>
            <path d="M24 32l6 7 12-15" fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        """,
        "clash": """
          <svg class="award-symbol-svg" viewBox="0 0 64 64" aria-hidden="true" focusable="false">
            <path d="M18 11l35 35M46 11L11 46" fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round"/>
            <path d="M12 52l8-8M52 52l-8-8" fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="round"/>
          </svg>
        """,
        "spark": """
          <svg class="award-symbol-svg" viewBox="0 0 64 64" aria-hidden="true" focusable="false">
            <path d="M32 7l6 19 19 6-19 6-6 19-6-19-19-6 19-6z" fill="none" stroke="currentColor" stroke-width="4" stroke-linejoin="round"/>
            <path d="M48 8l2 7 7 2-7 2-2 7-2-7-7-2 7-2z" fill="currentColor"/>
          </svg>
        """,
        "lane": """
          <svg class="award-symbol-svg" viewBox="0 0 64 64" aria-hidden="true" focusable="false">
            <rect x="16" y="16" width="32" height="32" rx="6" fill="none" stroke="currentColor" stroke-width="4" transform="rotate(45 32 32)"/>
            <circle cx="24" cy="24" r="4" fill="currentColor"/>
            <circle cx="40" cy="40" r="4" fill="currentColor"/>
          </svg>
        """,
        "leaf": """
          <svg class="award-symbol-svg" viewBox="0 0 64 64" aria-hidden="true" focusable="false">
            <path d="M51 13c-18 1-34 11-36 29-1 8 5 12 13 10 18-3 25-21 23-39z" fill="none" stroke="currentColor" stroke-width="4" stroke-linejoin="round"/>
            <path d="M18 49c9-13 19-21 31-30" fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="round"/>
          </svg>
        """,
    }
    return symbols.get(icon_name, symbols["spark"])


def render_awards(awards: Sequence[dict[str, object]]) -> str:
    award_icon_map = {
        "WR": "crown",
        "KDA": "diamond",
        "K": "crosshair",
        "GP": "wheel",
        "POOL": "fan",
        "D": "warning",
        "SAFE": "shield",
        "VS": "clash",
        "WIN": "spark",
        "TOP": "lane",
        "JUNG": "leaf",
        "MID": "spark",
        "BOT": "crosshair",
        "SUPP": "shield",
    }
    cards = []
    for award in awards:
        champion = str(award.get("champion", "")).strip()
        badge = str(award.get("badge", "")).strip() or str(award.get("title", "-"))[:3]
        theme = str(award.get("theme", "blue")).strip() or "blue"
        match_id = str(award.get("match_id", "")).strip()
        if champion and champion != "-":
            visual = (
                f'<div class="award-icon champion-award-icon">'
                f'<img src="{html_attr(champion_icon_url(champion))}" alt="{html_attr(champion)}">'
                f'</div>'
            )
        else:
            icon_name = award_icon_map.get(badge.upper(), "spark")
            visual = (
                f'<div class="award-icon award-badge award-symbol award-symbol-{html_attr(icon_name)}">'
                f'{render_award_symbol(icon_name)}'
                f'</div>'
            )
        if match_id:
            open_tag = (
                f'<a class="award-card award-theme-{html_attr(theme)}" '
                f'href="#match-{html_attr(match_id)}" data-award-match-id="{html_attr(match_id)}" '
                f'aria-label="Open Match {html_attr(match_id)} for {html_attr(award["title"])}">'
            )
            close_tag = "</a>"
        else:
            open_tag = f'<article class="award-card award-theme-{html_attr(theme)}">'
            close_tag = "</article>"
        cards.append(
            f"""
            {open_tag}
              {visual}
              <div class="award-copy">
                <span>{escape(str(award["title"]))}</span>
                <strong>{escape(str(award["winner"]))}</strong>
                <b>{escape(str(award["stat"]))}</b>
                <small>{escape(str(award["detail"]))}</small>
              </div>
            {close_tag}
            """
        )
    return "\n".join(cards)


def render_bar_chart(
    title: str,
    rows: Sequence[dict[str, object]],
    label_key: str,
    value_key: str,
    formatter: Callable[[float], str],
    *,
    limit: int = 10,
    max_value: float | None = None,
    footer_key: str | None = None,
    footer_formatter: Callable[[object], str] | None = None,
    class_name: str = "",
) -> str:
    chart_rows = list(rows[:limit])
    if max_value is None:
        max_value = max((float(row.get(value_key, 0)) for row in chart_rows), default=1)
    max_value = max(max_value, 0.01)
    rendered = []
    bar_accents = ("#62a8ff", "#4fc48b", "#f0c96a", "#b596ff", "#ff6f81")
    for index, row in enumerate(chart_rows, start=1):
        value = float(row.get(value_key, 0))
        width = max(2.0, min(100.0, value / max_value * 100))
        label_value = str(row.get(label_key, "-"))
        label_icon = ""
        label_modifier = ""
        if label_key == "champion" and label_value and label_value != "-":
            label_modifier = " bar-label-with-icon"
            label_icon = (
                f'<img class="bar-label-icon" src="{html_attr(champion_icon_url(label_value))}" '
                f'alt="{html_attr(label_value)}">'
            )
        footer = ""
        if footer_key:
            footer_value = row.get(footer_key, "")
            footer_text = (
                footer_formatter(footer_value)
                if footer_formatter is not None
                else str(footer_value)
            )
            footer = f"<small>{escape(footer_text)}</small>"
        rendered.append(
            f"""
            <div class="bar-row" data-rank="{index:02d}" style="--bar-accent: {bar_accents[(index - 1) % len(bar_accents)]};">
              <div class="bar-label{label_modifier}">
                <span class="bar-label-main">{label_icon}<span class="bar-label-text">{escape(label_value)}</span></span>
                {footer}
              </div>
              <div class="bar-track"><div class="bar-fill" style="width: {width:.2f}%"></div></div>
              <b>{escape(formatter(value))}</b>
            </div>
            """
        )
    section_class = "chart-panel"
    if class_name:
        section_class = f"{section_class} {class_name}"
    return f"""
    <section class="{html_attr(section_class)}">
      <h3>{escape(title)}</h3>
      <div class="bar-chart">{''.join(rendered)}</div>
    </section>
    """


def render_unplayed_champions_panel(rows: Sequence[dict[str, object]]) -> str:
    chips = "".join(
        f'<span class="champion-chip">{escape(str(row["champion"]))}</span>' for row in rows
    )
    if not chips:
        chips = '<span class="empty-list">Every current champion has been picked.</span>'
    played_count = len(CHAMPION_ROSTER) - len(rows)
    return f"""
    <section class="chart-panel unplayed-panel">
      <h3>Unplayed Champions</h3>
      <div class="unplayed-summary">
        <strong>{len(rows)}</strong>
        <span>not picked yet</span>
        <small>{played_count} of {len(CHAMPION_ROSTER)} current champions played</small>
      </div>
      <div class="champion-chip-list">{chips}</div>
      <small class="roster-source">
        Roster: <a href="{html_attr(CHAMPION_ROSTER_SOURCE_URL)}" target="_blank" rel="noreferrer">Data Dragon {escape(CHAMPION_ROSTER_VERSION)}</a>
      </small>
    </section>
    """


def interpolate_channel(start: int, end: int, amount: float) -> int:
    return round(start + (end - start) * amount)


def interpolate_color(start: tuple[int, int, int], end: tuple[int, int, int], amount: float) -> str:
    amount = max(0.0, min(1.0, amount))
    red = interpolate_channel(start[0], end[0], amount)
    green = interpolate_channel(start[1], end[1], amount)
    blue = interpolate_channel(start[2], end[2], amount)
    return f"rgb({red}, {green}, {blue})"


def heat_color(winrate: float) -> str:
    red = (214, 76, 92)
    yellow = (236, 177, 82)
    green = (42, 148, 111)
    if winrate < 0.5:
        return interpolate_color(red, yellow, winrate / 0.5)
    return interpolate_color(yellow, green, (winrate - 0.5) / 0.5)


def render_champion_role_heatmap(
    champion_rows: Sequence[dict[str, object]],
    champion_role_rows: Sequence[dict[str, object]],
    *,
    limit: int = 18,
) -> str:
    by_pair = {
        (str(row["champion"]), str(row["role"])): row for row in champion_role_rows
    }
    top_champions = list(champion_rows[:limit])
    header = "".join(f"<th>{role}</th>" for role in ROLE_ORDER)
    body = []
    for champion in top_champions:
        champion_name = str(champion["champion"])
        cells = []
        for role in ROLE_ORDER:
            row = by_pair.get((champion_name, role))
            if not row:
                cells.append('<td class="empty-cell" data-sort="-1">-</td>')
                continue
            winrate = float(row["winrate"])
            color = heat_color(winrate)
            text_color = heat_text_color(winrate)
            cells.append(
                f'<td style="background: {color}; color: {text_color}" '
                f'data-sort="{winrate:.4f}"><span>{pct(winrate)}</span>'
                f'<small>{row["games"]}g</small></td>'
            )
        body.append(
            f"""
            <tr>
              <th>{escape(champion_name)}<small>{champion["games"]} games</small></th>
              {''.join(cells)}
            </tr>
            """
        )
    return f"""
    <section class="table-panel heatmap-panel">
      <div class="section-heading"><h3>Champion Win Rate By Role</h3></div>
      <div class="table-wrap">
        <table class="heatmap-table">
          <thead><tr><th>Champion</th>{header}</tr></thead>
          <tbody>{''.join(body)}</tbody>
        </table>
      </div>
    </section>
    """


def render_player_role_heatmap(
    player_rows: Sequence[dict[str, object]],
    player_role_rows: Sequence[dict[str, object]],
) -> str:
    player_rows = without_spotlight_excluded_players(player_rows)
    player_role_rows = without_spotlight_excluded_players(player_role_rows)
    by_pair = {
        (str(row["name"]), str(row["role"])): row for row in player_role_rows
    }
    header = "".join(f"<th>{role}</th>" for role in ROLE_ORDER)
    body = []
    for player in player_rows:
        player_name = str(player["name"])
        cells = []
        for role in ROLE_ORDER:
            row = by_pair.get((player_name, role))
            if not row:
                cells.append('<td class="empty-cell" data-sort="-1">-</td>')
                continue
            winrate = float(row["winrate"])
            color = heat_color(winrate)
            text_color = heat_text_color(winrate)
            cells.append(
                f'<td style="background: {color}; color: {text_color}" '
                f'data-sort="{winrate:.4f}"><span>{pct(winrate)}</span>'
                f'<small>{row["games"]}g</small></td>'
            )
        body.append(
            f"""
            <tr>
              <th>{escape(player_name)}<small>{player["games"]} games</small></th>
              {''.join(cells)}
            </tr>
            """
        )
    return f"""
    <section class="table-panel heatmap-panel">
      <div class="section-heading"><h3>Player Win Rate By Role</h3></div>
      <div class="table-wrap">
        <table class="heatmap-table">
          <thead><tr><th>Player</th>{header}</tr></thead>
          <tbody>{''.join(body)}</tbody>
        </table>
      </div>
    </section>
    """


def role_breakdown_text(role_row: dict[str, object] | None) -> str:
    if not role_row:
        return "-"
    return f"{role_row['games']}g / {pct(float(role_row['winrate']))}"


def add_player_role_breakdowns(
    player_rows: Sequence[dict[str, object]],
    player_role_rows: Sequence[dict[str, object]],
) -> None:
    by_player_role = {
        (str(row["name"]), str(row["role"])): row for row in player_role_rows
    }
    for player in player_rows:
        for role in ROLE_ORDER:
            player[f"role_{role.lower()}"] = role_breakdown_text(
                by_player_role.get((str(player["name"]), role))
            )


def match_player_cell(row: Appearance, *, mirrored: bool = False) -> str:
    side_class = " mirrored" if mirrored else ""
    return (
        f'<span class="match-player-cell{side_class}">'
        f'<strong>{escape(row.name)}</strong><small>{escape(row.player)}</small>'
        f'</span>'
    )


def match_champion_cell(row: Appearance, *, mirrored: bool = False) -> str:
    champion = row.champion
    side_class = " mirrored" if mirrored else ""
    return (
        f'<span class="match-champion-cell{side_class}">'
        f'<img src="{html_attr(champion_icon_url(champion))}" alt="{html_attr(champion)}">'
        f'<span>{escape(champion)}</span>'
        f'</span>'
    )


def render_match_scoreboard(
    win_rows: Sequence[Appearance], lose_rows: Sequence[Appearance]
) -> str:
    win_by_role = {row.role: row for row in win_rows}
    lose_by_role = {row.role: row for row in lose_rows}
    body = []
    for role in ROLE_ORDER:
        win_row = win_by_role.get(role)
        lose_row = lose_by_role.get(role)
        if not win_row or not lose_row:
            continue
        body.append(
            f"""
            <tr>
              <td><span class="role-pill">{escape(win_row.role)}</span></td>
              <td>{match_player_cell(win_row)}</td>
              <td class="match-score-cell">{win_row.kills}/{win_row.deaths}/{win_row.assists}</td>
              <td class="match-kda-cell">{two_decimal(win_row.kda_ratio)}</td>
              <td>{match_champion_cell(win_row)}</td>
              <td class="match-versus-cell">vs</td>
              <td>{match_champion_cell(lose_row, mirrored=True)}</td>
              <td class="match-kda-cell">{two_decimal(lose_row.kda_ratio)}</td>
              <td class="match-score-cell">{lose_row.kills}/{lose_row.deaths}/{lose_row.assists}</td>
              <td>{match_player_cell(lose_row, mirrored=True)}</td>
              <td><span class="role-pill">{escape(lose_row.role)}</span></td>
            </tr>
            """
        )
    return f"""
    <div class="match-scoreboard">
      <div class="match-scoreboard-heading">
        <div class="winning-team">
          <h4>Winning Team</h4>
          <strong>{sum(row.kills for row in win_rows)} kills</strong>
        </div>
        <span>Head to Head</span>
        <div class="losing-team">
          <h4>Losing Team</h4>
          <strong>{sum(row.kills for row in lose_rows)} kills</strong>
        </div>
      </div>
      <div class="match-scoreboard-wrap">
        <table class="match-scoreboard-table">
          <colgroup>
            <col class="match-role-col">
            <col class="match-player-col">
            <col class="match-score-col">
            <col class="match-kda-col">
            <col class="match-champion-col">
            <col class="match-versus-col">
            <col class="match-champion-col">
            <col class="match-kda-col">
            <col class="match-score-col">
            <col class="match-player-col">
            <col class="match-role-col">
          </colgroup>
          <thead>
            <tr>
              <th>Role</th><th>Player</th><th>K/D/A</th><th>KDA</th><th>Champion</th>
              <th></th>
              <th>Champion</th><th>KDA</th><th>K/D/A</th><th>Player</th><th>Role</th>
            </tr>
          </thead>
          <tbody>{''.join(body)}</tbody>
        </table>
      </div>
    </div>
    """


def render_match_history(appearances: Sequence[Appearance]) -> str:
    grouped: dict[int, list[Appearance]] = defaultdict(list)
    for appearance in appearances:
        grouped[appearance.match_id].append(appearance)

    cards = []
    for match_id in sorted(grouped):
        rows = grouped[match_id]
        win_rows = [row for row in rows if row.win]
        lose_rows = [row for row in rows if not row.win]
        win_kills = sum(row.kills for row in win_rows)
        lose_kills = sum(row.kills for row in lose_rows)
        search_text = " ".join(
            [
                f"Match {match_id}",
                rows[0].date_label,
                rows[0].weekday_label,
                *(row.name for row in rows),
                *(row.player for row in rows),
                *(row.champion for row in rows),
                *(row.role for row in rows),
            ]
        )
        active_class = " active" if match_id == max(grouped) else ""
        match_label = f"Match {match_id} - {rows[0].weekday_label} {rows[0].date_label}"
        cards.append(
            f"""
            <article id="match-{match_id}" class="match-card{active_class}" data-match-id="{match_id}" data-match-label="{html_attr(match_label)}" data-card-text="{html_attr(search_text)}">
              <div class="match-card-heading">
                <div>
                  <h3>Match {match_id}</h3>
                  <small>{escape(rows[0].weekday_label)} {escape(rows[0].date_label)}</small>
                </div>
                <div class="match-score">
                  <span class="win-score">Win {win_kills}</span>
                  <span class="loss-score">Loss {lose_kills}</span>
                </div>
              </div>
              {render_match_scoreboard(win_rows, lose_rows)}
            </article>
            """
        )
    return "\n".join(cards)


def champion_pool_horizontal_svg(
    player_name: str, champion_rows: Sequence[dict[str, object]]
) -> str:
    row_height = 32
    top = 30
    icon_size = 24
    icon_x = 18
    left = 58
    right = 130
    width = 920
    chart_width = width - left - right
    height = top + 18 + max(1, len(champion_rows)) * row_height
    max_games = max((int(row["games"]) for row in champion_rows), default=1)
    bar_accents = ("#62a8ff", "#4fc48b", "#f0c96a", "#b596ff", "#ff6f81")
    parts = [
        f'<svg class="champ-pool-svg horizontal-chart" viewBox="0 0 {width} {height}" role="img" aria-label="{html_attr(player_name)} champion pool horizontal bar chart">'
    ]
    parts.append(
        f'<text x="{left}" y="19" class="pool-axis-label">Champion games played</text>'
    )
    parts.append(
        f'<text x="{left + chart_width + 16}" y="19" class="pool-axis-label">Games</text>'
    )
    parts.append(
        f'<text x="{width - 8}" y="19" class="pool-axis-label pool-axis-label-right">WR</text>'
    )
    for index, row in enumerate(champion_rows):
        games = int(row["games"])
        winrate = float(row["winrate"])
        y = top + index * row_height
        bar_y = y + 9
        icon_y = y + 2
        bar_width = max(4, games / max_games * chart_width)
        label = str(row["champion"])
        game_text = "game" if games == 1 else "games"
        accent = bar_accents[index % len(bar_accents)]
        clip_id = f"pool-icon-{svg_id_token(player_name)}-{index}"
        icon_url = champion_icon_url(label)
        parts.append(
            f'<g class="pool-row"><title>{escape(label)} - {games} {game_text}, {pct(winrate)} winrate</title>'
        )
        parts.append(
            f'<defs><clipPath id="{html_attr(clip_id)}"><rect x="{icon_x}" y="{icon_y}" width="{icon_size}" height="{icon_size}" rx="5"/></clipPath></defs>'
        )
        parts.append(
            f'<rect x="{icon_x - 1}" y="{icon_y - 1}" width="{icon_size + 2}" height="{icon_size + 2}" rx="6" class="pool-icon-frame"/>'
        )
        parts.append(
            f'<image href="{html_attr(icon_url)}" x="{icon_x}" y="{icon_y}" width="{icon_size}" height="{icon_size}" preserveAspectRatio="xMidYMid slice" clip-path="url(#{html_attr(clip_id)})"/>'
        )
        parts.append(
            f'<rect x="{left}" y="{bar_y}" width="{chart_width}" height="12" rx="6" class="pool-track"/>'
        )
        parts.append(
            f'<rect x="{left}" y="{bar_y}" width="{bar_width:.1f}" height="12" rx="6" class="pool-bar" style="fill: {accent};"/>'
        )
        parts.append(
            f'<text x="{left + chart_width + 18}" y="{bar_y + 10}" class="pool-value">{games}g</text>'
        )
        parts.append(
            f'<text x="{width - 8}" y="{bar_y + 10}" class="pool-winrate">{pct(winrate)}</text>'
        )
        parts.append("</g>")
    parts.append("</svg>")
    return "".join(parts)


def champion_pool_vertical_svg(
    player_name: str, champion_rows: Sequence[dict[str, object]]
) -> str:
    bar_width = 24
    gap = 14
    icon_size = 26
    left = 52
    top = 30
    chart_height = 214
    label_height = 46
    right = 34
    width = max(760, left + right + len(champion_rows) * (bar_width + gap))
    height = top + chart_height + label_height
    axis_y = top + chart_height
    max_games = max((int(row["games"]) for row in champion_rows), default=1)
    bar_accents = ("#62a8ff", "#4fc48b", "#f0c96a", "#b596ff", "#ff6f81")
    parts = [
        f'<svg class="champ-pool-svg vertical-chart" viewBox="0 0 {width} {height}" role="img" aria-label="{html_attr(player_name)} champion pool vertical bar chart">'
    ]
    parts.append(
        f'<line x1="{left - 12}" y1="{axis_y}" x2="{width - right}" y2="{axis_y}" class="svg-axis"/>'
    )
    for index, row in enumerate(champion_rows):
        games = int(row["games"])
        winrate = float(row["winrate"])
        bar_height = games / max_games * chart_height
        x = left + index * (bar_width + gap)
        y = axis_y - bar_height
        label = str(row["champion"])
        game_text = "game" if games == 1 else "games"
        accent = bar_accents[index % len(bar_accents)]
        icon_x = x + (bar_width - icon_size) / 2
        icon_y = axis_y + 10
        clip_id = f"pool-vertical-icon-{svg_id_token(player_name)}-{index}"
        icon_url = champion_icon_url(label)
        parts.append(
            f'<g class="pool-row"><title>{escape(label)} - {games} {game_text}, {pct(winrate)} winrate</title>'
        )
        parts.append(
            f'<rect x="{x}" y="{y:.1f}" width="{bar_width}" height="{bar_height:.1f}" rx="4" class="pool-bar" style="fill: {accent};"/>'
        )
        parts.append(
            f'<text x="{x + bar_width / 2}" y="{y - 8:.1f}" class="pool-value centered">{games}</text>'
        )
        parts.append(
            f'<defs><clipPath id="{html_attr(clip_id)}"><rect x="{icon_x:.1f}" y="{icon_y}" width="{icon_size}" height="{icon_size}" rx="5"/></clipPath></defs>'
        )
        parts.append(
            f'<rect x="{icon_x - 1:.1f}" y="{icon_y - 1}" width="{icon_size + 2}" height="{icon_size + 2}" rx="6" class="pool-icon-frame"/>'
        )
        parts.append(
            f'<image href="{html_attr(icon_url)}" x="{icon_x:.1f}" y="{icon_y}" width="{icon_size}" height="{icon_size}" preserveAspectRatio="xMidYMid slice" clip-path="url(#{html_attr(clip_id)})"/>'
        )
        parts.append("</g>")
    parts.append("</svg>")
    return "".join(parts)


def render_player_champion_pools(
    player_rows: Sequence[dict[str, object]],
    player_champion_rows: Sequence[dict[str, object]],
) -> str:
    player_rows = without_spotlight_excluded_players(player_rows)
    player_champion_rows = without_spotlight_excluded_players(player_champion_rows)
    rows_by_player: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in player_champion_rows:
        rows_by_player[str(row["name"])].append(row)

    player_order = sorted(
        player_rows,
        key=lambda row: (
            -int(int(row.get("games", 0)) >= MIN_PLAYER_GAMES),
            -float(row.get("champion_pool_rate", 0)),
            -int(row.get("unique_champions", 0)),
            -int(row.get("games", 0)),
            str(row.get("name", "")),
        ),
    )
    panels = []
    for index, player in enumerate(player_order, start=1):
        player_name = str(player["name"])
        champion_rows = sorted(
            rows_by_player.get(player_name, []),
            key=lambda row: (-int(row["games"]), -float(row["winrate"]), str(row["champion"])),
        )
        active_class = " active" if index == 1 else ""
        pool_rate = float(player.get("champion_pool_rate", 0))
        games_text = "game" if int(player["games"]) == 1 else "games"
        champion_text = "champion" if int(player["unique_champions"]) == 1 else "champions"
        pool_label = (
            f"{player_name} - {player['games']} {games_text}, "
            f"{player['unique_champions']} {champion_text}, {pct(pool_rate)} unique-pick rate"
        )
        search_text = " ".join([player_name, *(str(row["champion"]) for row in champion_rows)])
        panels.append(
            f"""
            <article class="player-pool-card{active_class}" data-player-pool-id="{index}" data-player-pool-label="{html_attr(pool_label)}" data-card-text="{html_attr(search_text)}">
              <div class="player-pool-heading">
                <h3>{escape(player_name)}</h3>
                <small>{player['games']} {games_text}, {player['unique_champions']} {champion_text}, {pct(pool_rate)} unique-pick rate</small>
              </div>
              <div class="champ-pool-chart">
                {champion_pool_horizontal_svg(player_name, champion_rows)}
                <div class="vertical-chart-wrap">
                  {champion_pool_vertical_svg(player_name, champion_rows)}
                </div>
              </div>
            </article>
            """
        )
    return "\n".join(panels)


def role_breakdown_svg(role_rows: Sequence[dict[str, object]]) -> str:
    width = 760
    height = 280
    padding = 52
    chart_width = width - padding * 2
    chart_height = height - padding * 2
    bar_gap = 18
    bar_width = (chart_width - bar_gap * (len(ROLE_ORDER) - 1)) / len(ROLE_ORDER)
    axis_y = padding + chart_height
    rows_by_role = {str(row["role"]): row for row in role_rows}
    parts = [
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Role winrate chart">'
    ]
    parts.append(f'<line x1="{padding}" y1="{axis_y}" x2="{width - padding}" y2="{axis_y}" class="svg-axis"/>')
    for index, role in enumerate(ROLE_ORDER):
        row = rows_by_role.get(role, {})
        winrate = float(row.get("winrate", 0))
        games = int(row.get("games", 0))
        bar_height = chart_height * winrate
        x = padding + index * (bar_width + bar_gap)
        y = axis_y - bar_height
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" '
            f'height="{bar_height:.1f}" rx="5" class="svg-role-bar"/>'
        )
        parts.append(
            f'<text x="{x + bar_width / 2:.1f}" y="{y - 10:.1f}" class="svg-value">{pct(winrate)}</text>'
        )
        parts.append(
            f'<text x="{x + bar_width / 2:.1f}" y="{axis_y + 24:.1f}" class="svg-label">{role}</text>'
        )
        parts.append(
            f'<text x="{x + bar_width / 2:.1f}" y="{axis_y + 43:.1f}" class="svg-sub">{games} games</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def daily_volume_svg(matches: Sequence[dict[str, object]]) -> str:
    counts = Counter(str(row["date_label"]) for row in matches)
    labels = list(counts.keys())
    values = list(counts.values())
    width = 760
    height = 230
    padding = 38
    if not values:
        return ""
    max_value = max(values)
    chart_width = width - padding * 2
    chart_height = height - padding * 2
    step = chart_width / max(1, len(values) - 1)
    points = []
    for index, value in enumerate(values):
        x = padding + index * step
        y = padding + chart_height - (value / max_value * chart_height)
        points.append((x, y, value, labels[index]))
    point_string = " ".join(f"{x:.1f},{y:.1f}" for x, y, _value, _label in points)
    parts = [
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Matches by date">',
        f'<polyline points="{point_string}" class="svg-line"/>',
    ]
    for x, y, value, label in points:
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" class="svg-dot"/>')
        if value == max_value:
            parts.append(
                f'<text x="{x:.1f}" y="{y - 12:.1f}" class="svg-value">{value} games</text>'
            )
    parts.append(f'<text x="{padding}" y="{height - 8}" class="svg-sub">{escape(labels[0])}</text>')
    parts.append(
        f'<text x="{width - padding}" y="{height - 8}" class="svg-sub end">{escape(labels[-1])}</text>'
    )
    parts.append("</svg>")
    return "".join(parts)


def weekday_volume_rows(matches: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    counts = Counter(str(row.get("weekday", "Unknown")) for row in matches)
    total = len(matches)
    return [
        {
            "weekday": weekday,
            "games": counts.get(weekday, 0),
            "share": safe_div(counts.get(weekday, 0), total),
        }
        for weekday in WEEKDAY_ORDER
    ]


def team_combo_rows(
    appearances: Sequence[Appearance], combo_size: int, minimum_games: int = 1
) -> list[dict[str, object]]:
    grouped: dict[tuple[int, str], set[str]] = defaultdict(set)
    for appearance in appearances:
        grouped[(appearance.match_id, appearance.side)].add(appearance.name)

    stats: dict[tuple[str, ...], dict[str, int]] = defaultdict(lambda: {"games": 0, "wins": 0})
    for (_match_id, side), names in grouped.items():
        if len(names) < combo_size:
            continue
        for combo in combinations(sorted(names), combo_size):
            stats[combo]["games"] += 1
            stats[combo]["wins"] += 1 if side == "win" else 0

    rows = []
    for combo, values in stats.items():
        games = values["games"]
        if games < minimum_games:
            continue
        wins = values["wins"]
        losses = games - wins
        rows.append(
            {
                "combo": " + ".join(combo),
                "players": combo,
                "games": games,
                "wins": wins,
                "losses": losses,
                "winrate": safe_div(wins, games),
                "footer": f"{wins}-{losses}, {games} games",
            }
        )
    return sorted(
        rows,
        key=lambda row: (
            -float(row["winrate"]),
            -int(row["wins"]),
            -int(row["games"]),
            str(row["combo"]),
        ),
    )


def head_to_head_rows(
    appearances: Sequence[Appearance], minimum_games: int = 1
) -> list[dict[str, object]]:
    grouped: dict[int, list[Appearance]] = defaultdict(list)
    for appearance in appearances:
        if is_spotlight_excluded_player(appearance.name):
            continue
        grouped[appearance.match_id].append(appearance)

    stats: dict[tuple[str, str, str], dict[str, object]] = {}
    for rows in grouped.values():
        rows_by_role: dict[str, dict[str, list[Appearance]]] = {
            role: {"win": [], "lose": []} for role in ROLE_ORDER
        }
        for row in rows:
            if row.role not in ROLE_ORDER:
                continue
            rows_by_role[row.role][row.side].append(row)

        for role, sides in rows_by_role.items():
            for win_row in sides["win"]:
                for lose_row in sides["lose"]:
                    names = tuple(sorted([win_row.name, lose_row.name]))
                    key = (role, names[0], names[1])
                    if key not in stats:
                        stats[key] = {
                            "role": role,
                            "players": names,
                            "games": 0,
                            "wins": Counter(),
                            "kills": Counter(),
                            "deaths": Counter(),
                            "assists": Counter(),
                            "champions": defaultdict(Counter),
                            "match_ids": [],
                        }
                    entry = stats[key]
                    entry["games"] = int(entry["games"]) + 1
                    entry["wins"][win_row.name] += 1
                    entry["match_ids"].append(win_row.match_id)
                    for player_row in (win_row, lose_row):
                        name = player_row.name
                        entry["kills"][name] += player_row.kills
                        entry["deaths"][name] += player_row.deaths
                        entry["assists"][name] += player_row.assists
                        entry["champions"][name][player_row.champion] += 1

    rows = []
    for entry in stats.values():
        games = int(entry["games"])
        if games < minimum_games:
            continue
        player_a, player_b = entry["players"]
        a_wins = int(entry["wins"][player_a])
        b_wins = int(entry["wins"][player_b])
        if (b_wins, player_a) > (a_wins, player_b):
            leader, opponent = player_b, player_a
            wins, losses = b_wins, a_wins
        else:
            leader, opponent = player_a, player_b
            wins, losses = a_wins, b_wins

        leader_kills = int(entry["kills"][leader])
        leader_deaths = int(entry["deaths"][leader])
        leader_assists = int(entry["assists"][leader])
        opponent_kills = int(entry["kills"][opponent])
        opponent_deaths = int(entry["deaths"][opponent])
        opponent_assists = int(entry["assists"][opponent])
        winrate = safe_div(wins, games)
        opponent_winrate = safe_div(losses, games)
        leader_champions = top_counter(entry["champions"][leader])
        opponent_champions = top_counter(entry["champions"][opponent])
        rows.append(
            {
                "role": str(entry["role"]),
                "player": leader,
                "opponent": opponent,
                "matchup": f"{leader} vs {opponent}",
                "chart_label": (
                    f"{leader} over {opponent}"
                    if wins != losses
                    else f"{leader} vs {opponent}"
                ),
                "games": games,
                "wins": wins,
                "losses": losses,
                "record": f"{wins}-{losses}",
                "winrate": winrate,
                "opponent_winrate": opponent_winrate,
                "dominance": abs(winrate - 0.5),
                "player_kda": safe_div(leader_kills + leader_assists, max(1, leader_deaths)),
                "opponent_kda": safe_div(
                    opponent_kills + opponent_assists, max(1, opponent_deaths)
                ),
                "player_line": (
                    f"{one_decimal(safe_div(leader_kills, games))} / "
                    f"{one_decimal(safe_div(leader_deaths, games))} / "
                    f"{one_decimal(safe_div(leader_assists, games))}"
                ),
                "opponent_line": (
                    f"{one_decimal(safe_div(opponent_kills, games))} / "
                    f"{one_decimal(safe_div(opponent_deaths, games))} / "
                    f"{one_decimal(safe_div(opponent_assists, games))}"
                ),
                "player_champions": leader_champions,
                "opponent_champions": opponent_champions,
                "match_ids": ", ".join(str(match_id) for match_id in entry["match_ids"]),
            }
        )
    return sorted(
        rows,
        key=lambda row: (
            -int(row["games"]),
            -float(row["dominance"]),
            -float(row["winrate"]),
            str(row["role"]),
            str(row["matchup"]),
        ),
    )


def champion_head_to_head_rows(
    appearances: Sequence[Appearance], minimum_games: int = 1
) -> list[dict[str, object]]:
    grouped: dict[int, list[Appearance]] = defaultdict(list)
    for appearance in appearances:
        if is_spotlight_excluded_player(appearance.name):
            continue
        grouped[appearance.match_id].append(appearance)

    stats: dict[tuple[str, str, str], dict[str, object]] = {}
    for rows in grouped.values():
        rows_by_role: dict[str, dict[str, list[Appearance]]] = {
            role: {"win": [], "lose": []} for role in ROLE_ORDER
        }
        for row in rows:
            if row.role in ROLE_ORDER:
                rows_by_role[row.role][row.side].append(row)

        for role, sides in rows_by_role.items():
            for win_row in sides["win"]:
                for lose_row in sides["lose"]:
                    champions = tuple(sorted([win_row.champion, lose_row.champion]))
                    if champions[0] == champions[1]:
                        continue
                    key = (role, champions[0], champions[1])
                    if key not in stats:
                        stats[key] = {
                            "role": role,
                            "champions": champions,
                            "games": 0,
                            "wins": Counter(),
                            "kills": Counter(),
                            "deaths": Counter(),
                            "assists": Counter(),
                            "pilots": defaultdict(Counter),
                            "match_ids": [],
                        }
                    entry = stats[key]
                    entry["games"] = int(entry["games"]) + 1
                    entry["wins"][win_row.champion] += 1
                    entry["match_ids"].append(win_row.match_id)
                    for champion_row in (win_row, lose_row):
                        champion = champion_row.champion
                        entry["kills"][champion] += champion_row.kills
                        entry["deaths"][champion] += champion_row.deaths
                        entry["assists"][champion] += champion_row.assists
                        entry["pilots"][champion][champion_row.name] += 1

    output_rows = []
    for entry in stats.values():
        games = int(entry["games"])
        if games < minimum_games:
            continue
        champion_a, champion_b = entry["champions"]
        a_wins = int(entry["wins"][champion_a])
        b_wins = int(entry["wins"][champion_b])
        if (b_wins, champion_a) > (a_wins, champion_b):
            leader, opponent = champion_b, champion_a
            wins, losses = b_wins, a_wins
        else:
            leader, opponent = champion_a, champion_b
            wins, losses = a_wins, b_wins

        leader_kills = int(entry["kills"][leader])
        leader_deaths = int(entry["deaths"][leader])
        leader_assists = int(entry["assists"][leader])
        opponent_kills = int(entry["kills"][opponent])
        opponent_deaths = int(entry["deaths"][opponent])
        opponent_assists = int(entry["assists"][opponent])
        leader_kda = safe_div(leader_kills + leader_assists, max(1, leader_deaths))
        opponent_kda = safe_div(
            opponent_kills + opponent_assists, max(1, opponent_deaths)
        )
        winrate = safe_div(wins, games)
        output_rows.append(
            {
                "role": str(entry["role"]),
                "champion": leader,
                "opponent_champion": opponent,
                "matchup": f"{leader} vs {opponent}",
                "chart_label": (
                    f"{leader} over {opponent}"
                    if wins != losses
                    else f"{leader} vs {opponent}"
                ),
                "games": games,
                "wins": wins,
                "losses": losses,
                "record": f"{wins}-{losses}",
                "winrate": winrate,
                "dominance": abs(winrate - 0.5),
                "champion_kda": leader_kda,
                "opponent_kda": opponent_kda,
                "kda_edge": leader_kda - opponent_kda,
                "champion_line": (
                    f"{one_decimal(safe_div(leader_kills, games))} / "
                    f"{one_decimal(safe_div(leader_deaths, games))} / "
                    f"{one_decimal(safe_div(leader_assists, games))}"
                ),
                "opponent_line": (
                    f"{one_decimal(safe_div(opponent_kills, games))} / "
                    f"{one_decimal(safe_div(opponent_deaths, games))} / "
                    f"{one_decimal(safe_div(opponent_assists, games))}"
                ),
                "champion_pilots": top_counter(entry["pilots"][leader]),
                "opponent_pilots": top_counter(entry["pilots"][opponent]),
                "match_ids": ", ".join(str(match_id) for match_id in entry["match_ids"]),
            }
        )

    return sorted(
        output_rows,
        key=lambda row: (
            -int(row["games"]),
            -float(row["dominance"]),
            -float(row["kda_edge"]),
            str(row["role"]),
            str(row["matchup"]),
        ),
    )


def pilot_champion_head_to_head_rows(
    appearances: Sequence[Appearance], minimum_games: int = 1
) -> list[dict[str, object]]:
    grouped: dict[int, list[Appearance]] = defaultdict(list)
    for appearance in appearances:
        if is_spotlight_excluded_player(appearance.name):
            continue
        grouped[appearance.match_id].append(appearance)

    stats: dict[tuple[str, str, str], dict[str, object]] = {}
    for rows in grouped.values():
        rows_by_role: dict[str, dict[str, list[Appearance]]] = {
            role: {"win": [], "lose": []} for role in ROLE_ORDER
        }
        for row in rows:
            if row.role in ROLE_ORDER:
                rows_by_role[row.role][row.side].append(row)

        for role, sides in rows_by_role.items():
            for win_row in sides["win"]:
                for lose_row in sides["lose"]:
                    win_entity = f"{win_row.name} on {win_row.champion}"
                    lose_entity = f"{lose_row.name} on {lose_row.champion}"
                    entities = tuple(sorted([win_entity, lose_entity]))
                    key = (role, entities[0], entities[1])
                    if key not in stats:
                        stats[key] = {
                            "role": role,
                            "entities": entities,
                            "games": 0,
                            "wins": Counter(),
                            "kills": Counter(),
                            "deaths": Counter(),
                            "assists": Counter(),
                            "match_ids": [],
                        }
                    entry = stats[key]
                    entry["games"] = int(entry["games"]) + 1
                    entry["wins"][win_entity] += 1
                    entry["match_ids"].append(win_row.match_id)
                    for entity, row in ((win_entity, win_row), (lose_entity, lose_row)):
                        entry["kills"][entity] += row.kills
                        entry["deaths"][entity] += row.deaths
                        entry["assists"][entity] += row.assists

    output_rows = []
    for entry in stats.values():
        games = int(entry["games"])
        if games < minimum_games:
            continue
        entity_a, entity_b = entry["entities"]
        a_wins = int(entry["wins"][entity_a])
        b_wins = int(entry["wins"][entity_b])
        if (b_wins, entity_a) > (a_wins, entity_b):
            leader, opponent = entity_b, entity_a
            wins, losses = b_wins, a_wins
        else:
            leader, opponent = entity_a, entity_b
            wins, losses = a_wins, b_wins
        leader_kda = safe_div(
            int(entry["kills"][leader]) + int(entry["assists"][leader]),
            max(1, int(entry["deaths"][leader])),
        )
        opponent_kda = safe_div(
            int(entry["kills"][opponent]) + int(entry["assists"][opponent]),
            max(1, int(entry["deaths"][opponent])),
        )
        output_rows.append(
            {
                "role": str(entry["role"]),
                "entity": leader,
                "opponent_entity": opponent,
                "games": games,
                "wins": wins,
                "losses": losses,
                "record": f"{wins}-{losses}",
                "winrate": safe_div(wins, games),
                "kda_edge": leader_kda - opponent_kda,
                "entity_kda": leader_kda,
                "opponent_kda": opponent_kda,
                "match_ids": ", ".join(str(match_id) for match_id in entry["match_ids"]),
            }
        )
    return sorted(
        output_rows,
        key=lambda row: (
            -int(row["games"]),
            -float(row["winrate"]),
            -float(row["kda_edge"]),
            str(row["role"]),
            str(row["entity"]),
        ),
    )


def worst_combo_rows(rows: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    return sorted(
        rows,
        key=lambda row: (
            float(row["winrate"]),
            -int(row["losses"]),
            -int(row["games"]),
            str(row["combo"]),
        ),
    )


def render_combo_list(
    rows: Sequence[dict[str, object]],
    minimum_games: int,
    *,
    limit: int = 10,
    mode: str = "best",
) -> str:
    visible_rows = list(rows[:limit])
    rendered = []
    if mode == "worst":
        bar_accents = ("#ff6f81", "#ff8a6a", "#f0c96a", "#ff9aa7", "#b596ff")
    else:
        bar_accents = ("#4fc48b", "#62a8ff", "#f0c96a", "#b596ff", "#ff6f81")
    row_class = "combo-row combo-row-worst" if mode == "worst" else "combo-row"
    for index, row in enumerate(visible_rows, start=1):
        winrate = float(row["winrate"])
        width_value = 1 - winrate if mode == "worst" else winrate
        width = max(2.0, width_value * 100)
        rendered.append(
            f"""
            <div class="{row_class}" data-rank="{index:02d}" style="--bar-accent: {bar_accents[(index - 1) % len(bar_accents)]};">
              <div class="combo-label">
                <span>{escape(str(row["combo"]))}</span>
                <small>{escape(str(row["footer"]))}</small>
              </div>
              <div class="bar-track"><div class="bar-fill" style="width: {width:.2f}%"></div></div>
              <b>{pct(winrate)}</b>
            </div>
            """
        )
    if not rendered:
        rendered.append(
            f"""
            <div class="empty-state">
              No combinations have reached {minimum_games} games yet.
            </div>
            """
        )
    return "".join(rendered)


def render_combo_comparison(
    title: str, rows: Sequence[dict[str, object]], minimum_games: int, limit: int = 10
) -> str:
    best_rows = list(rows[:limit])
    worst_rows = worst_combo_rows(rows)[:limit]
    return f"""
    <section class="chart-panel combo-comparison-panel">
      <div class="combo-comparison-heading">
        <h3>{escape(title)}</h3>
        <p class="chart-note">Minimum sample: {minimum_games} games</p>
      </div>
      <div class="combo-compare-grid">
        <div class="combo-compare-column combo-compare-best">
          <h4>Best {escape(title)}</h4>
          <div class="combo-chart">{render_combo_list(best_rows, minimum_games, limit=limit, mode="best")}</div>
        </div>
        <div class="combo-compare-column combo-compare-worst">
          <h4>Worst {escape(title)}</h4>
          <div class="combo-chart">{render_combo_list(worst_rows, minimum_games, limit=limit, mode="worst")}</div>
        </div>
      </div>
    </section>
    """


def render_head_to_head_css() -> str:
    return """
    .h2h-filter-panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
      padding: 14px;
    }
    .h2h-filter-row {
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }
    .h2h-filter-row + .h2h-filter-row {
      margin-top: 12px;
      padding-top: 12px;
      border-top: 1px solid var(--line);
    }
    .h2h-filter-row strong {
      min-width: 58px;
      color: var(--muted);
      font-size: 0.78rem;
      text-transform: uppercase;
    }
    .h2h-filter-button {
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #101924;
      color: var(--ink);
      cursor: pointer;
      font-weight: 850;
      padding: 8px 10px;
    }
    .h2h-filter-button.active {
      background: rgba(79, 196, 139, 0.16);
      border-color: #3fa477;
      color: #8ee1b8;
    }
    .h2h-count {
      margin-left: auto;
      color: var(--muted);
      font-weight: 800;
    }
    .h2h-highlight-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 14px;
      margin-top: 16px;
    }
    .h2h-highlight-card {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
      padding: 16px;
      min-height: 142px;
    }
    .h2h-highlight-card span {
      color: var(--muted);
      display: block;
      font-size: 0.78rem;
      font-weight: 900;
      text-transform: uppercase;
    }
    .h2h-highlight-card strong {
      display: block;
      font-size: 1.1rem;
      margin-top: 8px;
    }
    .h2h-highlight-card strong .h2h-champion-label {
      display: inline-flex;
      margin: 0 3px 0 0;
      vertical-align: middle;
    }
    .h2h-highlight-card em {
      color: var(--muted);
      font-style: normal;
      margin: 0 4px;
    }
    .h2h-highlight-card b {
      color: var(--gold);
      display: block;
      font-size: 1.35rem;
      margin-top: 8px;
    }
    .h2h-highlight-card small {
      color: var(--muted);
      display: block;
      line-height: 1.35;
      margin-top: 8px;
    }
    .h2h-layout {
      display: grid;
      grid-template-columns: minmax(0, 1fr);
      gap: 16px;
    }
    .h2h-chart {
      display: grid;
      gap: 10px;
    }
    .h2h-chart-row {
      display: grid;
      grid-template-columns: minmax(210px, 1.1fr) minmax(220px, 2fr) 86px;
      align-items: center;
      gap: 12px;
      padding: 8px 0;
    }
    .h2h-chart-label strong,
    .h2h-chart-label small {
      display: block;
    }
    .h2h-chart-label small {
      color: var(--muted);
      margin-top: 2px;
    }
    .h2h-track {
      height: 12px;
      overflow: hidden;
      border-radius: 999px;
      background: #223044;
    }
    .h2h-fill {
      height: 100%;
      min-width: 3%;
      border-radius: inherit;
      background: linear-gradient(90deg, #4fc48b, #f0c96a);
    }
    .h2h-chart-row b {
      color: var(--ink);
      font-variant-numeric: tabular-nums;
      text-align: right;
    }
    .h2h-heatmap-section {
      margin-top: 18px;
    }
    .h2h-heatmap-grid {
      display: grid;
      gap: 16px;
    }
    .h2h-role-heatmap {
      margin: 0;
    }
    .h2h-role-heatmap .table-wrap {
      max-height: 680px;
      overflow: auto;
      overscroll-behavior: contain;
    }
    .h2h-matrix {
      table-layout: fixed;
      width: max-content;
      min-width: 100%;
    }
    .h2h-matrix col.h2h-row-col {
      width: 156px;
    }
    .h2h-matrix col.h2h-value-col {
      width: 76px;
    }
    .h2h-matrix th,
    .h2h-matrix td {
      width: 76px;
      min-width: 76px;
      max-width: 76px;
      padding: 6px 7px;
      line-height: 1.1;
      overflow: hidden;
      text-align: center;
      white-space: nowrap;
    }
    .h2h-matrix th:first-child {
      left: 0;
      width: 156px;
      min-width: 156px;
      max-width: 156px;
      position: sticky;
      text-align: left;
      z-index: 2;
    }
    .h2h-matrix thead th {
      height: 78px;
      padding: 6px 5px;
      position: sticky;
      top: 0;
      vertical-align: bottom;
      z-index: 3;
    }
    .h2h-matrix thead th:first-child {
      z-index: 4;
    }
    .h2h-column-name,
    .h2h-row-name,
    .h2h-row-games {
      display: block;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .h2h-column-name {
      color: var(--ink);
      font-size: 0.72rem;
      line-height: 1.15;
      margin: 0 auto;
      max-width: 64px;
      text-transform: none;
    }
    .h2h-row-name {
      max-width: 130px;
    }
    .h2h-row-games {
      max-width: 130px;
    }
    .h2h-heatmap-cell span,
    .h2h-heatmap-cell small {
      display: block;
    }
    .h2h-heatmap-cell span {
      font-size: 0.84rem;
      font-weight: 950;
      letter-spacing: 0;
    }
    .h2h-heatmap-cell small {
      font-size: 0.62rem;
      opacity: 0.86;
      margin-top: 1px;
    }
    .h2h-heatmap-cell .h2h-cell-games {
      opacity: 0.72;
    }
    @media (max-width: 760px) {
      .h2h-matrix col.h2h-row-col {
        width: 132px;
      }
      .h2h-matrix col.h2h-value-col {
        width: 66px;
      }
      .h2h-matrix th,
      .h2h-matrix td {
        width: 66px;
        min-width: 66px;
        max-width: 66px;
        padding: 5px 5px;
      }
      .h2h-matrix th:first-child {
        width: 132px;
        min-width: 132px;
        max-width: 132px;
      }
      .h2h-column-name {
        max-width: 56px;
        font-size: 0.68rem;
      }
      .h2h-row-name,
      .h2h-row-games {
        max-width: 108px;
      }
    }
    .h2h-empty {
      display: none;
    }
    .h2h-table-player {
      min-width: 120px;
    }
    .h2h-champion-label {
      align-items: center;
      display: inline-flex;
      gap: 7px;
      min-width: 0;
    }
    .h2h-champion-label img {
      border-radius: 6px;
      height: 28px;
      object-fit: cover;
      width: 28px;
    }
    .h2h-champion-label span {
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    @media (max-width: 1040px) {
      .h2h-highlight-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }
    }
    @media (max-width: 720px) {
      .h2h-highlight-grid {
        grid-template-columns: 1fr;
      }
      .h2h-chart-row {
        grid-template-columns: minmax(0, 1fr) 72px;
      }
      .h2h-track {
        grid-column: 1 / -1;
        grid-row: 2;
      }
      .h2h-filter-row strong,
      .h2h-count {
        width: 100%;
        margin-left: 0;
      }
    }
    """


def render_head_to_head_script() -> str:
    return """
    const h2hState = { role: "all", player: "all" };
    const h2hItems = Array.from(document.querySelectorAll("[data-h2h-item]"));
    const h2hChampionItems = Array.from(document.querySelectorAll("[data-h2h-champion-item]"));
    const h2hPilotChampionItems = Array.from(document.querySelectorAll("[data-h2h-pilot-champion-item]"));
    const h2hHeatmapRows = Array.from(document.querySelectorAll("[data-h2h-heatmap-row]"));
    const h2hCount = document.querySelector("[data-h2h-count]");
    const h2hEmpty = document.querySelector("[data-h2h-empty]");

    function h2hMatches(item) {
      const roleMatches = h2hState.role === "all" || item.dataset.h2hRole === h2hState.role;
      const players = (item.dataset.h2hPlayers || "").split("|||");
      const playerMatches = h2hState.player === "all" || players.includes(h2hState.player);
      return roleMatches && playerMatches;
    }

    function updateH2hFilters() {
      let visible = 0;
      h2hItems.forEach(item => {
        const matches = h2hMatches(item);
        item.style.display = matches ? "" : "none";
        if (matches && item.matches("[data-h2h-table-row]")) visible += 1;
      });
      h2hHeatmapRows.forEach(row => {
        const roleMatches = h2hState.role === "all" || row.dataset.h2hRole === h2hState.role;
        const playerMatches = h2hState.player === "all" || row.dataset.h2hHeatmapPlayer === h2hState.player;
        row.style.display = roleMatches && playerMatches ? "" : "none";
      });
      h2hChampionItems.forEach(item => {
        const roleMatches = h2hState.role === "all" || item.dataset.h2hRole === h2hState.role;
        item.style.display = roleMatches ? "" : "none";
      });
      h2hPilotChampionItems.forEach(item => {
        const roleMatches = h2hState.role === "all" || item.dataset.h2hRole === h2hState.role;
        const playerMatches = h2hState.player === "all" || (item.dataset.h2hPlayers || "").split("|").includes(h2hState.player);
        item.style.display = roleMatches && playerMatches ? "" : "none";
      });
      document.querySelectorAll("[data-h2h-role-filter]").forEach(button => {
        button.classList.toggle("active", button.dataset.h2hRoleFilter === h2hState.role);
      });
      document.querySelectorAll("[data-h2h-player-filter]").forEach(button => {
        button.classList.toggle("active", button.dataset.h2hPlayerFilter === h2hState.player);
      });
      if (h2hCount) h2hCount.textContent = `${visible} matchups`;
      if (h2hEmpty) h2hEmpty.style.display = visible ? "none" : "block";
    }

    document.querySelectorAll("[data-h2h-role-filter]").forEach(button => {
      button.addEventListener("click", () => {
        const value = button.dataset.h2hRoleFilter;
        h2hState.role = h2hState.role === value && value !== "all" ? "all" : value;
        updateH2hFilters();
      });
    });

    document.querySelectorAll("[data-h2h-player-filter]").forEach(button => {
      button.addEventListener("click", () => {
        const value = button.dataset.h2hPlayerFilter;
        h2hState.player = h2hState.player === value && value !== "all" ? "all" : value;
        updateH2hFilters();
      });
    });

    function compareH2hCells(a, b, type, direction) {
      const av = a?.dataset.sort || a?.textContent || "";
      const bv = b?.dataset.sort || b?.textContent || "";
      let result;
      if (type === "number") {
        const aNumber = Number(av);
        const bNumber = Number(bv);
        result = Number.isFinite(aNumber) && Number.isFinite(bNumber)
          ? aNumber - bNumber
          : av.localeCompare(bv, undefined, { numeric: true, sensitivity: "base" });
      } else {
        result = av.localeCompare(bv, undefined, { numeric: true, sensitivity: "base" });
      }
      return direction === "asc" ? result : -result;
    }

    document.querySelectorAll(".h2h-sortable th").forEach(th => {
      th.addEventListener("click", () => {
        const table = th.closest("table");
        const tbody = table.querySelector("tbody");
        const index = Array.from(th.parentElement.children).indexOf(th);
        const currentDirection = th.classList.contains("sorted-asc") ? "asc" : "desc";
        const nextDirection = currentDirection === "asc" ? "desc" : "asc";
        table.querySelectorAll("th").forEach(header => header.classList.remove("sorted-asc", "sorted-desc"));
        th.classList.add(nextDirection === "asc" ? "sorted-asc" : "sorted-desc");
        Array.from(tbody.querySelectorAll("tr"))
          .sort((left, right) => compareH2hCells(left.children[index], right.children[index], th.dataset.type, nextDirection))
          .forEach(row => tbody.appendChild(row));
        updateH2hFilters();
      });
    });

    updateH2hFilters();
    """


def h2h_filter_attrs(role: object, players: Iterable[object]) -> str:
    players_value = "|||".join(str(player) for player in players if str(player))
    return (
        f'data-h2h-item data-h2h-role="{html_attr(role)}" '
        f'data-h2h-players="{html_attr(players_value)}"'
    )


def h2h_item_attrs(row: dict[str, object]) -> str:
    return h2h_filter_attrs(
        row.get("role", ""), [row.get("player", ""), row.get("opponent", "")]
    )


def h2h_champion_item_attrs(row: dict[str, object]) -> str:
    return (
        f'data-h2h-champion-item data-h2h-role="{html_attr(row.get("role", ""))}"'
    )


def h2h_pilot_champion_item_attrs(row: dict[str, object]) -> str:
    players = sorted(
        {
            str(row.get("entity", "")).split(" on ", 1)[0],
            str(row.get("opponent_entity", "")).split(" on ", 1)[0],
        }
    )
    return (
        f'data-h2h-pilot-champion-item data-h2h-role="{html_attr(row.get("role", ""))}" '
        f'data-h2h-players="{html_attr("|".join(players))}"'
    )


def render_h2h_champion_label(champion: object) -> str:
    champion_name = str(champion or "-")
    if champion_name == "-":
        return "-"
    return (
        f'<span class="h2h-champion-label">'
        f'<img src="{html_attr(champion_icon_url(champion_name))}" alt="{html_attr(champion_name)}">'
        f'<span>{escape(champion_name)}</span>'
        f"</span>"
    )


def render_head_to_head_heatmaps(rows: Sequence[dict[str, object]]) -> str:
    role_sections = []
    for role in ROLE_ORDER:
        role_rows = [row for row in rows if str(row.get("role", "")) == role]
        if not role_rows:
            continue

        player_games: Counter[str] = Counter()
        for row in role_rows:
            games = int(row.get("games", 0))
            player_games[str(row.get("player", ""))] += games
            player_games[str(row.get("opponent", ""))] += games

        players = [
            name
            for name, _games in sorted(
                player_games.items(), key=lambda item: (-item[1], item[0])
            )
            if name
        ]
        by_pair = {
            tuple(sorted([str(row.get("player", "")), str(row.get("opponent", ""))])): row
            for row in role_rows
        }

        header = "".join(
            f'<th class="h2h-column-header" title="{html_attr(player)}">'
            f'<span class="h2h-column-name">{escape(player)}</span></th>'
            for player in players
        )
        colgroup = (
            '<colgroup><col class="h2h-row-col">'
            + "".join('<col class="h2h-value-col">' for _player in players)
            + "</colgroup>"
        )
        body = []
        for player in players:
            cells = []
            for opponent in players:
                if player == opponent:
                    cells.append('<td class="empty-cell" data-sort="-1">-</td>')
                    continue
                row = by_pair.get(tuple(sorted([player, opponent])))
                if not row:
                    cells.append('<td class="empty-cell" data-sort="-1">-</td>')
                    continue

                player_is_leader = player == str(row.get("player", ""))
                wins = int(row.get("wins", 0) if player_is_leader else row.get("losses", 0))
                losses = int(
                    row.get("losses", 0) if player_is_leader else row.get("wins", 0)
                )
                games = int(row.get("games", 0))
                winrate = safe_div(wins, games)
                color = heat_color(winrate)
                text_color = heat_text_color(winrate)
                compact_winrate = pct(winrate).replace(".0%", "%")
                cells.append(
                    f'<td class="h2h-heatmap-cell" style="background: {color}; color: {text_color}" '
                    f'data-sort="{winrate:.4f}" title="{html_attr(player)} vs {html_attr(opponent)}: {wins}-{losses} over {games} games ({html_attr(compact_winrate)})">'
                    f'<span>{wins}-{losses}</span><small>{escape(compact_winrate)}</small><small class="h2h-cell-games">{games}g</small></td>'
                )
            body.append(
                f"""
                <tr data-h2h-heatmap-row data-h2h-role="{html_attr(role)}" data-h2h-heatmap-player="{html_attr(player)}">
                  <th title="{html_attr(player)}">
                    <span class="h2h-row-name">{escape(player)}</span>
                    <small class="h2h-row-games">{integer(player_games[player])} games</small>
                  </th>
                  {''.join(cells)}
                </tr>
                """
            )

        role_sections.append(
            f"""
            <section class="table-panel h2h-role-heatmap" {h2h_filter_attrs(role, players)}>
              <div class="section-heading">
                <h3>{escape(role)} Head To Head Heatmap</h3>
                <small>Cells show player record against the column opponent</small>
              </div>
              <div class="table-wrap">
                <table class="heatmap-table h2h-matrix">
                  {colgroup}
                  <thead><tr><th>Player</th>{header}</tr></thead>
                  <tbody>{''.join(body)}</tbody>
                </table>
              </div>
            </section>
            """
        )

    if not role_sections:
        return ""

    return f"""
    <section class="h2h-heatmap-section">
      <div class="section-title">
        <div>
          <h3>Role Head To Head Heatmaps</h3>
          <p class="note">Each role gets its own matrix. Row player score is shown against the player in the column.</p>
        </div>
      </div>
      <div class="h2h-heatmap-grid">{''.join(role_sections)}</div>
    </section>
    """


def render_head_to_head_highlight(
    title: str, row: dict[str, object], detail: str
) -> str:
    return f"""
    <article class="h2h-highlight-card" {h2h_item_attrs(row)}>
      <span>{escape(title)}</span>
      <strong>{escape(str(row.get("chart_label", "-")))}</strong>
      <b>{escape(pct(float(row.get("winrate", 0))))}</b>
      <small>{escape(detail)}</small>
    </article>
    """


def render_head_to_head_table(rows: Sequence[dict[str, object]]) -> str:
    body = []
    for row in rows:
        winrate = float(row.get("winrate", 0))
        body.append(
            f"""
            <tr {h2h_item_attrs(row)} data-h2h-table-row>
              <td data-sort="{html_attr(row.get('role', ''))}"><span class="role-pill">{escape(str(row.get('role', '')))}</span></td>
              <td class="h2h-table-player name-cell" data-sort="{html_attr(row.get('player', ''))}">{escape(str(row.get('player', '')))}</td>
              <td class="h2h-table-player name-cell" data-sort="{html_attr(row.get('opponent', ''))}">{escape(str(row.get('opponent', '')))}</td>
              <td class="number-cell" data-sort="{int(row.get('games', 0))}">{integer(row.get('games', 0))}</td>
              <td class="number-cell" data-sort="{int(row.get('wins', 0))}">{escape(str(row.get('record', '')))}</td>
              {heat_table_cell(pct(winrate), winrate, winrate)}
              <td class="number-cell" data-sort="{float(row.get('player_kda', 0))}">{two_decimal(float(row.get('player_kda', 0)))}</td>
              <td class="number-cell" data-sort="{float(row.get('opponent_kda', 0))}">{two_decimal(float(row.get('opponent_kda', 0)))}</td>
              <td data-sort="{html_attr(row.get('player_champions', ''))}">{escape(str(row.get('player_champions', '-')))}</td>
              <td data-sort="{html_attr(row.get('opponent_champions', ''))}">{escape(str(row.get('opponent_champions', '-')))}</td>
            </tr>
            """
        )
    return f"""
    <section class="table-panel">
      <div class="section-heading">
        <h3>All Head To Head Matchups</h3>
        <small>Same-role opponent pairs, including one-game samples</small>
      </div>
      <div class="table-wrap">
        <table class="h2h-sortable sortable-table">
          <thead>
            <tr>
              <th data-type="text">Role</th>
              <th data-type="text">Player</th>
              <th data-type="text">Opponent</th>
              <th data-type="number">Games</th>
              <th data-type="number">W-L</th>
              <th data-type="number">Winrate</th>
              <th data-type="number">Player KDA</th>
              <th data-type="number">Opponent KDA</th>
              <th data-type="text">Player Champions</th>
              <th data-type="text">Opponent Champions</th>
            </tr>
          </thead>
          <tbody>{''.join(body)}</tbody>
        </table>
      </div>
    </section>
    """


def render_champion_head_to_head_highlight(
    title: str, row: dict[str, object], detail: str
) -> str:
    return f"""
    <article class="h2h-highlight-card" {h2h_champion_item_attrs(row)}>
      <span>{escape(title)}</span>
      <strong>{render_h2h_champion_label(row.get("champion", "-"))} <em>vs</em> {render_h2h_champion_label(row.get("opponent_champion", "-"))}</strong>
      <b>{escape(str(row.get("record", "-")))}</b>
      <small>{escape(detail)}</small>
    </article>
    """


def render_champion_head_to_head_table(rows: Sequence[dict[str, object]]) -> str:
    body = []
    for row in rows:
        winrate = float(row.get("winrate", 0))
        kda_edge = float(row.get("kda_edge", 0))
        body.append(
            f"""
            <tr {h2h_champion_item_attrs(row)} data-h2h-champion-table-row>
              <td data-sort="{html_attr(row.get('role', ''))}"><span class="role-pill">{escape(str(row.get('role', '')))}</span></td>
              <td data-sort="{html_attr(row.get('champion', ''))}">{render_h2h_champion_label(row.get('champion', '-'))}</td>
              <td data-sort="{html_attr(row.get('opponent_champion', ''))}">{render_h2h_champion_label(row.get('opponent_champion', '-'))}</td>
              <td class="number-cell" data-sort="{int(row.get('games', 0))}">{integer(row.get('games', 0))}</td>
              <td class="number-cell" data-sort="{int(row.get('wins', 0))}">{escape(str(row.get('record', '')))}</td>
              {heat_table_cell(pct(winrate), winrate, winrate)}
              <td class="number-cell" data-sort="{kda_edge:.4f}">{score(kda_edge)}</td>
              <td class="number-cell" data-sort="{float(row.get('champion_kda', 0))}">{two_decimal(float(row.get('champion_kda', 0)))}</td>
              <td class="number-cell" data-sort="{float(row.get('opponent_kda', 0))}">{two_decimal(float(row.get('opponent_kda', 0)))}</td>
              <td data-sort="{html_attr(row.get('champion_pilots', ''))}">{escape(str(row.get('champion_pilots', '-')))}</td>
              <td data-sort="{html_attr(row.get('opponent_pilots', ''))}">{escape(str(row.get('opponent_pilots', '-')))}</td>
            </tr>
            """
        )
    if not body:
        return """
        <section class="table-panel">
          <div class="empty-state">No champion lane matchups have repeated enough yet.</div>
        </section>
        """
    return f"""
    <section class="table-panel">
      <div class="section-heading">
        <h3>All Champion Lane Matchups</h3>
        <small>Champion-vs-champion pairs in the same role, including one-game samples</small>
      </div>
      <div class="table-wrap">
        <table class="h2h-sortable sortable-table">
          <thead>
            <tr>
              <th data-type="text">Role</th>
              <th data-type="text">Champion</th>
              <th data-type="text">Opponent</th>
              <th data-type="number">Games</th>
              <th data-type="number">W-L</th>
              <th data-type="number">Winrate</th>
              <th data-type="number">KDA Edge</th>
              <th data-type="number">Champion KDA</th>
              <th data-type="number">Opponent KDA</th>
              <th data-type="text">Pilots</th>
              <th data-type="text">Opponent Pilots</th>
            </tr>
          </thead>
          <tbody>{''.join(body)}</tbody>
        </table>
      </div>
    </section>
    """


def render_pilot_champion_head_to_head_table(rows: Sequence[dict[str, object]]) -> str:
    body = []
    for row in rows[:40]:
        winrate = float(row.get("winrate", 0))
        body.append(
            f"""
            <tr {h2h_pilot_champion_item_attrs(row)}>
              <td data-sort="{html_attr(row.get('role', ''))}"><span class="role-pill">{escape(str(row.get('role', '')))}</span></td>
              <td data-sort="{html_attr(row.get('entity', ''))}">{escape(str(row.get('entity', '-')))}</td>
              <td data-sort="{html_attr(row.get('opponent_entity', ''))}">{escape(str(row.get('opponent_entity', '-')))}</td>
              <td class="number-cell" data-sort="{int(row.get('games', 0))}">{integer(row.get('games', 0))}</td>
              <td class="number-cell" data-sort="{int(row.get('wins', 0))}">{escape(str(row.get('record', '-')))}</td>
              {heat_table_cell(pct(winrate), winrate, winrate)}
              <td class="number-cell" data-sort="{float(row.get('kda_edge', 0))}">{score(float(row.get('kda_edge', 0)))}</td>
              <td data-sort="{html_attr(row.get('match_ids', ''))}">{escape(str(row.get('match_ids', '-')))}</td>
            </tr>
            """
        )
    if not body:
        body.append(
            """
            <tr><td colspan="8" class="empty-cell">No exact player/champion lane matchups available yet.</td></tr>
            """
        )
    return f"""
    <section class="table-panel">
      <div class="section-heading">
        <h3>Pilot-Specific Champion Duels</h3>
        <small>Exact player/champion vs player/champion pairs are sparse, so one-game samples should be treated as directional.</small>
      </div>
      <div class="table-wrap">
        <table class="h2h-sortable sortable-table">
          <thead>
            <tr>
              <th data-type="text">Role</th>
              <th data-type="text">Player Champion</th>
              <th data-type="text">Opponent Champion</th>
              <th data-type="number">Games</th>
              <th data-type="number">W-L</th>
              <th data-type="number">Winrate</th>
              <th data-type="number">KDA Edge</th>
              <th data-type="text">Matches</th>
            </tr>
          </thead>
          <tbody>{''.join(body)}</tbody>
        </table>
      </div>
    </section>
    """


def render_champion_head_to_head_section(
    rows: Sequence[dict[str, object]],
    pilot_rows: Sequence[dict[str, object]],
) -> str:
    most_repeated = find_first(
        sorted(rows, key=lambda row: (-int(row.get("games", 0)), -float(row.get("dominance", 0))))
    )
    strongest = find_first(
        sorted(rows, key=lambda row: (-float(row.get("dominance", 0)), -int(row.get("games", 0))))
    )
    kda_edge = find_first(
        sorted(rows, key=lambda row: (-float(row.get("kda_edge", 0)), -int(row.get("games", 0))))
    )
    nemesis = find_first(
        sorted(
            [row for row in rows if int(row.get("wins", 0)) > int(row.get("losses", 0))],
            key=lambda row: (-float(row.get("dominance", 0)), -int(row.get("games", 0))),
        )
    )
    highlight_rows = [
        (
            "Most Repeated Lane Matchup",
            most_repeated,
            f"{most_repeated.get('role', '-')} lane, {most_repeated.get('record', '-')} over {most_repeated.get('games', 0)} games.",
        ),
        (
            "Strongest Champion Counter",
            strongest,
            f"{strongest.get('role', '-')} lane, {pct(float(strongest.get('winrate', 0)))} winrate.",
        ),
        (
            "Biggest KDA Edge",
            kda_edge,
            f"{two_decimal(float(kda_edge.get('champion_kda', 0)))} KDA vs {two_decimal(float(kda_edge.get('opponent_kda', 0)))}.",
        ),
        (
            "Nemesis Champion",
            nemesis,
            f"{nemesis.get('champion', '-')} is {nemesis.get('record', '-')} into {nemesis.get('opponent_champion', '-')} in {nemesis.get('role', '-')}.",
        ),
    ]
    highlights = "".join(
        render_champion_head_to_head_highlight(title, row, detail)
        for title, row, detail in highlight_rows
        if row
    )
    chart_rows = sorted(
        rows,
        key=lambda row: (
            -int(row.get("games", 0)),
            -float(row.get("dominance", 0)),
            -float(row.get("kda_edge", 0)),
        ),
    )[:18]
    chart_html = []
    for row in chart_rows:
        winrate = float(row.get("winrate", 0))
        chart_html.append(
            f"""
            <div class="h2h-chart-row" {h2h_champion_item_attrs(row)}>
              <div class="h2h-chart-label">
                <strong>{escape(str(row.get("chart_label", "-")))}</strong>
                <small>{escape(str(row.get("role", "-")))} lane · {escape(str(row.get("record", "-")))} over {integer(row.get("games", 0))} games · KDA edge {score(float(row.get("kda_edge", 0)))}</small>
              </div>
              <div class="h2h-track"><div class="h2h-fill" style="width: {max(3.0, winrate * 100):.2f}%"></div></div>
              <b>{escape(pct(winrate))}</b>
            </div>
            """
        )

    return f"""
    <section id="champion-head-to-head" class="section">
      <div class="section-title">
        <div>
          <h2>Champion Vs Champion Within Role</h2>
          <p class="note">Aggregated lane matchups such as Viktor vs Ziggs or Renekton vs Ornn. Role filters above also apply here; player filters only affect the player head-to-head section.</p>
        </div>
      </div>
      <div class="h2h-highlight-grid">{highlights}</div>
      <section class="chart-panel">
        <h3>Most Repeated Champion Lane Matchups</h3>
        <div class="h2h-chart">{"".join(chart_html)}</div>
      </section>
      {render_champion_head_to_head_table(rows)}
      {render_pilot_champion_head_to_head_table(pilot_rows)}
    </section>
    """


def render_head_to_head_page(
    *,
    shared_style: str,
    rows: Sequence[dict[str, object]],
    champion_rows: Sequence[dict[str, object]],
    pilot_champion_rows: Sequence[dict[str, object]],
    generated_at: str,
    main_page_name: str,
    teams_page_name: str,
    draft_coach_page_name: str,
    showcases_page_name: str,
    experimental_page_name: str,
) -> str:
    player_counts: Counter[str] = Counter()
    for row in rows:
        player_counts[str(row.get("player", ""))] += int(row.get("games", 0))
        player_counts[str(row.get("opponent", ""))] += int(row.get("games", 0))

    role_buttons = [
        '<button type="button" class="h2h-filter-button active" data-h2h-role-filter="all">All Roles</button>'
    ]
    role_buttons.extend(
        f'<button type="button" class="h2h-filter-button" data-h2h-role-filter="{html_attr(role)}">{escape(role)}</button>'
        for role in ROLE_ORDER
    )
    player_buttons = [
        '<button type="button" class="h2h-filter-button active" data-h2h-player-filter="all">All Players</button>'
    ]
    player_buttons.extend(
        f'<button type="button" class="h2h-filter-button" data-h2h-player-filter="{html_attr(name)}">{escape(name)}</button>'
        for name, _count in sorted(
            player_counts.items(), key=lambda item: (-item[1], item[0])
        )
    )

    by_dominance = sorted(
        rows,
        key=lambda row: (
            -float(row.get("dominance", 0)),
            -int(row.get("games", 0)),
            -float(row.get("winrate", 0)),
        ),
    )
    busiest = find_first(sorted(rows, key=lambda row: (-int(row.get("games", 0)), -float(row.get("dominance", 0)))))
    strongest = find_first(by_dominance)
    closest = find_first(
        sorted(rows, key=lambda row: (float(row.get("dominance", 0)), -int(row.get("games", 0))))
    )
    kda_edge = find_first(
        sorted(
            rows,
            key=lambda row: (
                -(
                    float(row.get("player_kda", 0))
                    - float(row.get("opponent_kda", 0))
                ),
                -int(row.get("games", 0)),
            ),
        )
    )
    highlight_rows = [
        (
            "Most Repeated Duel",
            busiest,
            f"{busiest.get('role', '-')} lane, {busiest.get('record', '-')} over {busiest.get('games', 0)} games.",
        ),
        (
            "Most One-Sided",
            strongest,
            f"{strongest.get('role', '-')} lane, {strongest.get('record', '-')} record.",
        ),
        (
            "Closest Rivalry",
            closest,
            f"{closest.get('role', '-')} lane, {closest.get('record', '-')} record.",
        ),
        (
            "Biggest KDA Edge",
            kda_edge,
            f"{two_decimal(float(kda_edge.get('player_kda', 0)))} KDA vs {two_decimal(float(kda_edge.get('opponent_kda', 0)))}.",
        ),
    ]
    highlights = "".join(
        render_head_to_head_highlight(title, row, detail)
        for title, row, detail in highlight_rows
        if row
    )

    empty_html = (
        '<div class="empty-state">No same-role head-to-head matchups available yet.</div>'
        if not rows
        else ""
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>LoL Head To Head</title>
  <style>{shared_style}{render_head_to_head_css()}</style>
</head>
<body>
  <header>
    <div class="topline">
      <div>
        <h1>LoL Head To Head</h1>
        <p>Same-role rivalries, including one-game samples.</p>
      </div>
      {render_refresh_control(generated_at)}
    </div>
  </header>
  <nav>
    <a href="{html_attr(main_page_name)}#overview">Overview</a>
    <a href="{html_attr(main_page_name)}#awards">Awards</a>
    <a href="{html_attr(main_page_name)}#match-history">Matches</a>
    <a href="{html_attr(main_page_name)}#players">Players</a>
    <a href="{html_attr(main_page_name)}#champion-pools">Champion Pools</a>
    <a href="{html_attr(main_page_name)}#champions">Champions</a>
    <a href="{html_attr(main_page_name)}#role-pools">Role Pools</a>
    <a href="{html_attr(main_page_name)}#combos">Combos</a>
    <a href="{html_attr(teams_page_name)}#teams">Teams</a>
    <a href="{html_attr(draft_coach_page_name)}#draft-coach">Draft Coach</a>
    <a href="{html_attr(showcases_page_name)}">Showcases</a>
    <a href="{html_attr(experimental_page_name)}#custom-meta">Experimental</a>
    <a href="{html_attr(main_page_name)}#deep-dive">Deep Dive</a>
  </nav>
  <main>
    <section id="head-to-head" class="section">
      <div class="section-title">
        <div>
          <h2>Head To Head</h2>
          <p class="note">Each row compares two players who faced each other in the same role. The displayed winrate belongs to the player listed first.</p>
        </div>
      </div>
      <section class="h2h-filter-panel">
        <div class="h2h-filter-row">
          <strong>Role</strong>
          {"".join(role_buttons)}
          <span class="h2h-count" data-h2h-count>{len(rows)} matchups</span>
        </div>
        <div class="h2h-filter-row">
          <strong>Player</strong>
          {"".join(player_buttons)}
        </div>
      </section>
      {empty_html}
      {render_head_to_head_heatmaps(rows)}
      <div class="h2h-highlight-grid">{highlights}</div>
      <div class="empty-state h2h-empty" data-h2h-empty>No matchups match the selected filters.</div>
      {render_head_to_head_table(rows)}
    </section>
    {render_champion_head_to_head_section(champion_rows, pilot_champion_rows)}
  </main>
  <script>{render_head_to_head_script()}{render_refresh_script()}</script>
</body>
</html>
"""


FINGERPRINT_METRICS: tuple[tuple[str, str], ...] = (
    ("Carry", "carry_score"),
    ("Teamfight", "teamfight_score"),
    ("Survive", "survivability_score"),
    ("Versatile", "versatility_score"),
    ("Reliable", "reliability_score"),
    ("Comfort", "comfort_score"),
)


def radar_points(values: Sequence[float], *, center: float = 96, radius: float = 70) -> str:
    points = []
    for index, value in enumerate(values):
        angle = (-90 + (360 / len(values)) * index) * math.pi / 180
        distance = radius * clamp(value)
        x = center + (math.cos(angle) * distance)
        y = center + (math.sin(angle) * distance)
        points.append(f"{x:.1f},{y:.1f}")
    return " ".join(points)


def radar_grid_points(level: float, *, center: float = 96, radius: float = 70) -> str:
    return radar_points([level] * len(FINGERPRINT_METRICS), center=center, radius=radius)


def render_fingerprint_radar(row: dict[str, object], *, large: bool = False) -> str:
    values = [float(row.get(key, 0)) for _label, key in FINGERPRINT_METRICS]
    axes = []
    labels = []
    size = 320 if large else 280
    center = size / 2
    radius = 88 if large else 76
    label_radius = radius + (18 if large else 12)
    for index, (label, _key) in enumerate(FINGERPRINT_METRICS):
        angle = (-90 + (360 / len(FINGERPRINT_METRICS)) * index) * math.pi / 180
        x = center + (math.cos(angle) * radius)
        y = center + (math.sin(angle) * radius)
        label_x = center + (math.cos(angle) * label_radius)
        label_y = center + (math.sin(angle) * label_radius)
        anchor = "middle"
        if label_x < center - 10:
            anchor = "end"
        elif label_x > center + 10:
            anchor = "start"
        axes.append(
            f'<line x1="{center}" y1="{center}" x2="{x:.1f}" y2="{y:.1f}" />'
        )
        labels.append(
            f'<text x="{label_x:.1f}" y="{label_y:.1f}" text-anchor="{anchor}">{escape(label)}</text>'
        )

    rings = "\n".join(
        f'<polygon points="{radar_grid_points(level, center=center, radius=radius)}" />'
        for level in (0.25, 0.50, 0.75, 1.0)
    )
    class_name = "fingerprint-radar fingerprint-radar-large" if large else "fingerprint-radar"
    return f"""
    <svg class="{class_name}" viewBox="0 0 {size} {size}" role="img" aria-label="{html_attr(row.get('name', 'Player'))} fingerprint radar">
      <g class="radar-grid">{rings}</g>
      <g class="radar-axis">{"".join(axes)}</g>
      <polygon class="radar-fill" points="{radar_points(values, center=center, radius=radius)}" />
      <g class="radar-labels">{"".join(labels)}</g>
    </svg>
    """


def render_showcase_fingerprint(row: dict[str, object] | None) -> str:
    if not row:
        return ""
    metric_rows = []
    for label, key in FINGERPRINT_METRICS:
        value = float(row.get(key, 0))
        metric_rows.append(
            f"""
            <div class="showcase-fingerprint-metric">
              <span>{escape(label)}</span>
              <b>{fingerprint_score_label(value)}</b>
            </div>
            """
        )
    return f"""
    <article class="showcase-fingerprint">
      <div class="showcase-fingerprint-heading">
        <div>
          <span>Player Fingerprint</span>
          <strong>{fingerprint_score_label(float(row.get('fingerprint_score', 0)))}</strong>
        </div>
        <small>{escape(str(row.get('comfort_label', '-')))}</small>
      </div>
      {render_fingerprint_radar(row, large=True)}
      <div class="showcase-fingerprint-metrics">{"".join(metric_rows)}</div>
    </article>
    """


def render_meta_spotlights(rows: Sequence[dict[str, object]]) -> str:
    cards = []
    for role in ROLE_ORDER:
        row = find_first(
            sorted(
                [item for item in rows if str(item.get("role", "")) == role],
                key=lambda item: (
                    -float(item.get("contested_score", 0)),
                    -int(item.get("games", 0)),
                    str(item.get("champion", "")),
                ),
            )
        )
        if not row:
            continue
        champion = str(row.get("champion", "-"))
        cards.append(
            f"""
            <article class="meta-spotlight-card tier-{html_attr(str(row.get('tier', 'd')).lower())}">
              <span>{escape(role)}</span>
              <img src="{html_attr(champion_icon_url(champion))}" alt="{html_attr(champion)}">
              <strong>{escape(champion)}</strong>
              <b>{escape(str(row.get('tier', '-')))} Tier / {score(float(row.get('contested_score', 0)))}</b>
              <small>{integer(row.get('games', 0))} games, {pct(float(row.get('winrate', 0)))} WR, best pilot {escape(str(row.get('best_pilot', '-')))}</small>
            </article>
            """
        )
    return f'<div class="meta-spotlight-grid">{"".join(cards)}</div>'


def form_status_class(status: object) -> str:
    return str(status).lower().replace(" ", "-")


def render_form_highlight(title: str, row: dict[str, object], detail: str) -> str:
    return f"""
    <article class="form-highlight-card status-{html_attr(form_status_class(row.get('status', 'stable')))}">
      <span>{escape(title)}</span>
      <strong>{escape(str(row.get('name', '-')))}</strong>
      <b>{score(float(row.get('recent_score', 0)))} form</b>
      <small>{escape(detail)}</small>
    </article>
    """


def render_recent_form_section(rows: Sequence[dict[str, object]]) -> str:
    eligible = [row for row in rows if int(row.get("recent_games", 0)) >= 4]
    best_form = find_first(
        sorted(eligible, key=lambda row: (-float(row.get("recent_score", 0)), str(row.get("name", ""))))
    )
    heating = find_first(
        sorted(eligible, key=lambda row: (-float(row.get("mvp_movement", 0)), str(row.get("name", ""))))
    )
    cooling = find_first(
        sorted(eligible, key=lambda row: (float(row.get("mvp_movement", 0)), str(row.get("name", ""))))
    )
    streak = find_first(
        sorted(
            eligible,
            key=lambda row: (
                str(row.get("active_result", "")) != "Win",
                -int(row.get("active_length", 0)),
                -float(row.get("recent_score", 0)),
            ),
        )
    )
    highlights = []
    if best_form:
        highlights.append(
            render_form_highlight(
                "Best Current Form",
                best_form,
                f"{best_form.get('recent_record', '-')} over last {best_form.get('recent_games', 0)}, {two_decimal(float(best_form.get('recent_kda', 0)))} recent KDA.",
            )
        )
    if heating:
        highlights.append(
            render_form_highlight(
                "Heating Up",
                heating,
                f"{signed_integer(round(float(heating.get('mvp_movement', 0))))} vs season MVP baseline.",
            )
        )
    if cooling:
        highlights.append(
            render_form_highlight(
                "Biggest Slump",
                cooling,
                f"{signed_integer(round(float(cooling.get('mvp_movement', 0))))} vs season MVP baseline.",
            )
        )
    if streak:
        highlights.append(
            render_form_highlight(
                "Current Streak",
                streak,
                str(streak.get("streak_label", "No streak")),
            )
        )

    cards = []
    for row in rows:
        timeline = []
        for item in row.get("timeline", []):
            result_class = "win" if item.get("result") == "Win" else "loss"
            timeline.append(
                f"""
                <span class="form-pill {result_class}" title="Match {html_attr(item.get('match_id', ''))}: {html_attr(item.get('champion', ''))} {html_attr(item.get('role', ''))} {html_attr(item.get('kda', ''))}">
                  {escape(str(item.get("result", "-"))[0])}
                </span>
                """
            )
        movement = float(row.get("mvp_movement", 0))
        cards.append(
            f"""
            <article class="form-card status-{html_attr(form_status_class(row.get('status', 'stable')))}" data-card-text="{html_attr(row.get('search_text', ''))}">
              <div class="form-card-heading">
                <div>
                  <span>{escape(str(row.get('status', '-')))}</span>
                  <h3>{escape(str(row.get('name', '-')))}</h3>
                </div>
                <strong>{score(float(row.get('recent_score', 0)))}</strong>
              </div>
              <div class="form-timeline">{"".join(timeline)}</div>
              <div class="form-stat-grid">
                <div><span>Last {integer(row.get('recent_games', 0))}</span><b>{escape(str(row.get('recent_record', '-')))}</b></div>
                <div><span>Recent WR</span><b>{pct(float(row.get('recent_winrate', 0)))}</b></div>
                <div><span>KDA Trend</span><b>{two_decimal(float(row.get('recent_kda', 0)))} vs {two_decimal(float(row.get('overall_kda', 0)))}</b></div>
                <div><span>MVP Move</span><b>{signed_integer(round(movement))}</b></div>
              </div>
              <small>{escape(str(row.get('streak_label', 'No streak')))}</small>
            </article>
            """
        )

    return f"""
    <section id="recent-form" class="section">
      <div class="section-title">
        <div>
          <h2>Recent Form</h2>
          <p class="note">Last 10 games per player, with current streak, recent KDA/KP trends, and an approximate MVP movement against season baseline.</p>
        </div>
      </div>
      <div class="form-highlight-grid">{"".join(highlights)}</div>
      <div class="form-toolbar">
        <input class="card-search" type="search" placeholder="Search recent form" data-card-filter="recent-form">
        <span class="pool-count">{len(rows)} form cards</span>
      </div>
      <div class="form-grid" data-card-container="recent-form">{"".join(cards)}</div>
    </section>
    """


def render_lab_award_visual(row: dict[str, object]) -> str:
    champion = str(row.get("champion", "")).strip()
    badge = str(row.get("badge", "")).strip() or str(row.get("title", "-"))[:3]
    if champion and champion != "-":
        return (
            f'<div class="lab-award-icon">'
            f'<img src="{html_attr(champion_icon_url(champion))}" alt="{html_attr(champion)}">'
            f"</div>"
        )
    return f'<div class="lab-award-icon lab-award-badge">{escape(badge[:4].upper())}</div>'


def render_hall_of_fame_section(
    rows: Sequence[dict[str, object]], main_page_name: str
) -> str:
    cards = []
    for row in rows:
        theme = str(row.get("theme", "blue"))
        match_id = str(row.get("match_id", "")).strip()
        if match_id:
            open_tag = (
                f'<a class="lab-award-card lab-theme-{html_attr(theme)}" '
                f'href="{html_attr(main_page_name)}#match-{html_attr(match_id)}">'
            )
            close_tag = "</a>"
        else:
            open_tag = f'<article class="lab-award-card lab-theme-{html_attr(theme)}">'
            close_tag = "</article>"
        cards.append(
            f"""
            {open_tag}
              {render_lab_award_visual(row)}
              <div>
                <span>{escape(str(row.get('title', '-')))}</span>
                <strong>{escape(str(row.get('winner', '-')))}</strong>
                <b>{escape(str(row.get('stat', '-')))}</b>
                <small>{escape(str(row.get('detail', '-')))}</small>
              </div>
            {close_tag}
            """
        )
    return f"""
    <section id="hall-of-fame" class="section">
      <div class="section-title">
        <div>
          <h2>Customs Hall Of Fame / Hall Of Pain</h2>
          <p class="note">Single-game legends, cursed picks, tragic losses, and other custom-only awards.</p>
        </div>
      </div>
      <div class="lab-award-grid">{"".join(cards)}</div>
    </section>
    """


def chemistry_link_detail(row: dict[str, object]) -> str:
    return (
        f"{integer(row.get('wins', 0))}-{integer(row.get('losses', 0))}, "
        f"{integer(row.get('games', 0))} games, {pct(float(row.get('winrate', 0)))} WR, "
        f"{signed_integer(round(float(row.get('lift_points', 0))))} pts vs baseline"
    )


def render_chemistry_list(title: str, rows: Sequence[dict[str, object]], mood: str) -> str:
    items = []
    for row in rows:
        items.append(
            f"""
            <li class="chemistry-list-item chemistry-{html_attr(mood)}">
              <strong>{escape(str(row.get('label', '-')))}</strong>
              <span>{escape(chemistry_link_detail(row))}</span>
            </li>
            """
        )
    if not items:
        items.append('<li class="chemistry-list-item"><strong>No sample yet</strong><span>Needs more games.</span></li>')
    return f"""
    <article class="chemistry-panel">
      <h3>{escape(title)}</h3>
      <ul>{"".join(items)}</ul>
    </article>
    """


def render_chemistry_network_chart(links: Sequence[dict[str, object]]) -> str:
    if not links:
        return '<div class="chemistry-empty">Not enough duo samples yet.</div>'
    sorted_links = sorted(
        links,
        key=lambda row: (
            -abs(float(row.get("lift_points", 0))),
            -int(row.get("games", 0)),
            str(row.get("label", "")),
        ),
    )
    players = []
    for link in sorted_links:
        pair = tuple(link.get("players", ()))
        if len(pair) != 2:
            continue
        for name in pair:
            if name not in players:
                players.append(str(name))
    if len(players) < 2:
        return '<div class="chemistry-empty">Not enough duo samples yet.</div>'

    width = 980
    height = 620
    center_x = width / 2
    center_y = height / 2
    radius_x = 382
    radius_y = 228
    positions = {}
    for index, name in enumerate(players):
        angle = (-94 + (360 / len(players)) * index) * math.pi / 180
        positions[name] = (
            center_x + math.cos(angle) * radius_x,
            center_y + math.sin(angle) * radius_y,
        )

    max_lift = max(abs(float(link.get("lift_points", 0))) for link in sorted_links) or 1
    path_parts = []
    label_parts = []
    for index, link in enumerate(sorted_links, start=1):
        pair = tuple(str(name) for name in link.get("players", ()))
        if len(pair) != 2 or pair[0] not in positions or pair[1] not in positions:
            continue
        lift_points = float(link.get("lift_points", 0))
        lift = float(link.get("lift", safe_div(lift_points, 100)))
        mood = "good" if lift >= 0 else "bad"
        stroke_width = 3.0 + min(6.0, abs(lift_points) / max_lift * 6.0)
        x1, y1 = positions[pair[0]]
        x2, y2 = positions[pair[1]]
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2
        out_x = mid_x - center_x
        out_y = mid_y - center_y
        out_len = max(1.0, math.hypot(out_x, out_y))
        if out_len < 46:
            dx = x2 - x1
            dy = y2 - y1
            line_len = max(1.0, math.hypot(dx, dy))
            out_x = -dy / line_len
            out_y = dx / line_len
            if index % 2:
                out_x *= -1
                out_y *= -1
        else:
            out_x /= out_len
            out_y /= out_len
        curve = 54 + (index % 4) * 16
        control_x = mid_x + out_x * curve
        control_y = mid_y + out_y * curve
        dash_attr = ' stroke-dasharray="10 8"' if mood == "bad" else ""
        path_parts.append(
            f"""
            <path class="chemistry-link-path chemistry-link-{mood}" d="M {x1:.1f} {y1:.1f} Q {control_x:.1f} {control_y:.1f} {x2:.1f} {y2:.1f}" stroke-width="{stroke_width:.1f}"{dash_attr}>
              <title>{escape(str(link.get('label', '-')))}: {integer(link.get('wins', 0))}-{integer(link.get('losses', 0))}, {pct(float(link.get('winrate', 0)))} WR, {signed_integer(round(lift_points))} pts</title>
            </path>
            """
        )
        label_text = signed_integer(round(lift_points))
        label_width = max(42, 12 + len(label_text) * 8)
        label_x = min(max(10.0, control_x - (label_width / 2)), width - label_width - 10)
        label_y = min(max(22.0, control_y - 12), height - 32)
        label_parts.append(
            f"""
            <g class="chemistry-edge-label chemistry-edge-label-{mood}">
              <rect x="{label_x:.1f}" y="{label_y:.1f}" width="{label_width:.1f}" height="24" rx="8"></rect>
              <text x="{label_x + (label_width / 2):.1f}" y="{label_y + 16:.1f}" text-anchor="middle">{escape(label_text)}</text>
            </g>
            """
        )

    node_parts = []
    for name, (x, y) in positions.items():
        initials = "".join(part[:1] for part in name.split()[:2]).upper()[:2] or name[:1]
        label_width = min(122, max(58, len(name) * 8 + 20))
        label_x = min(max(8.0, x - (label_width / 2)), width - label_width - 8)
        label_y = y + 38 if y < center_y else y - 58
        node_parts.append(
            f"""
            <g class="chemistry-node">
              <circle cx="{x:.1f}" cy="{y:.1f}" r="28"></circle>
              <text class="chemistry-node-initials" x="{x:.1f}" y="{y + 5:.1f}" text-anchor="middle">{escape(initials)}</text>
              <rect class="chemistry-node-label-bg" x="{label_x:.1f}" y="{label_y:.1f}" width="{label_width:.1f}" height="26" rx="8"></rect>
              <text class="chemistry-node-label" x="{label_x + (label_width / 2):.1f}" y="{label_y + 17:.1f}" text-anchor="middle">{escape(name)}</text>
            </g>
            """
        )

    if not path_parts:
        return '<div class="chemistry-empty">Not enough duo samples yet.</div>'
    return f"""
    <svg class="chemistry-network" viewBox="0 0 {width} {height}" role="img" aria-label="Team chemistry network">
      <g class="chemistry-grid">
        <ellipse cx="{center_x:.1f}" cy="{center_y:.1f}" rx="{radius_x:.1f}" ry="{radius_y:.1f}"></ellipse>
        <ellipse cx="{center_x:.1f}" cy="{center_y:.1f}" rx="{radius_x * 0.58:.1f}" ry="{radius_y * 0.58:.1f}"></ellipse>
      </g>
      <g class="chemistry-links">{"".join(path_parts)}</g>
      <g class="chemistry-edge-labels">{"".join(label_parts)}</g>
      <g class="chemistry-nodes">{"".join(node_parts)}</g>
      <g class="chemistry-legend">
        <rect x="24" y="24" width="210" height="58" rx="10"></rect>
        <path class="chemistry-link-path chemistry-link-good" d="M 42 46 L 92 46" stroke-width="5"></path>
        <text x="102" y="50">Overperforms</text>
        <path class="chemistry-link-path chemistry-link-bad" d="M 42 68 L 92 68" stroke-width="5" stroke-dasharray="10 8"></path>
        <text x="102" y="72">Underperforms</text>
      </g>
    </svg>
    """


def render_directed_chemistry_card(
    title: str, row: dict[str, object], mood: str, fallback: str
) -> str:
    if not row:
        return f"""
        <article class="chemistry-callout chemistry-{html_attr(mood)}">
          <span>{escape(title)}</span>
          <strong>{escape(fallback)}</strong>
          <small>Needs more directed duo samples.</small>
        </article>
        """
    relationship = (
        f"{row.get('source', '-')} improves {row.get('target', '-')}"
        if mood == "good"
        else f"{row.get('source', '-')} lowers {row.get('target', '-')}"
    )
    return f"""
    <article class="chemistry-callout chemistry-{html_attr(mood)}">
      <span>{escape(title)}</span>
      <strong>{escape(relationship)}</strong>
      <b>{signed_integer(round(float(row.get('lift_points', 0))))} pts</b>
      <small>{pct(float(row.get('winrate', 0)))} with them vs {pct(float(row.get('without_winrate', 0)))} without.</small>
    </article>
    """


def render_team_chemistry_section(data: dict[str, object]) -> str:
    best_five = data.get("best_five", {})
    best_five_card = ""
    if isinstance(best_five, dict) and best_five:
        best_five_card = f"""
        <article class="chemistry-callout chemistry-good">
          <span>Best 5-Stack Historically</span>
          <strong>{escape(str(best_five.get('combo', '-')))}</strong>
          <b>{pct(float(best_five.get('winrate', 0)))} WR</b>
          <small>{escape(str(best_five.get('footer', '')))}</small>
        </article>
        """
    return f"""
    <section id="team-chemistry-network" class="section">
      <div class="section-title">
        <div>
          <h2>Team Chemistry Network</h2>
          <p class="note">Duo links compare same-side winrate against each player's baseline. Curved green links overperform; dashed red links underperform; thicker links and badges show bigger swings.</p>
        </div>
      </div>
      <div class="chemistry-layout">
        <div class="chemistry-visual">{render_chemistry_network_chart(data.get('network_links', []))}</div>
        <div class="chemistry-callout-grid">
          {render_directed_chemistry_card("Do Not Separate", data.get("do_not_separate", {}), "good", "No standout yet")}
          {render_directed_chemistry_card("Avoid Pairing", data.get("avoid_pairing", {}), "bad", "No danger pair yet")}
          {best_five_card}
        </div>
      </div>
      <div class="chemistry-list-grid">
        {render_chemistry_list("Best Duo Links", data.get("best_links", []), "good")}
        {render_chemistry_list("Worst Duo Links", data.get("worst_links", []), "bad")}
      </div>
    </section>
    """


def render_upset_cards(
    title: str, rows: Sequence[dict[str, object]], main_page_name: str, mood: str
) -> str:
    cards = []
    for row in rows:
        cards.append(
            f"""
            <a class="upset-card upset-{html_attr(mood)}" href="{html_attr(main_page_name)}#match-{html_attr(row.get('match_id', ''))}">
              <span>{escape(str(row.get('label', '-')))}</span>
              <strong>{escape(str(row.get('winner_names', '-')))}</strong>
              <b>{score(float(row.get('expected_margin', 0)))} expected-point gap</b>
              <small>{escape(str(row.get('detail', '-')))}</small>
            </a>
            """
        )
    if not cards:
        cards.append(
            '<article class="upset-card"><span>No sample yet</span><strong>Nothing found</strong><small>Needs more matches.</small></article>'
        )
    return f"""
    <article class="upset-column">
      <h3>{escape(title)}</h3>
      <div class="upset-stack">{"".join(cards)}</div>
    </article>
    """


def render_upset_detector_section(data: dict[str, list[dict[str, object]]], main_page_name: str) -> str:
    return f"""
    <section id="upset-detector" class="section">
      <div class="section-title">
        <div>
          <h2>Upset Detector</h2>
          <p class="note">Pre-match expectation is estimated from MVP score, role score, and champion-role comfort, then compared with the actual result.</p>
        </div>
      </div>
      <div class="upset-grid">
        {render_upset_cards("Biggest Upset Wins", data.get("upsets", []), main_page_name, "upset")}
        {render_upset_cards("Expected Stomps That Happened", data.get("stomps", []), main_page_name, "stomp")}
        {render_upset_cards("Biggest Throws By Expected Strength", data.get("throws", []), main_page_name, "throw")}
      </div>
    </section>
    """


def render_champion_ownership_section(rows: Sequence[dict[str, object]]) -> str:
    cards = []
    for row in rows:
        champion = str(row.get("champion", "-"))
        cards.append(
            f"""
            <article class="ownership-card" data-card-text="{html_attr(row.get('search_text', ''))}">
              <div class="ownership-heading">
                <img src="{html_attr(champion_icon_url(champion))}" alt="{html_attr(champion)}">
                <div>
                  <h3>{escape(champion)}</h3>
                  <span>{integer(row.get('games', 0))} games / {pct(float(row.get('winrate', 0)))} WR</span>
                </div>
                <strong>{score(float(row.get('ban_priority', 0)))}</strong>
              </div>
              <div class="ownership-details">
                <div><span>Owner</span><b>{escape(str(row.get('owner', '-')))}</b><small>{escape(str(row.get('owner_detail', '-')))}</small></div>
                <div><span>Cursed Pilot</span><b>{escape(str(row.get('cursed_pilot', '-')))}</b><small>{escape(str(row.get('cursed_detail', '-')))}</small></div>
                <div><span>Best Role</span><b>{escape(str(row.get('best_role', '-')))}</b><small>{escape(str(row.get('best_role_detail', '-')))}</small></div>
                <div><span>Draft Ban Priority</span><b>{escape(str(row.get('ban_detail', '-')))}</b><small>If included in the 40-champ draft.</small></div>
              </div>
              <small class="ownership-recent">{escape(str(row.get('recent', '-')))}</small>
            </article>
            """
        )
    return f"""
    <section id="champion-ownership" class="section">
      <div class="section-title">
        <div>
          <h2>Champion Ownership Cards</h2>
          <p class="note">Each champion's current owner, cursed pilot, best role, recent usage, and draft-ban signal.</p>
        </div>
      </div>
      <div class="form-toolbar">
        <input class="card-search" type="search" placeholder="Search champions, owners, or roles" data-card-filter="ownership">
        <span class="pool-count">{len(rows)} champion cards</span>
      </div>
      <div class="ownership-grid" data-card-container="ownership">{"".join(cards)}</div>
    </section>
    """


def render_experimental_css() -> str:
    return """
    .experimental-hero {
      display: grid;
      grid-template-columns: minmax(0, 1.5fr) minmax(280px, 0.8fr);
      gap: 16px;
      align-items: stretch;
    }
    .experiment-note {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
      padding: 16px;
    }
    .experiment-note span {
      color: var(--gold);
      display: block;
      font-size: 0.78rem;
      font-weight: 900;
      text-transform: uppercase;
    }
    .experiment-note strong {
      display: block;
      font-size: 1.35rem;
      margin-top: 6px;
    }
    .experiment-note small {
      color: var(--muted);
      display: block;
      line-height: 1.45;
      margin-top: 8px;
    }
    .meta-spotlight-grid {
      display: grid;
      gap: 14px;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      margin-bottom: 16px;
    }
    .meta-spotlight-card {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
      min-height: 230px;
      padding: 14px;
    }
    .meta-spotlight-card span {
      color: var(--muted);
      display: block;
      font-size: 0.78rem;
      font-weight: 950;
    }
    .meta-spotlight-card img {
      border-radius: 8px;
      display: block;
      height: 56px;
      margin: 12px 0;
      width: 56px;
    }
    .meta-spotlight-card strong,
    .meta-spotlight-card b,
    .meta-spotlight-card small {
      display: block;
    }
    .meta-spotlight-card b {
      color: var(--gold);
      margin-top: 8px;
    }
    .meta-spotlight-card small {
      color: var(--muted);
      line-height: 1.4;
      margin-top: 8px;
    }
    .tier-s { border-top-color: #f0c96a; }
    .tier-a { border-top-color: #4fc48b; }
    .tier-b { border-top-color: #62a8ff; }
    .tier-c { border-top-color: #b596ff; }
    .tier-d { border-top-color: #f0a85a; }
    .tier-e { border-top-color: #ff6f81; }
    .tier-f { border-top-color: #8a94a6; }
    .form-toolbar {
      align-items: center;
      display: flex;
      gap: 10px;
      justify-content: space-between;
      margin-bottom: 14px;
    }
    .lab-award-grid {
      display: grid;
      gap: 16px;
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }
    .lab-award-card {
      align-items: center;
      background: linear-gradient(180deg, #121d2a, #0d1620);
      border: 1px solid var(--line);
      border-left: 4px solid #62a8ff;
      border-radius: 8px;
      box-shadow: var(--shadow);
      color: var(--ink);
      display: grid;
      gap: 13px;
      grid-template-columns: 58px minmax(0, 1fr);
      min-height: 150px;
      padding: 14px;
      text-decoration: none;
    }
    .lab-award-icon {
      align-items: center;
      background: #101b28;
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 8px;
      display: flex;
      height: 56px;
      justify-content: center;
      overflow: hidden;
      width: 56px;
    }
    .lab-award-icon img {
      display: block;
      height: 100%;
      object-fit: cover;
      width: 100%;
    }
    .lab-award-badge {
      color: var(--gold);
      font-size: 0.82rem;
      font-weight: 950;
    }
    .lab-award-card span,
    .chemistry-callout span,
    .ownership-heading span {
      color: var(--muted);
      display: block;
      font-size: 0.78rem;
      font-weight: 950;
      text-transform: uppercase;
    }
    .lab-award-card strong,
    .lab-award-card b,
    .lab-award-card small {
      display: block;
    }
    .lab-award-card strong {
      font-size: 1.08rem;
      margin-top: 4px;
    }
    .lab-award-card b {
      color: var(--gold);
      margin-top: 5px;
    }
    .lab-award-card small {
      color: var(--muted);
      line-height: 1.4;
      margin-top: 7px;
    }
    .lab-theme-gold { border-left-color: #f0c96a; }
    .lab-theme-green { border-left-color: #4fc48b; }
    .lab-theme-red { border-left-color: #ff6f81; }
    .lab-theme-purple { border-left-color: #b596ff; }
    .lab-theme-blue { border-left-color: #62a8ff; }
    .form-highlight-grid {
      display: grid;
      gap: 14px;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      margin-bottom: 16px;
    }
    .form-highlight-card,
    .form-card {
      background: linear-gradient(180deg, #121d2a, #0d1620);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
    }
    .form-highlight-card {
      border-top: 4px solid #62a8ff;
      min-height: 142px;
      padding: 14px;
    }
    .form-highlight-card span,
    .form-card-heading span {
      color: var(--muted);
      font-size: 0.78rem;
      font-weight: 950;
      text-transform: uppercase;
    }
    .form-highlight-card strong,
    .form-highlight-card b,
    .form-highlight-card small {
      display: block;
    }
    .form-highlight-card strong {
      font-size: 1.3rem;
      margin-top: 8px;
    }
    .form-highlight-card b {
      color: var(--gold);
      margin-top: 6px;
    }
    .form-highlight-card small {
      color: var(--muted);
      line-height: 1.4;
      margin-top: 8px;
    }
    .form-grid {
      display: grid;
      gap: 16px;
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }
    .form-card {
      border-top: 4px solid #8a94a6;
      padding: 15px;
    }
    .form-card-heading {
      align-items: start;
      display: flex;
      gap: 12px;
      justify-content: space-between;
    }
    .form-card-heading h3 {
      margin: 4px 0 0;
    }
    .form-card-heading strong {
      color: var(--gold);
      font-size: 1.45rem;
      line-height: 1;
    }
    .form-timeline {
      display: flex;
      gap: 6px;
      margin: 13px 0;
    }
    .form-pill {
      align-items: center;
      border-radius: 999px;
      display: inline-flex;
      font-size: 0.72rem;
      font-weight: 950;
      height: 22px;
      justify-content: center;
      width: 22px;
    }
    .form-pill.win {
      background: rgba(79, 196, 139, 0.18);
      color: #78e0a8;
    }
    .form-pill.loss {
      background: rgba(255, 111, 129, 0.16);
      color: #ff9eab;
    }
    .form-stat-grid {
      display: grid;
      gap: 8px;
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
    .form-stat-grid div {
      background: #101b28;
      border: 1px solid rgba(255, 255, 255, 0.04);
      border-radius: 7px;
      padding: 8px;
    }
    .form-stat-grid span,
    .form-card > small {
      color: var(--muted);
      display: block;
      font-size: 0.76rem;
      font-weight: 850;
    }
    .form-stat-grid b {
      display: block;
      margin-top: 3px;
    }
    .form-card > small {
      margin-top: 12px;
    }
    .status-heating-up,
    .status-hot-form {
      border-top-color: #4fc48b;
    }
    .status-cooling-down,
    .status-cold-spell {
      border-top-color: #ff6f81;
    }
    .status-stable {
      border-top-color: #62a8ff;
    }
    .status-small-sample {
      border-top-color: #8a94a6;
    }
    .chemistry-layout {
      display: grid;
      gap: 16px;
      grid-template-columns: minmax(0, 1.45fr) minmax(280px, 0.75fr);
      margin-bottom: 16px;
    }
    .chemistry-visual,
    .chemistry-panel,
    .chemistry-callout,
    .upset-column,
    .ownership-card {
      background: linear-gradient(180deg, #121d2a, #0d1620);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
    }
    .chemistry-visual {
      min-height: 520px;
      overflow-x: auto;
      padding: 10px;
    }
    .chemistry-network {
      display: block;
      height: auto;
      min-width: 820px;
      width: 100%;
    }
    .chemistry-grid ellipse {
      fill: none;
      stroke: rgba(98, 168, 255, 0.12);
      stroke-dasharray: 8 11;
      stroke-width: 1.4;
    }
    .chemistry-link-path {
      fill: none;
      opacity: 0.9;
      stroke-linecap: round;
      stroke-linejoin: round;
    }
    .chemistry-link-good {
      stroke: #4fc48b;
    }
    .chemistry-link-bad {
      stroke: #ff6f81;
    }
    .chemistry-edge-label rect {
      fill: #0b1119;
      stroke-width: 1.2;
    }
    .chemistry-edge-label-good rect {
      stroke: rgba(79, 196, 139, 0.72);
    }
    .chemistry-edge-label-bad rect {
      stroke: rgba(255, 111, 129, 0.72);
    }
    .chemistry-edge-label text {
      fill: var(--ink);
      font-size: 11px;
      font-weight: 950;
    }
    .chemistry-node circle {
      fill: #142338;
      stroke: #62a8ff;
      stroke-width: 2.5;
    }
    .chemistry-node-initials {
      fill: var(--ink);
      font-size: 14px;
      font-weight: 950;
      letter-spacing: 0;
    }
    .chemistry-node-label-bg {
      fill: rgba(11, 17, 25, 0.92);
      stroke: rgba(98, 168, 255, 0.24);
      stroke-width: 1;
    }
    .chemistry-node-label {
      fill: #dce8f5;
      font-size: 12px;
      font-weight: 900;
      letter-spacing: 0;
    }
    .chemistry-legend rect {
      fill: rgba(11, 17, 25, 0.92);
      stroke: rgba(98, 168, 255, 0.22);
    }
    .chemistry-legend text {
      fill: var(--muted);
      font-size: 12px;
      font-weight: 900;
    }
    .chemistry-empty {
      align-items: center;
      color: var(--muted);
      display: flex;
      font-weight: 850;
      min-height: 240px;
      justify-content: center;
    }
    .chemistry-callout-grid,
    .upset-stack {
      display: grid;
      gap: 12px;
    }
    .chemistry-callout {
      border-left: 4px solid #62a8ff;
      padding: 14px;
    }
    .chemistry-callout strong,
    .chemistry-callout b,
    .chemistry-callout small {
      display: block;
    }
    .chemistry-callout strong {
      font-size: 1.05rem;
      margin-top: 7px;
    }
    .chemistry-callout b {
      color: var(--gold);
      margin-top: 5px;
    }
    .chemistry-callout small {
      color: var(--muted);
      line-height: 1.4;
      margin-top: 7px;
    }
    .chemistry-good { border-left-color: #4fc48b; }
    .chemistry-bad { border-left-color: #ff6f81; }
    .chemistry-list-grid {
      display: grid;
      gap: 16px;
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
    .chemistry-panel {
      padding: 16px;
    }
    .chemistry-panel h3,
    .upset-column h3 {
      margin: 0 0 12px;
    }
    .chemistry-panel ul {
      display: grid;
      gap: 10px;
      list-style: none;
      margin: 0;
      padding: 0;
    }
    .chemistry-list-item {
      border-left: 4px solid #62a8ff;
      background: #101b28;
      border-radius: 7px;
      display: grid;
      gap: 3px;
      padding: 10px;
    }
    .chemistry-list-item span {
      color: var(--muted);
      font-size: 0.82rem;
    }
    .upset-grid {
      display: grid;
      gap: 16px;
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }
    .upset-column {
      padding: 16px;
    }
    .upset-card {
      background: #101b28;
      border: 1px solid rgba(255, 255, 255, 0.05);
      border-left: 4px solid #62a8ff;
      border-radius: 7px;
      color: var(--ink);
      display: block;
      padding: 12px;
      text-decoration: none;
    }
    .upset-upset,
    .upset-throw {
      border-left-color: #ff6f81;
    }
    .upset-stomp {
      border-left-color: #4fc48b;
    }
    .upset-card span,
    .upset-card strong,
    .upset-card b,
    .upset-card small {
      display: block;
    }
    .upset-card span {
      color: var(--muted);
      font-size: 0.78rem;
      font-weight: 950;
    }
    .upset-card strong {
      margin-top: 5px;
    }
    .upset-card b {
      color: var(--gold);
      margin-top: 5px;
    }
    .upset-card small {
      color: var(--muted);
      line-height: 1.4;
      margin-top: 7px;
    }
    .ownership-grid {
      display: grid;
      gap: 16px;
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }
    .ownership-card {
      padding: 14px;
    }
    .ownership-heading {
      align-items: center;
      display: grid;
      gap: 11px;
      grid-template-columns: 52px minmax(0, 1fr) auto;
    }
    .ownership-heading img {
      border-radius: 8px;
      height: 52px;
      object-fit: cover;
      width: 52px;
    }
    .ownership-heading h3 {
      margin: 0 0 3px;
    }
    .ownership-heading strong {
      color: var(--gold);
      font-size: 1.15rem;
    }
    .ownership-details {
      display: grid;
      gap: 8px;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      margin-top: 13px;
    }
    .ownership-details div {
      background: #101b28;
      border: 1px solid rgba(255, 255, 255, 0.04);
      border-radius: 7px;
      padding: 8px;
    }
    .ownership-details span,
    .ownership-details small,
    .ownership-recent {
      color: var(--muted);
      display: block;
      font-size: 0.76rem;
      font-weight: 850;
    }
    .ownership-details b {
      display: block;
      margin-top: 3px;
    }
    .ownership-recent {
      margin-top: 12px;
    }
    @media (max-width: 1100px) {
      .meta-spotlight-grid,
      .form-highlight-grid,
      .form-grid,
      .lab-award-grid,
      .upset-grid,
      .ownership-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }
      .experimental-hero {
        grid-template-columns: 1fr;
      }
      .chemistry-layout {
        grid-template-columns: 1fr;
      }
    }
    @media (max-width: 720px) {
      .meta-spotlight-grid,
      .form-highlight-grid,
      .form-grid,
      .lab-award-grid,
      .chemistry-list-grid,
      .upset-grid,
      .ownership-grid {
        grid-template-columns: 1fr;
      }
      .chemistry-visual {
        min-height: 430px;
        padding: 8px;
      }
      .chemistry-network {
        min-width: 720px;
      }
      .form-toolbar {
        align-items: stretch;
        flex-direction: column;
      }
    }
    """


def render_experimental_page(
    *,
    shared_style: str,
    shared_script: str,
    meta_rows: Sequence[dict[str, object]],
    form_rows: Sequence[dict[str, object]],
    hall_rows: Sequence[dict[str, object]],
    chemistry_data: dict[str, object],
    upset_data: dict[str, list[dict[str, object]]],
    ownership_rows: Sequence[dict[str, object]],
    generated_at: str,
    main_page_name: str,
    teams_page_name: str,
    draft_coach_page_name: str,
    showcases_page_name: str,
    head_to_head_page_name: str,
) -> str:
    meta_columns: list[Column] = [
        ("Tier", "tier", str, "text"),
        ("Champion", "champion", str, "text"),
        ("Role", "role", str, "text"),
        ("Games", "games", integer, "number"),
        ("Winrate", "winrate", lambda value: pct(float(value)), "number"),
        ("KDA", "kda_ratio", lambda value: two_decimal(float(value)), "number"),
        ("Unique Players", "unique_players", integer, "number"),
        ("Best Pilot", "best_pilot", str, "text"),
        ("Worst Pilot", "worst_pilot", str, "text"),
        ("Contested Score", "contested_score", lambda value: score(float(value)), "number"),
    ]
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>LoL Experimental Stats</title>
  <style>{shared_style}{render_experimental_css()}</style>
</head>
<body>
  {render_hidden_head_to_head_link(head_to_head_page_name)}
  <header>
    <div class="topline">
      <div>
        <h1>LoL Experimental Stats</h1>
        <p>Custom meta tiering, recent form, hall-of-fame awards, team chemistry, upset detection, and champion ownership experiments.</p>
      </div>
      {render_refresh_control(generated_at)}
    </div>
  </header>
  <nav>
    <a href="{html_attr(main_page_name)}#overview">Overview</a>
    <a href="{html_attr(main_page_name)}#awards">Awards</a>
    <a href="{html_attr(main_page_name)}#match-history">Matches</a>
    <a href="{html_attr(main_page_name)}#players">Players</a>
    <a href="{html_attr(main_page_name)}#champion-pools">Champion Pools</a>
    <a href="{html_attr(main_page_name)}#champions">Champions</a>
    <a href="{html_attr(main_page_name)}#role-pools">Role Pools</a>
    <a href="{html_attr(main_page_name)}#combos">Combos</a>
    <a href="{html_attr(teams_page_name)}#teams">Teams</a>
    <a href="{html_attr(draft_coach_page_name)}#draft-coach">Draft Coach</a>
    <a href="{html_attr(showcases_page_name)}">Showcases</a>
    <a href="#custom-meta">Experimental</a>
    <a href="{html_attr(main_page_name)}#deep-dive">Deep Dive</a>
  </nav>
  <main>
    <section class="section experimental-hero">
      <div class="section-title">
        <div>
          <h2>Experimental Lab</h2>
          <p class="note">These models use only the current custom-game fields: result, role, champion, KDA, kill participation, and player history.</p>
        </div>
      </div>
      <article class="experiment-note">
        <span>Current limits</span>
        <strong>No CS, gold, vision, damage, or objectives yet</strong>
        <small>The scoring leans into what the API currently provides. If those fields are added later, this page can evolve into deeper OP.GG-style post-game analysis.</small>
      </article>
    </section>
    <section id="custom-meta" class="section">
      <div class="section-title">
        <div>
          <h2>Custom Meta Tier List</h2>
          <p class="note">Champion-role strength ranked by games, winrate, KDA, unique pilots, and custom presence. Minimum sample: 2 games.</p>
        </div>
      </div>
      {render_meta_spotlights(meta_rows)}
      {render_table("custom-meta-tier-list", "Champion Role Meta", meta_rows, meta_columns, controls_html=role_filter_control("custom-meta-tier-list"))}
    </section>
    {render_recent_form_section(form_rows)}
    {render_hall_of_fame_section(hall_rows, main_page_name)}
    {render_team_chemistry_section(chemistry_data)}
    {render_upset_detector_section(upset_data, main_page_name)}
    {render_champion_ownership_section(ownership_rows)}
  </main>
  <script>{shared_script}</script>
</body>
</html>
"""


def weight_summary(weights: dict[str, float]) -> str:
    return ", ".join(f"{name} {int(weight * 100)}%" for name, weight in weights.items())


def render_tiered_teams(
    teams: Sequence[dict[str, object]], unused_players: Sequence[str]
) -> str:
    cards = []
    for team in teams:
        assignments = []
        for row in team.get("assignments", []):
            assignments.append(
                f"""
                <div class="team-role-row">
                  <b>{escape(str(row["role"]))}</b>
                  <span>{escape(str(row["name"]))}</span>
                  <small>{escape(str(row.get("fit", "")))}, {signed_integer(row["net_wins"])} net, {integer(row["games"])}g, {escape(str(row["champions"]))}</small>
                  <strong>{score(float(row["score"]))}</strong>
                </div>
                """
            )
        cards.append(
            f"""
            <article class="team-tier-card tier-{html_attr(str(team["tier"]).lower())}">
              <div class="team-tier-heading">
                <span>Tier {escape(str(team["tier"]))}</span>
                <strong>{score(float(team["score"]))}</strong>
                <small>average role score</small>
              </div>
              <div class="team-role-list">{''.join(assignments)}</div>
            </article>
            """
        )
    unused_html = ""
    if unused_players:
        unused_html = (
            f'<p class="note unused-players">Unused players after complete teams: '
            f'{escape(", ".join(unused_players))}</p>'
        )
    return f"""
    <div class="team-tier-grid">{''.join(cards)}</div>
    {unused_html}
    """


def render_ban_planner_css() -> str:
    return """
    .ban-target-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 14px;
      margin-bottom: 16px;
    }
    .ban-target-card {
      position: relative;
      display: grid;
      grid-template-columns: 58px minmax(0, 1fr);
      gap: 12px;
      min-height: 150px;
      padding: 14px;
      background:
        linear-gradient(135deg, rgba(255, 111, 129, 0.12), rgba(17, 25, 35, 0) 48%),
        var(--panel);
      border: 1px solid rgba(255, 111, 129, 0.28);
      border-radius: 8px;
      box-shadow: var(--shadow);
      overflow: hidden;
    }
    .ban-target-card::before {
      content: "";
      position: absolute;
      inset: 0 0 auto;
      height: 3px;
      background: var(--red);
    }
    .practice-target-card {
      background:
        linear-gradient(135deg, rgba(240, 201, 106, 0.13), rgba(17, 25, 35, 0) 48%),
        var(--panel);
      border-color: rgba(240, 201, 106, 0.3);
    }
    .practice-target-card::before {
      background: var(--gold);
    }
    .ban-card-rank {
      position: absolute;
      right: 12px;
      top: 10px;
      color: rgba(232, 238, 246, 0.18);
      font-size: 2rem;
      font-weight: 900;
      line-height: 1;
    }
    .ban-card-icon {
      width: 54px;
      height: 54px;
      border-radius: 10px;
      border: 1px solid rgba(240, 201, 106, 0.34);
      object-fit: cover;
      display: block;
    }
    .ban-card-copy {
      display: grid;
      gap: 5px;
      align-content: start;
      min-width: 0;
      padding-right: 22px;
    }
    .ban-card-copy span {
      color: var(--muted);
      font-size: 0.76rem;
      font-weight: 900;
      text-transform: uppercase;
    }
    .ban-card-copy strong {
      font-size: 1.08rem;
      line-height: 1.2;
      overflow-wrap: anywhere;
    }
    .ban-card-copy b {
      color: var(--gold);
      font-size: 1rem;
    }
    .ban-planner-panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
      overflow: hidden;
    }
    .ban-board-actions {
      display: flex;
      justify-content: flex-end;
    }
    .draft-clear,
    .draft-import-button,
    .champion-pool-clear {
      min-height: 34px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #172331;
      color: var(--ink);
      padding: 7px 10px;
      font-weight: 800;
      cursor: pointer;
    }
    .draft-clear:hover,
    .draft-import-button:hover,
    .champion-pool-clear:hover {
      background: #1d2b3b;
    }
    .draft-import-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
      padding: 16px 16px 0;
    }
    .draft-import-panel {
      display: grid;
      gap: 10px;
      min-width: 0;
    }
    .draft-import-panel label {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
      color: var(--muted);
      font-size: 0.78rem;
      font-weight: 900;
      text-transform: uppercase;
    }
    .draft-import-panel textarea {
      width: 100%;
      min-height: 154px;
      resize: vertical;
      border: 1px solid #2a384a;
      border-radius: 8px;
      background: #0b1119;
      color: var(--ink);
      padding: 10px;
      font: 0.88rem Consolas, "Courier New", monospace;
      line-height: 1.35;
    }
    .draft-import-panel textarea:focus {
      outline: 2px solid rgba(240, 201, 106, 0.36);
      outline-offset: 1px;
    }
    .draft-import-actions,
    .champion-pool-actions {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      flex-wrap: wrap;
    }
    .draft-import-status,
    .champion-pool-status {
      color: var(--muted);
      font-size: 0.84rem;
      font-weight: 800;
    }
    .champion-pool-list {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      min-height: 32px;
      max-height: 82px;
      overflow: auto;
      padding-right: 4px;
    }
    .champion-pool-list .champion-chip {
      font-size: 0.74rem;
      padding: 5px 7px;
    }
    .draft-board {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
      gap: 16px;
      padding: 16px;
      align-items: center;
    }
    .draft-side {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #0f1721;
      overflow: hidden;
      min-width: 0;
    }
    .draft-side-blue {
      border-color: rgba(98, 168, 255, 0.38);
    }
    .draft-side-red {
      border-color: rgba(255, 111, 129, 0.38);
    }
    .draft-side-heading {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      gap: 10px;
      padding: 12px;
      border-bottom: 1px solid var(--line);
    }
    .draft-side-blue .draft-side-heading {
      background: rgba(98, 168, 255, 0.12);
    }
    .draft-side-red .draft-side-heading {
      background: rgba(255, 111, 129, 0.12);
    }
    .draft-side-heading h3 {
      font-size: 1rem;
    }
    .draft-side-heading small {
      font-weight: 800;
    }
    .draft-slots {
      display: grid;
    }
    .draft-slot {
      display: grid;
      grid-template-columns: 72px minmax(0, 1fr) 72px;
      gap: 10px;
      align-items: center;
      padding: 10px 12px;
      border-bottom: 1px solid #202b39;
    }
    .draft-slot:last-child {
      border-bottom: 0;
    }
    .draft-slot span {
      color: var(--muted);
      font-size: 0.74rem;
      font-weight: 900;
    }
    .draft-slot .draft-fit {
      text-align: right;
      color: var(--muted);
      font-size: 0.72rem;
      font-weight: 900;
      white-space: nowrap;
    }
    .draft-slot input {
      width: 100%;
      min-width: 0;
      min-height: 38px;
      border: 1px solid #2a384a;
      border-radius: 6px;
      background: #0b1119;
      color: var(--ink);
      padding: 8px 10px;
      font-weight: 800;
    }
    .draft-slot input:focus {
      outline: 2px solid rgba(240, 201, 106, 0.36);
      outline-offset: 1px;
    }
    .draft-vs {
      width: 52px;
      height: 52px;
      display: grid;
      place-items: center;
      border: 1px solid rgba(240, 201, 106, 0.38);
      border-radius: 8px;
      color: var(--gold);
      background: #0b1119;
      font-weight: 950;
      letter-spacing: 0;
    }
    .draft-coach-panel {
      border-top: 1px solid var(--line);
      display: grid;
      gap: 14px;
      padding: 0 16px 16px;
    }
    .draft-coach-panel .section-heading {
      padding-left: 0;
      padding-right: 0;
      border-bottom: 0;
    }
    .draft-coach-summary {
      color: var(--muted);
      font-size: 0.86rem;
      font-weight: 800;
    }
    .draft-turn-list {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }
    .draft-turn-card {
      border: 1px solid var(--line);
      border-radius: 8px;
      background:
        linear-gradient(135deg, rgba(98, 168, 255, 0.08), rgba(17, 25, 35, 0) 46%),
        #0f1721;
      overflow: hidden;
      min-width: 0;
    }
    .draft-turn-card[data-side="red"] {
      background:
        linear-gradient(135deg, rgba(255, 111, 129, 0.09), rgba(17, 25, 35, 0) 46%),
        #0f1721;
    }
    .draft-turn-card[data-action="ban"] {
      border-color: rgba(255, 111, 129, 0.28);
    }
    .draft-turn-card[data-action="pick"] {
      border-color: rgba(101, 220, 154, 0.26);
    }
    .draft-turn-top {
      display: flex;
      justify-content: space-between;
      gap: 10px;
      padding: 10px 12px;
      border-bottom: 1px solid #202b39;
      color: var(--muted);
      font-size: 0.74rem;
      font-weight: 900;
      text-transform: uppercase;
    }
    .draft-turn-main {
      display: grid;
      grid-template-columns: 44px minmax(0, 1fr) auto;
      gap: 10px;
      align-items: center;
      padding: 10px 12px;
    }
    .draft-turn-main img {
      width: 42px;
      height: 42px;
      border-radius: 8px;
      border: 1px solid rgba(240, 201, 106, 0.3);
      object-fit: cover;
      display: block;
    }
    .draft-turn-copy {
      display: grid;
      gap: 3px;
      min-width: 0;
    }
    .draft-turn-copy strong,
    .draft-turn-copy span,
    .draft-turn-copy small {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .draft-turn-copy span {
      color: var(--blue);
      font-weight: 900;
      font-size: 0.86rem;
    }
    .draft-turn-card[data-side="red"] .draft-turn-copy span {
      color: var(--red);
    }
    .draft-turn-score {
      color: var(--gold);
      font-weight: 950;
      font-variant-numeric: tabular-nums;
    }
    .draft-tag-row {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      padding: 0 12px 12px;
    }
    .draft-tag {
      border: 1px solid var(--line);
      border-radius: 999px;
      background: #0b1119;
      color: var(--muted);
      font-size: 0.72rem;
      font-weight: 900;
      padding: 4px 7px;
      max-width: 100%;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .draft-tag-safe {
      color: var(--green);
      border-color: rgba(101, 220, 154, 0.32);
    }
    .draft-tag-ceiling {
      color: var(--blue);
      border-color: rgba(98, 168, 255, 0.32);
    }
    .draft-tag-trap {
      color: var(--red);
      border-color: rgba(255, 111, 129, 0.32);
    }
    .draft-tag-counter {
      color: var(--gold);
      border-color: rgba(240, 201, 106, 0.34);
    }
    .ban-results-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
      padding: 0 16px 16px;
    }
    .practice-section {
      border-top: 1px solid var(--line);
      display: grid;
      gap: 16px;
      padding-bottom: 16px;
    }
    .practice-section .section-heading {
      border-bottom: 0;
      padding-bottom: 0;
    }
    .practice-target-grid {
      padding: 0 16px;
    }
    .practice-target-grid {
      margin-bottom: 0;
    }
    .ban-result-panel {
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
      min-width: 0;
    }
    .ban-result-heading {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
      padding: 12px;
      background: #0f1721;
      border-bottom: 1px solid var(--line);
    }
    .ban-result-heading h3 {
      margin-bottom: 3px;
    }
    .ban-result-heading strong {
      color: var(--gold);
      font-variant-numeric: tabular-nums;
      white-space: nowrap;
    }
    .ban-result-list,
    .pick-result-list {
      display: grid;
      min-height: 190px;
    }
    .ban-pick-row {
      display: grid;
      grid-template-columns: 34px 44px minmax(0, 1fr) 54px;
      gap: 10px;
      align-items: center;
      padding: 10px 12px;
      border-bottom: 1px solid #202b39;
      min-width: 0;
    }
    .ban-pick-row:last-child {
      border-bottom: 0;
    }
    .ban-pick-row > b {
      color: var(--muted);
      font-size: 0.8rem;
      text-align: center;
    }
    .ban-pick-row img {
      width: 42px;
      height: 42px;
      border-radius: 8px;
      border: 1px solid rgba(240, 201, 106, 0.28);
      object-fit: cover;
      display: block;
    }
    .ban-pick-copy {
      display: grid;
      gap: 2px;
      min-width: 0;
    }
    .ban-pick-copy strong,
    .ban-pick-copy span,
    .ban-pick-copy small {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .ban-pick-copy span {
      color: var(--blue);
      font-weight: 900;
      font-size: 0.86rem;
    }
    .pick-result-panel .ban-pick-copy span {
      color: var(--green);
    }
    .ban-pick-row em {
      color: var(--green);
      font-style: normal;
      font-weight: 900;
      text-align: right;
      font-variant-numeric: tabular-nums;
    }
    .ban-empty {
      color: var(--muted);
      padding: 18px;
      font-weight: 800;
      align-self: center;
    }
    @media (max-width: 1040px) {
      .ban-target-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }
    }
    @media (max-width: 720px) {
      .ban-target-grid,
      .draft-import-grid,
      .ban-results-grid {
        grid-template-columns: 1fr;
      }
      .draft-board {
        grid-template-columns: 1fr;
      }
      .draft-turn-list {
        grid-template-columns: 1fr;
      }
      .draft-vs {
        justify-self: center;
      }
      .draft-slot {
        grid-template-columns: 54px minmax(0, 1fr);
      }
      .draft-slot .draft-fit {
        grid-column: 2;
        text-align: left;
      }
      .ban-pick-row {
        grid-template-columns: 28px 40px minmax(0, 1fr) 48px;
        gap: 8px;
      }
    }
    """


def render_target_ban_cards(
    target_ban_rows: Sequence[dict[str, object]], limit: int = 6
) -> str:
    visible_rows = list(qualify(target_ban_rows, TARGET_BAN_MIN_GAMES) or target_ban_rows)[
        :limit
    ]
    cards = []
    for index, row in enumerate(visible_rows, start=1):
        player = str(row.get("name", "-"))
        champion = str(row.get("champion", "-"))
        cards.append(
            f"""
            <article class="ban-target-card">
              <div class="ban-card-rank">#{index}</div>
              <img class="ban-card-icon" src="{html_attr(champion_icon_url(champion))}" alt="{html_attr(champion)}">
              <div class="ban-card-copy">
                <span>{escape(str(row.get("confidence", "Low")))} target</span>
                <strong>{escape(player)} - {escape(champion)}</strong>
                <b>{score(float(row.get("ban_score", 0)))} ban score</b>
                <small>{escape(str(row.get("target_detail", "")))}</small>
                <small>{pct(float(row.get("player_winrate", 0)))} player WR, {signed_pct(float(row.get("lift", 0)))} lift, {escape(str(row.get("top_roles", "-")))}</small>
              </div>
            </article>
            """
        )
    if not cards:
        cards.append('<div class="empty-state">No player/champion picks available yet.</div>')
    return f'<div class="ban-target-grid">{"".join(cards)}</div>'


def render_practice_pick_cards(
    practice_pick_rows: Sequence[dict[str, object]], limit: int = 6
) -> str:
    visible_rows = list(practice_pick_rows)[:limit]
    cards = []
    for index, row in enumerate(visible_rows, start=1):
        player = str(row.get("name", "-"))
        champion = str(row.get("champion", "-"))
        cards.append(
            f"""
            <article class="ban-target-card practice-target-card">
              <div class="ban-card-rank">#{index}</div>
              <img class="ban-card-icon" src="{html_attr(champion_icon_url(champion))}" alt="{html_attr(champion)}">
              <div class="ban-card-copy">
                <span>{escape(str(row.get("confidence", "Low")))} sample</span>
                <strong>{escape(player)} - {escape(champion)}</strong>
                <b>{score(float(row.get("practice_score", 0)))} practice score</b>
                <small>{escape(str(row.get("practice_detail", "")))}</small>
                <small>{escape(str(row.get("top_roles", "-")))}</small>
              </div>
            </article>
            """
        )
    if not cards:
        cards.append(
            f'<div class="empty-state">No {PRACTICE_PICK_MIN_GAMES}+ game player/champion combos are below {pct(PRACTICE_PICK_MAX_WINRATE)} WR and at least {pct(PRACTICE_PICK_BASELINE_GAP)} below player baseline yet.</div>'
        )
    return f'<div class="ban-target-grid practice-target-grid">{"".join(cards)}</div>'


def render_target_ban_section(
    target_ban_rows: Sequence[dict[str, object]],
    practice_pick_rows: Sequence[dict[str, object]],
    player_rows: Sequence[dict[str, object]],
) -> str:
    player_options = "".join(
        f'<option value="{html_attr(row["name"])}"></option>'
        for row in sorted(player_rows, key=lambda item: str(item["name"]))
    )

    def render_draft_side(team_key: str, title: str) -> str:
        role_inputs = []
        for role in ROLE_ORDER:
            role_inputs.append(
                f"""
                <label class="draft-slot">
                  <span>{escape(role)}</span>
                  <input type="text" list="ban-player-list" data-draft-team="{html_attr(team_key)}" data-draft-role="{escape(role)}" autocomplete="off" aria-label="{html_attr(title)} {escape(role)} player">
                  <small class="draft-fit" data-draft-fit="{html_attr(team_key)}-{escape(role)}"></small>
                </label>
                """
            )
        return f"""
        <section class="draft-side draft-side-{html_attr(team_key)}">
          <div class="draft-side-heading">
            <h3>{escape(title)}</h3>
            <small>5 players</small>
          </div>
          <div class="draft-slots">{''.join(role_inputs)}</div>
        </section>
        """

    return f"""
    <section id="draft-coach" class="section">
      <div class="section-title">
        <div>
          <h2>Draft Coach</h2>
          <p class="note">Target bans, tournament draft simulation, best available picks, and practice picks in one board. Ban targets use adjusted winrate, sample size, KDA, takedowns, MVP rating, and lift against that player's baseline.</p>
        </div>
      </div>
      {render_target_ban_cards(target_ban_rows)}
      <section class="ban-planner-panel">
        <div class="section-heading">
          <div>
            <h3>Draft Board</h3>
            <small>Blue bans target Red players; Red bans target Blue players</small>
          </div>
          <div class="ban-board-actions">
            <button type="button" class="draft-clear" data-draft-clear>Clear</button>
          </div>
        </div>
        <datalist id="ban-player-list">{player_options}</datalist>
        <div class="draft-import-grid">
          <section class="draft-import-panel">
            <label for="draft-import-text">
              <span>Draft Text</span>
              <button type="button" class="draft-import-button" data-draft-import>Apply Draft</button>
            </label>
            <textarea id="draft-import-text" data-draft-import-text spellcheck="false" placeholder="Blue Team&#10;Role    Player   Fit&#10;------  -------  --------&#10;TOP     Jay      Off-role&#10;..."></textarea>
            <div class="draft-import-actions">
              <span class="draft-import-status" data-draft-import-status>No draft imported</span>
            </div>
          </section>
          <section class="draft-import-panel">
            <label for="champion-pool-text">
              <span>Champion Pool</span>
              <button type="button" class="champion-pool-clear" data-champion-pool-clear>Clear Pool</button>
            </label>
            <textarea id="champion-pool-text" data-champion-pool-text spellcheck="false" placeholder="Aatrox, Ahri, Jinx, Leona, Viktor"></textarea>
            <div class="champion-pool-actions">
              <span class="champion-pool-status" data-champion-pool-status>All champions eligible</span>
            </div>
            <div class="champion-pool-list" data-champion-pool-list></div>
          </section>
        </div>
        <div class="draft-board">
          {render_draft_side("blue", "Blue Team")}
          <div class="draft-vs">VS</div>
          {render_draft_side("red", "Red Team")}
        </div>
        <section class="draft-coach-panel">
          <div class="section-heading">
            <div>
              <h3>Tournament Draft Simulation</h3>
              <small>Tournament order: Blue/Red alternating bans, then B1, R1+R2, B2+B3, R3+R4, B4+B5, R5. Main cards show the likely simulation; Ideal tags show first choice before earlier blocks.</small>
            </div>
          </div>
          <div class="draft-coach-summary" data-draft-coach-summary>Enter teams and a champion pool to simulate the draft.</div>
          <div class="draft-turn-list" data-draft-coach-turns></div>
        </section>
        <div class="ban-results-grid">
          <section class="ban-result-panel ban-result-blue">
            <div class="ban-result-heading">
              <div>
                <h3>Blue Bans</h3>
                <small data-ban-targets="blue">Targets: none</small>
              </div>
              <strong data-ban-count="blue">0/3</strong>
            </div>
            <div class="ban-result-list" data-ban-results="blue"></div>
          </section>
          <section class="ban-result-panel ban-result-red">
            <div class="ban-result-heading">
              <div>
                <h3>Red Bans</h3>
                <small data-ban-targets="red">Targets: none</small>
              </div>
              <strong data-ban-count="red">0/3</strong>
            </div>
            <div class="ban-result-list" data-ban-results="red"></div>
          </section>
          <section class="ban-result-panel pick-result-panel pick-result-blue">
            <div class="ban-result-heading">
              <div>
                <h3>Blue Picks</h3>
                <small data-pick-targets="blue">Players: none</small>
              </div>
              <strong data-pick-count="blue">0/5</strong>
            </div>
            <div class="pick-result-list" data-pick-results="blue"></div>
          </section>
          <section class="ban-result-panel pick-result-panel pick-result-red">
            <div class="ban-result-heading">
              <div>
                <h3>Red Picks</h3>
                <small data-pick-targets="red">Players: none</small>
              </div>
              <strong data-pick-count="red">0/5</strong>
            </div>
            <div class="pick-result-list" data-pick-results="red"></div>
          </section>
        </div>
        <section id="practice-picks" class="practice-section">
          <div class="section-heading">
            <div>
              <h3>Practice Picks</h3>
              <small>Lab picks: {PRACTICE_PICK_MIN_GAMES}+ game player/champion combos below {pct(PRACTICE_PICK_MAX_WINRATE)} WR and at least {pct(PRACTICE_PICK_BASELINE_GAP)} below that player's baseline</small>
            </div>
          </div>
          {render_practice_pick_cards(practice_pick_rows)}
        </section>
      </section>
    </section>
    """


def render_ban_planner_script(
    target_ban_rows: Sequence[dict[str, object]],
    target_pick_rows: Sequence[dict[str, object]],
    player_rows: Sequence[dict[str, object]],
    champion_matchup_rows: Sequence[dict[str, object]],
) -> str:
    target_data = []
    for row in target_ban_rows:
        champion = str(row.get("champion", ""))
        target_data.append(
            {
                "player": str(row.get("name", "")),
                "champion": champion,
                "championIcon": champion_icon_url(champion),
                "roles": str(row.get("top_roles", "")),
                "games": int(row.get("games", 0)),
                "wins": int(row.get("wins", 0)),
                "winrate": round(float(row.get("winrate", 0)), 4),
                "kda": round(float(row.get("kda_ratio", 0)), 2),
                "avgKills": round(float(row.get("avg_kills", 0)), 1),
                "avgDeaths": round(float(row.get("avg_deaths", 0)), 1),
                "avgAssists": round(float(row.get("avg_assists", 0)), 1),
                "score": round(float(row.get("ban_score", 0)), 1),
                "lift": round(float(row.get("lift", 0)), 4),
                "playerWinrate": round(float(row.get("player_winrate", 0)), 4),
                "mvpScore": round(float(row.get("mvp_score", 0)), 1),
                "playerThreat": round(float(row.get("player_threat", 0)), 4),
                "confidence": str(row.get("confidence", "Low")),
            }
        )
    pick_data = []
    for row in target_pick_rows:
        champion = str(row.get("champion", ""))
        pick_data.append(
            {
                "player": str(row.get("name", "")),
                "champion": champion,
                "championIcon": champion_icon_url(champion),
                "role": str(row.get("role", "")),
                "roles": str(row.get("top_roles", "")),
                "games": int(row.get("games", 0)),
                "wins": int(row.get("wins", 0)),
                "winrate": round(float(row.get("winrate", 0)), 4),
                "kda": round(float(row.get("kda_ratio", 0)), 2),
                "avgKills": round(float(row.get("avg_kills", 0)), 1),
                "avgDeaths": round(float(row.get("avg_deaths", 0)), 1),
                "avgAssists": round(float(row.get("avg_assists", 0)), 1),
                "score": round(float(row.get("ban_score", 0)), 1),
                "lift": round(float(row.get("lift", 0)), 4),
                "playerWinrate": round(float(row.get("player_winrate", 0)), 4),
                "mvpScore": round(float(row.get("mvp_score", 0)), 1),
                "playerThreat": round(float(row.get("player_threat", 0)), 4),
                "confidence": str(row.get("confidence", "Low")),
            }
        )
    champion_data = [
        {
            "name": champion,
            "icon": champion_icon_url(champion),
            "assetId": champion_asset_id(champion),
        }
        for champion in CHAMPION_ROSTER
    ]
    matchup_data = []
    for row in champion_matchup_rows:
        matchup_data.append(
            {
                "role": str(row.get("role", "")),
                "champion": str(row.get("champion", "")),
                "opponentChampion": str(row.get("opponent_champion", "")),
                "games": int(row.get("games", 0)),
                "winrate": round(float(row.get("winrate", 0)), 4),
                "kdaEdge": round(float(row.get("kda_edge", 0)), 2),
                "record": str(row.get("record", "")),
            }
        )
    player_names = sorted(str(row.get("name", "")) for row in player_rows)
    target_json = json.dumps(target_data, ensure_ascii=True).replace("</", "<\\/")
    pick_json = json.dumps(pick_data, ensure_ascii=True).replace("</", "<\\/")
    champion_json = json.dumps(champion_data, ensure_ascii=True).replace("</", "<\\/")
    matchup_json = json.dumps(matchup_data, ensure_ascii=True).replace("</", "<\\/")
    player_json = json.dumps(player_names, ensure_ascii=True).replace("</", "<\\/")
    script = """
    const banTargetData = __BAN_TARGET_DATA__;
    const pickTargetData = __PICK_TARGET_DATA__;
    const championRosterData = __CHAMPION_ROSTER_DATA__;
    const championMatchupData = __CHAMPION_MATCHUP_DATA__;
    const banPlayerNames = __BAN_PLAYER_NAMES__;
    const draftInputs = Array.from(document.querySelectorAll("[data-draft-team]"));
    const draftImportText = document.querySelector("[data-draft-import-text]");
    const draftImportButton = document.querySelector("[data-draft-import]");
    const draftImportStatus = document.querySelector("[data-draft-import-status]");
    const championPoolText = document.querySelector("[data-champion-pool-text]");
    const championPoolStatus = document.querySelector("[data-champion-pool-status]");
    const championPoolList = document.querySelector("[data-champion-pool-list]");
    const championPoolClear = document.querySelector("[data-champion-pool-clear]");
    const draftCoachSummary = document.querySelector("[data-draft-coach-summary]");
    const draftCoachTurns = document.querySelector("[data-draft-coach-turns]");

    function formatBanPercent(value) {
      return `${(Number(value) * 100).toFixed(1)}%`;
    }

    function formatSignedBanPercent(value) {
      const number = Number(value);
      const sign = number >= 0 ? "+" : "";
      return `${sign}${formatBanPercent(number)}`;
    }

    function escapeBanHtml(value) {
      const element = document.createElement("div");
      element.textContent = String(value ?? "");
      return element.innerHTML;
    }

    function normalizeLookupName(value) {
      return String(value || "")
        .toLowerCase()
        .replace(/&/g, "and")
        .replace(/[^a-z0-9]/g, "");
    }

    const championByKey = new Map();
    championRosterData.forEach(champion => {
      [champion.name, champion.assetId].forEach(value => {
        const key = normalizeLookupName(value);
        if (key && !championByKey.has(key)) {
          championByKey.set(key, champion.name);
        }
      });
    });
    const roleEligibleChampions = new Map();
    pickTargetData.forEach(row => {
      if (!roleEligibleChampions.has(row.role)) {
        roleEligibleChampions.set(row.role, new Set());
      }
      roleEligibleChampions.get(row.role).add(row.champion);
    });
    const roleMetaAccumulator = new Map();
    pickTargetData.forEach(row => {
      const key = `${row.role}|||${row.champion}`;
      if (!roleMetaAccumulator.has(key)) {
        roleMetaAccumulator.set(key, {
          role: row.role,
          champion: row.champion,
          championIcon: row.championIcon,
          games: 0,
          wins: 0,
          weightedKda: 0,
          score: 0,
          pilots: new Set()
        });
      }
      const entry = roleMetaAccumulator.get(key);
      const games = Number(row.games) || 0;
      entry.games += games;
      entry.wins += Number(row.wins) || 0;
      entry.weightedKda += (Number(row.kda) || 0) * games;
      entry.score = Math.max(entry.score, Number(row.score) || 0);
      entry.pilots.add(row.player);
    });
    const roleMetaData = Array.from(roleMetaAccumulator.values()).map(row => ({
      player: "Role meta",
      champion: row.champion,
      championIcon: row.championIcon,
      role: row.role,
      roles: row.role,
      games: row.games,
      wins: row.wins,
      winrate: row.games ? row.wins / row.games : 0,
      kda: row.games ? row.weightedKda / row.games : 0,
      avgKills: 0,
      avgDeaths: 0,
      avgAssists: 0,
      score: Math.max(35, row.score - 8),
      lift: 0,
      playerWinrate: 0,
      mvpScore: 0,
      playerThreat: 0,
      confidence: `${row.pilots.size} pilots`
    }));

    function canonicalPlayerName(value) {
      const term = String(value || "").trim().toLowerCase();
      if (!term) return "";
      const exact = banPlayerNames.find(name => name.toLowerCase() === term);
      if (exact) return exact;
      const matches = banPlayerNames.filter(name => name.toLowerCase().includes(term));
      return matches.length === 1 ? matches[0] : "";
    }

    function canonicalChampionName(value) {
      const key = normalizeLookupName(value);
      if (!key) return "";
      if (championByKey.has(key)) return championByKey.get(key);
      const matches = championRosterData.filter(champion => {
        const championKey = normalizeLookupName(champion.name);
        return championKey.includes(key) || key.includes(championKey);
      });
      return matches.length === 1 ? matches[0].name : "";
    }

    function championPoolState() {
      const raw = championPoolText ? championPoolText.value.trim() : "";
      if (!raw) {
        return { limited: false, names: [], set: null, unmatched: [] };
      }
      const seen = new Set();
      const unmatched = [];
      const names = [];
      raw.split(/[,;\\n\\r\\t]+/)
        .map(item => item.trim())
        .filter(Boolean)
        .forEach(item => {
          const champion = canonicalChampionName(item);
          if (!champion) {
            unmatched.push(item);
            return;
          }
          if (!seen.has(champion)) {
            seen.add(champion);
            names.push(champion);
          }
        });
      return { limited: true, names, set: seen, unmatched };
    }

    function rowInChampionPool(row, pool) {
      return !pool.limited || pool.set.has(row.champion);
    }

    function championHasRole(champion, role) {
      return Boolean(roleEligibleChampions.get(role)?.has(champion));
    }

    function updateChampionPoolDisplay(pool) {
      if (!championPoolStatus || !championPoolList) return;
      if (!pool.limited) {
        championPoolStatus.textContent = "All champions eligible";
        championPoolList.innerHTML = "";
        return;
      }
      const suffix = pool.unmatched.length
        ? `, ${pool.unmatched.length} unmatched`
        : "";
      championPoolStatus.textContent = `${pool.names.length}/40 champions matched${suffix}`;
      championPoolList.innerHTML = pool.names.slice(0, 40).map(name => (
        `<span class="champion-chip">${escapeBanHtml(name)}</span>`
      )).join("");
    }

    function setDraftFit(team, role, value) {
      const fit = document.querySelector(`[data-draft-fit="${team}-${role}"]`);
      if (fit) fit.textContent = value || "";
    }

    function selectedDraftEntries(team) {
      const seen = new Set();
      return draftInputs
        .filter(input => input.dataset.draftTeam === team)
        .map(input => ({
          player: canonicalPlayerName(input.value),
          role: input.dataset.draftRole,
          fit: document.querySelector(`[data-draft-fit="${team}-${input.dataset.draftRole}"]`)?.textContent || ""
        }))
        .filter(entry => {
          if (!entry.player || seen.has(entry.player)) return false;
          seen.add(entry.player);
          return true;
        });
    }

    function banCandidatesForEntry(entry) {
      const exactRows = pickTargetData
        .filter(row => row.player === entry.player && row.role === entry.role)
        .map(row => ({
          ...row,
          assignedRole: entry.role,
          fit: entry.fit,
          roleMatched: true,
          draftScore: row.score + 4
        }));
      const exactChampions = new Set(exactRows.map(row => row.champion.toLowerCase()));
      const fallbackRows = banTargetData
        .filter(row => row.player === entry.player)
        .filter(row => championHasRole(row.champion, entry.role))
        .filter(row => !exactChampions.has(row.champion.toLowerCase()))
        .map(row => ({
          ...row,
          assignedRole: entry.role,
          fit: entry.fit,
          roleMatched: false,
          draftScore: row.score - 6
        }));
      return exactRows.concat(fallbackRows);
    }

    function championDraftKey(champion) {
      return String(champion || "").toLowerCase();
    }

    function sideName(team) {
      return team === "blue" ? "Blue" : "Red";
    }

    function opponentTeam(team) {
      return team === "blue" ? "red" : "blue";
    }

    function entriesForSide(team, blueEntries, redEntries) {
      return team === "blue" ? blueEntries : redEntries;
    }

    function picksForSide(team, state) {
      return team === "blue" ? state.bluePicks : state.redPicks;
    }

    function bansForSide(team, state) {
      return team === "blue" ? state.blueBans : state.redBans;
    }

    function championMatchupSignal(champion, opponentChampion, role) {
      if (!champion || !opponentChampion || !role) {
        return { bonus: 0, label: "" };
      }
      const matchup = championMatchupData.find(row =>
        row.role === role &&
        (
          (row.champion === champion && row.opponentChampion === opponentChampion) ||
          (row.champion === opponentChampion && row.opponentChampion === champion)
        )
      );
      if (!matchup) {
        return { bonus: 0, label: "" };
      }
      const direct = matchup.champion === champion;
      const winrate = direct ? Number(matchup.winrate) : 1 - Number(matchup.winrate);
      const kdaEdge = direct ? Number(matchup.kdaEdge) : -Number(matchup.kdaEdge);
      const games = Number(matchup.games) || 0;
      const bonus = ((winrate - 0.5) * 24) + (Math.max(-3, Math.min(3, kdaEdge)) * 2) + Math.min(games, 4);
      const edge = kdaEdge >= 0 ? `+${kdaEdge.toFixed(1)}` : kdaEdge.toFixed(1);
      return {
        bonus,
        label: `Counter ${opponentChampion}: ${formatBanPercent(winrate)}, ${games}g, KDA ${edge}`
      };
    }

    function pickCandidatesForEntry(entry, pool, unavailableChampions, opponentPicks = []) {
      const unavailable = unavailableChampions || new Set();
      const sameRoleOpponent = opponentPicks.find(row => row.assignedRole === entry.role);
      const decorate = (row, roleMatched, metaFallback = false) => {
        const matchup = championMatchupSignal(row.champion, sameRoleOpponent?.champion || "", entry.role);
        const sampleBonus = Math.min(Number(row.games) || 0, 8) * 0.8;
        const roleBonus = roleMatched ? 8 : -4;
        const historyPenalty = metaFallback ? -18 : 0;
        const comfortBonus =
          (Number(row.winrate) * 8) +
          (Math.min(Number(row.kda) || 0, 6) * 2) +
          Math.max(-4, Math.min(8, Number(row.lift || 0) * 50));
        return {
          ...row,
          player: entry.player,
          assignedRole: entry.role,
          fit: entry.fit,
          roleMatched,
          metaFallback,
          matchupBonus: matchup.bonus,
          matchupLabel: matchup.label,
          pickScore: Number(row.score || 0) + roleBonus + sampleBonus + comfortBonus + matchup.bonus + historyPenalty
        };
      };
      const exactRows = pickTargetData
        .filter(row => row.player === entry.player && row.role === entry.role)
        .map(row => decorate(row, true));
      const exactChampions = new Set(exactRows.map(row => championDraftKey(row.champion)));
      const fallbackRows = banTargetData
        .filter(row => row.player === entry.player)
        .filter(row => championHasRole(row.champion, entry.role))
        .filter(row => !exactChampions.has(championDraftKey(row.champion)))
        .map(row => decorate(row, false));
      const personalChampions = new Set(
        exactRows.concat(fallbackRows).map(row => championDraftKey(row.champion))
      );
      const metaRows = roleMetaData
        .filter(row => row.role === entry.role)
        .filter(row => !personalChampions.has(championDraftKey(row.champion)))
        .map(row => decorate(row, true, true));
      const seen = new Set();
      return exactRows.concat(fallbackRows, metaRows)
        .filter(row => rowInChampionPool(row, pool))
        .filter(row => !unavailable.has(championDraftKey(row.champion)))
        .filter(row => {
          const key = championDraftKey(row.champion);
          if (seen.has(key)) return false;
          seen.add(key);
          return true;
        })
        .sort((left, right) =>
          Number(right.pickScore) - Number(left.pickScore) ||
          Number(right.score) - Number(left.score) ||
          Number(right.winrate) - Number(left.winrate) ||
          Number(right.games) - Number(left.games)
        );
    }

    function denyCandidatesForEntries(entries, pool, unavailableChampions, existingBans = []) {
      const unavailable = unavailableChampions || new Set();
      const targetCounts = new Map();
      existingBans.forEach(row => {
        targetCounts.set(row.player, (targetCounts.get(row.player) || 0) + 1);
      });
      return entries
        .flatMap(entry => banCandidatesForEntry(entry))
        .filter(row => rowInChampionPool(row, pool))
        .filter(row => !unavailable.has(championDraftKey(row.champion)))
        .map(row => ({
          ...row,
          denyScore: Number(row.draftScore || row.score || 0) - ((targetCounts.get(row.player) || 0) * 9)
        }))
        .sort((left, right) =>
          Number(right.denyScore) - Number(left.denyScore) ||
          Number(right.draftScore) - Number(left.draftScore) ||
          Number(right.winrate) - Number(left.winrate) ||
          Number(right.games) - Number(left.games)
        );
    }

    function bestSafePick(candidates) {
      return candidates
        .filter(row => !row.metaFallback && Number(row.games) >= 3 && Number(row.winrate) >= 0.5)
        .sort((left, right) =>
          Number(right.games) - Number(left.games) ||
          Number(right.pickScore) - Number(left.pickScore)
        )[0] || candidates.find(row => !row.metaFallback && Number(row.games) >= 2) || null;
    }

    function highCeilingPick(candidates) {
      return candidates
        .slice()
        .sort((left, right) =>
          ((Number(right.kda) || 0) * 8 + Number(right.winrate) * 35 + Number(right.score)) -
          ((Number(left.kda) || 0) * 8 + Number(left.winrate) * 35 + Number(left.score))
        )[0] || null;
    }

    function trapPick(candidates) {
      return candidates
        .filter(row => !row.metaFallback && Number(row.games) >= 2 && (Number(row.winrate) < 0.42 || Number(row.lift || 0) < -0.08))
        .sort((left, right) =>
          Number(left.winrate) - Number(right.winrate) ||
          Number(left.score) - Number(right.score) ||
          Number(right.games) - Number(left.games)
        )[0] || null;
    }

    function opponentContestScore(champion, opponentEntries, pool, unavailableChampions) {
      return Math.max(0, ...opponentEntries.map(entry => {
        const rows = pickCandidatesForEntry(entry, pool, unavailableChampions, []);
        const match = rows.find(row => row.champion === champion);
        return match ? Number(match.pickScore) : 0;
      }));
    }

    function chooseNextPickForTeam(team, blueEntries, redEntries, pool, state, unavailableChampions) {
      const ownEntries = entriesForSide(team, blueEntries, redEntries);
      const enemyEntries = entriesForSide(opponentTeam(team), blueEntries, redEntries);
      const ownPicks = picksForSide(team, state);
      const enemyPicks = picksForSide(opponentTeam(team), state);
      const pickedPlayers = new Set(ownPicks.map(row => row.player));
      const options = ownEntries
        .filter(entry => !pickedPlayers.has(entry.player))
        .map(entry => {
          const candidates = pickCandidatesForEntry(entry, pool, unavailableChampions, enemyPicks);
          const pick = candidates[0];
          if (!pick) return null;
          const ideal = pickCandidatesForEntry(entry, pool, new Set(), [])[0] || null;
          const safe = bestSafePick(candidates);
          const ceiling = highCeilingPick(candidates);
          const trap = trapPick(candidates);
          const contested = opponentContestScore(pick.champion, enemyEntries, pool, unavailableChampions);
          const idealStillAvailable = ideal && championDraftKey(ideal.champion) === championDraftKey(pick.champion);
          const priority =
            Number(pick.pickScore) +
            Math.min(contested / 10, 8) +
            (idealStillAvailable ? 5 : 0) +
            (Number(pick.matchupBonus) > 0 ? 5 : 0);
          return { entry, pick, ideal, safe, ceiling, trap, contested, priority };
        })
        .filter(Boolean)
        .sort((left, right) =>
          Number(right.priority) - Number(left.priority) ||
          Number(right.pick.pickScore) - Number(left.pick.pickScore) ||
          Number(right.pick.games) - Number(left.pick.games)
        );
      return options[0] || null;
    }

    function runTournamentDraft(blueEntries, redEntries, pool) {
      const state = {
        blueBans: [],
        redBans: [],
        bluePicks: [],
        redPicks: [],
        turns: []
      };
      const unavailable = new Set();
      const banOrder = ["blue", "red", "blue", "red", "blue", "red"];
      banOrder.forEach((team, index) => {
        const targetEntries = entriesForSide(opponentTeam(team), blueEntries, redEntries);
        const ownBans = bansForSide(team, state);
        const ideal = denyCandidatesForEntries(targetEntries, pool, new Set(), [])[0] || null;
        const candidate = denyCandidatesForEntries(targetEntries, pool, unavailable, ownBans)[0] || null;
        if (candidate) {
          unavailable.add(championDraftKey(candidate.champion));
          ownBans.push({ ...candidate, draftTurn: index + 1, action: "ban", team });
        }
        state.turns.push({
          number: index + 1,
          phase: "Bans",
          action: "ban",
          team,
          targetEntries,
          candidate,
          ideal
        });
      });

      const pickGroups = [
        { team: "blue", count: 1, label: "B1" },
        { team: "red", count: 2, label: "R1+R2" },
        { team: "blue", count: 2, label: "B2+B3" },
        { team: "red", count: 2, label: "R3+R4" },
        { team: "blue", count: 2, label: "B4+B5" },
        { team: "red", count: 1, label: "R5" }
      ];
      let turnNumber = banOrder.length + 1;
      pickGroups.forEach(group => {
        for (let slot = 0; slot < group.count; slot += 1) {
          const choice = chooseNextPickForTeam(group.team, blueEntries, redEntries, pool, state, unavailable);
          const pick = choice?.pick || null;
          if (pick) {
            unavailable.add(championDraftKey(pick.champion));
            picksForSide(group.team, state).push({
              ...pick,
              draftTurn: turnNumber,
              action: "pick",
              team: group.team
            });
          }
          state.turns.push({
            number: turnNumber,
            phase: group.label,
            action: "pick",
            team: group.team,
            candidate: pick,
            choice,
            ideal: choice?.ideal || null
          });
          turnNumber += 1;
        }
      });
      return state;
    }

    function draftTag(className, text) {
      if (!text) return "";
      return `<span class="draft-tag ${className}">${escapeBanHtml(text)}</span>`;
    }

    function renderDraftTurn(turn) {
      const row = turn.candidate;
      const actionLabel = turn.action === "ban" ? "Ban" : "Pick";
      if (!row) {
        const emptyText = turn.action === "ban"
          ? "No eligible deny ban available."
          : "No eligible pick available for remaining players.";
        return `
          <article class="draft-turn-card" data-side="${turn.team}" data-action="${turn.action}">
            <div class="draft-turn-top"><span>Turn ${turn.number} - ${sideName(turn.team)} ${actionLabel}</span><span>${escapeBanHtml(turn.phase)}</span></div>
            <div class="ban-empty">${emptyText}</div>
          </article>
        `;
      }
      const isPick = turn.action === "pick";
      const roleNote = row.roleMatched ? row.assignedRole : `${row.assignedRole} eligible`;
      const mainLine = isPick
        ? `${row.player} - ${roleNote}${row.fit ? `, ${row.fit}` : ""}${row.metaFallback ? ", role meta fallback" : ""}`
        : `Deny ${row.player} - ${row.assignedRole}`;
      const detail = row.metaFallback
        ? `${row.games} role games, ${formatBanPercent(row.winrate)} role WR, ${Number(row.kda).toFixed(2)} role KDA, no player sample`
        : `${row.games}g, ${formatBanPercent(row.winrate)} WR, ${Number(row.kda).toFixed(2)} KDA, ${Number(row.mvpScore).toFixed(1)} MVP`;
      const scoreValue = Number(isPick ? row.pickScore : row.denyScore || row.draftScore || row.score);
      const ideal = turn.ideal;
      const tags = [];
      if (ideal && championDraftKey(ideal.champion) !== championDraftKey(row.champion)) {
        tags.push(draftTag("draft-tag-counter", `Ideal: ${ideal.champion}`));
      } else if (ideal) {
        tags.push(draftTag("draft-tag-counter", "Ideal available"));
      }
      if (isPick && turn.choice) {
        const safe = turn.choice.safe;
        const ceiling = turn.choice.ceiling;
        const trap = turn.choice.trap;
        if (row.metaFallback) tags.push(draftTag("draft-tag-trap", "No player sample"));
        if (safe) tags.push(draftTag("draft-tag-safe", `Safe: ${safe.champion}`));
        if (ceiling) tags.push(draftTag("draft-tag-ceiling", `Ceiling: ${ceiling.champion}`));
        if (row.matchupLabel) tags.push(draftTag("draft-tag-counter", row.matchupLabel));
        if (trap) tags.push(draftTag("draft-tag-trap", `Trap: ${trap.champion}`));
      } else {
        tags.push(draftTag("draft-tag-trap", `${formatSignedBanPercent(row.lift)} vs baseline`));
      }
      return `
        <article class="draft-turn-card" data-side="${turn.team}" data-action="${turn.action}">
          <div class="draft-turn-top"><span>Turn ${turn.number} - ${sideName(turn.team)} ${actionLabel}</span><span>${escapeBanHtml(turn.phase)}</span></div>
          <div class="draft-turn-main">
            <img src="${escapeBanHtml(row.championIcon)}" alt="${escapeBanHtml(row.champion)}">
            <div class="draft-turn-copy">
              <strong>${escapeBanHtml(row.champion)}</strong>
              <span>${escapeBanHtml(mainLine)}</span>
              <small>${escapeBanHtml(detail)}</small>
            </div>
            <b class="draft-turn-score">${scoreValue.toFixed(1)}</b>
          </div>
          <div class="draft-tag-row">${tags.join("")}</div>
        </article>
      `;
    }

    function renderDraftCoach(simulation, blueEntries, redEntries, pool) {
      if (!draftCoachSummary || !draftCoachTurns) return;
      if (!blueEntries.length && !redEntries.length) {
        draftCoachSummary.textContent = "Enter teams and a champion pool to simulate the tournament draft order.";
        draftCoachTurns.innerHTML = "";
        return;
      }
      const poolText = pool.limited
        ? `${pool.names.length} champion pool`
        : "all champions";
      const pickedCount = simulation.bluePicks.length + simulation.redPicks.length;
      const banCount = simulation.blueBans.length + simulation.redBans.length;
      draftCoachSummary.textContent =
        `Simulating ${poolText}: ${banCount}/6 bans and ${pickedCount}/10 picks. ` +
        "Role-specific comfort is used first, champion matchup bonuses apply after a lane opponent is visible, and class needs will need champion tags later.";
      draftCoachTurns.innerHTML = simulation.turns.map(renderDraftTurn).join("");
    }

    function renderBanResults(team, picks, targetEntries) {
      const list = document.querySelector(`[data-ban-results="${team}"]`);
      const count = document.querySelector(`[data-ban-count="${team}"]`);
      const targets = document.querySelector(`[data-ban-targets="${team}"]`);
      if (!list || !count || !targets) return;

      count.textContent = `${picks.length}/3`;
      targets.textContent = targetEntries.length
        ? `Targets: ${targetEntries.map(entry => `${entry.role} ${entry.player}`).join(", ")}`
        : "Targets: none";

      if (!targetEntries.length) {
        list.innerHTML = '<div class="ban-empty">No opposing players entered.</div>';
        return;
      }
      if (!picks.length) {
        list.innerHTML = '<div class="ban-empty">No eligible champion data for those players.</div>';
        return;
      }

      list.innerHTML = picks.map((row, index) => `
        <article class="ban-pick-row">
          <b>${index + 1}</b>
          <img src="${escapeBanHtml(row.championIcon)}" alt="${escapeBanHtml(row.champion)}">
          <div class="ban-pick-copy">
            <strong>${escapeBanHtml(row.champion)}</strong>
            <span>${escapeBanHtml(row.player)} - ${escapeBanHtml(row.assignedRole)}${row.roleMatched ? "" : " eligible"}</span>
            <small>${row.games}g, ${formatBanPercent(row.winrate)} WR, ${Number(row.kda).toFixed(2)} KDA, ${Number(row.mvpScore).toFixed(1)} MVP, ${escapeBanHtml(row.roles)}</small>
          </div>
          <em title="${formatSignedBanPercent(row.lift)} vs player baseline">${Number(row.score).toFixed(1)}</em>
        </article>
      `).join("");
    }

    function renderPickResults(team, picks, entries) {
      const list = document.querySelector(`[data-pick-results="${team}"]`);
      const count = document.querySelector(`[data-pick-count="${team}"]`);
      const targets = document.querySelector(`[data-pick-targets="${team}"]`);
      if (!list || !count || !targets) return;

      count.textContent = `${picks.length}/5`;
      targets.textContent = entries.length
        ? `Players: ${entries.map(entry => `${entry.role} ${entry.player}`).join(", ")}`
        : "Players: none";

      if (!entries.length) {
        list.innerHTML = '<div class="ban-empty">No players entered.</div>';
        return;
      }
      if (!picks.length) {
        list.innerHTML = '<div class="ban-empty">No eligible champion data for this team.</div>';
        return;
      }

      list.innerHTML = picks.map((row, index) => {
        const roleNote = row.roleMatched ? row.assignedRole : `${row.assignedRole} eligible`;
        const fitNote = row.fit ? `, ${escapeBanHtml(row.fit)}` : "";
        const sampleNote = row.metaFallback
          ? `${row.games} role games, ${formatBanPercent(row.winrate)} role WR, no player sample`
          : `${row.games}g, ${formatBanPercent(row.winrate)} WR, ${Number(row.kda).toFixed(2)} KDA, ${Number(row.mvpScore).toFixed(1)} MVP`;
        return `
          <article class="ban-pick-row">
            <b>${index + 1}</b>
            <img src="${escapeBanHtml(row.championIcon)}" alt="${escapeBanHtml(row.champion)}">
            <div class="ban-pick-copy">
              <strong>${escapeBanHtml(row.champion)}</strong>
              <span>${escapeBanHtml(row.player)} - ${escapeBanHtml(roleNote)}${fitNote}${row.metaFallback ? ", role meta" : ""}</span>
              <small>${sampleNote}</small>
            </div>
            <em>${Number(row.pickScore || row.score).toFixed(1)}</em>
          </article>
        `;
      }).join("");
    }

    function parseDraftImport(text) {
      const parsed = { blue: [], red: [] };
      let activeTeam = "";
      String(text || "").split(/\\r?\\n/).forEach(line => {
        const trimmed = line.trim();
        if (/^Blue Team$/i.test(trimmed)) {
          activeTeam = "blue";
          return;
        }
        if (/^Red Team$/i.test(trimmed)) {
          activeTeam = "red";
          return;
        }
        const match = trimmed.match(/^(TOP|JUNGLE|MID|BOT|SUPP)\\s+(.+?)\\s+(Primary|Secondary|Off-role)\\s*$/i);
        if (!activeTeam || !match) return;
        parsed[activeTeam].push({
          role: match[1].toUpperCase(),
          player: match[2].trim(),
          fit: match[3]
        });
      });
      return parsed;
    }

    function championPoolFromDraftImport(text) {
      const match = String(text || "").match(/(?:^|\\n)Champions:\\s*([\\s\\S]*)$/i);
      return match ? match[1].trim() : "";
    }

    function applyDraftImport() {
      if (!draftImportText) return;
      const parsed = parseDraftImport(draftImportText.value);
      let applied = 0;
      ["blue", "red"].forEach(team => {
        parsed[team].forEach(entry => {
          const input = draftInputs.find(item => item.dataset.draftTeam === team && item.dataset.draftRole === entry.role);
          if (!input) return;
          const canonical = canonicalPlayerName(entry.player) || entry.player;
          input.value = canonical;
          setDraftFit(team, entry.role, entry.fit);
          applied += 1;
        });
      });
      if (draftImportStatus) {
        draftImportStatus.textContent = `${applied}/10 draft slots applied`;
      }
      const importedChampionPool = championPoolFromDraftImport(draftImportText.value);
      if (championPoolText && importedChampionPool) {
        championPoolText.value = importedChampionPool;
      }
      updateBanPlanner();
    }

    function updateBanPlanner() {
      const pool = championPoolState();
      updateChampionPoolDisplay(pool);
      const blueEntries = selectedDraftEntries("blue");
      const redEntries = selectedDraftEntries("red");
      const simulation = runTournamentDraft(blueEntries, redEntries, pool);
      renderDraftCoach(simulation, blueEntries, redEntries, pool);
      renderBanResults("blue", simulation.blueBans, redEntries);
      renderPickResults("blue", simulation.bluePicks, blueEntries);
      renderBanResults("red", simulation.redBans, blueEntries);
      renderPickResults("red", simulation.redPicks, redEntries);
    }

    if (draftInputs.length) {
      draftInputs.forEach(input => {
        input.addEventListener("input", () => {
          setDraftFit(input.dataset.draftTeam, input.dataset.draftRole, "");
          updateBanPlanner();
        });
        input.addEventListener("change", () => {
          const canonical = canonicalPlayerName(input.value);
          if (canonical) input.value = canonical;
          updateBanPlanner();
        });
      });
      if (draftImportButton) {
        draftImportButton.addEventListener("click", applyDraftImport);
      }
      if (championPoolText) {
        championPoolText.addEventListener("input", updateBanPlanner);
      }
      if (championPoolClear) {
        championPoolClear.addEventListener("click", () => {
          if (championPoolText) championPoolText.value = "";
          updateBanPlanner();
        });
      }
      const clearButton = document.querySelector("[data-draft-clear]");
      if (clearButton) {
        clearButton.addEventListener("click", () => {
          draftInputs.forEach(input => {
            input.value = "";
            setDraftFit(input.dataset.draftTeam, input.dataset.draftRole, "");
          });
          if (draftImportStatus) {
            draftImportStatus.textContent = "No draft imported";
          }
          updateBanPlanner();
        });
      }
      updateBanPlanner();
    }
    """
    return (
        script.replace("__BAN_TARGET_DATA__", target_json)
        .replace("__PICK_TARGET_DATA__", pick_json)
        .replace("__CHAMPION_ROSTER_DATA__", champion_json)
        .replace("__CHAMPION_MATCHUP_DATA__", matchup_json)
        .replace("__BAN_PLAYER_NAMES__", player_json)
    )


def render_refresh_control(generated_at: str) -> str:
    return f"""
    <div class="header-actions" data-generated-at="{html_attr(generated_at)}">
      <button class="refresh-data-button" type="button" data-refresh-data>Refresh Data</button>
      <small class="refresh-data-note">Last refresh: {escape(generated_at)}</small>
      <small class="refresh-data-status" data-refresh-data-status></small>
    </div>
    """


def render_hidden_head_to_head_link(head_to_head_page_name: str) -> str:
    return f'<a class="hidden-page-link" href="{html_attr(head_to_head_page_name)}#head-to-head" aria-label="Head to Head"></a>'


def render_refresh_script() -> str:
    return """
    document.querySelectorAll("[data-refresh-data]").forEach(button => {
      const status = button.parentElement?.querySelector("[data-refresh-data-status]");
      const setStatus = (state, text) => {
        if (!status) return;
        status.dataset.state = state || "";
        status.textContent = text;
      };
      button.addEventListener("click", async () => {
        button.disabled = true;
        setStatus("", "Queueing refresh...");
        try {
          const response = await fetch("/.netlify/functions/refresh-data", { method: "POST" });
          const data = await response.json().catch(() => ({}));
          if (!response.ok) {
            throw new Error(data.error || `Refresh failed with ${response.status}`);
          }
          setStatus("ok", "Refresh queued. Reload the page after a couple of minutes");
        } catch (error) {
          setStatus("error", error?.message || "Refresh unavailable. Check the Netlify Function logs.");
        } finally {
          button.disabled = false;
        }
      });
    });
    """


def player_showcase_slug(name: str) -> str:
    slug = "".join(character.lower() if character.isalnum() else "-" for character in name)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-") or "player"


def player_streaks(records: Sequence[Appearance]) -> dict[str, int | str]:
    longest_win = 0
    longest_loss = 0
    current_result = ""
    current_length = 0
    for row in records:
        if row.result == current_result:
            current_length += 1
        else:
            current_result = row.result
            current_length = 1
        if row.win:
            longest_win = max(longest_win, current_length)
        else:
            longest_loss = max(longest_loss, current_length)

    active_result = ""
    active_length = 0
    for row in reversed(records):
        if not active_result:
            active_result = row.result
        if row.result != active_result:
            break
        active_length += 1

    return {
        "longest_win": longest_win,
        "longest_loss": longest_loss,
        "active_result": active_result,
        "active_length": active_length,
    }


def showcase_match_label(row: Appearance) -> str:
    return f"Match {row.match_id} - {row.date_label}"


def showcase_kda(row: Appearance) -> str:
    return f"{row.kills}/{row.deaths}/{row.assists}"


def render_showcase_css() -> str:
    return """
    body.showcase-body {
      background: #060a0f;
    }
    body.showcase-body main {
      max-width: none;
      padding: 0;
    }
    .showcase-toolbar {
      position: sticky;
      top: 0;
      z-index: 8;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      padding: 14px clamp(18px, 4vw, 48px);
      background: rgba(8, 13, 19, 0.94);
      border-bottom: 1px solid var(--line);
    }
    .showcase-toolbar label {
      display: grid;
      gap: 5px;
      color: var(--muted);
      font-size: 0.76rem;
      font-weight: 900;
      text-transform: uppercase;
      min-width: min(340px, 100%);
    }
    .showcase-toolbar select {
      min-height: 40px;
      border: 1px solid #34465d;
      border-radius: 6px;
      background: #101925;
      color: var(--ink);
      padding: 8px 34px 8px 10px;
      font-weight: 900;
    }
    .showcase-count {
      color: var(--muted);
      font-weight: 900;
      white-space: nowrap;
    }
    .player-showcase {
      --accent: var(--gold);
      --accent-2: var(--blue);
      display: none;
      min-height: calc(100vh - 150px);
      background:
        linear-gradient(180deg, rgba(255, 255, 255, 0.03), rgba(255, 255, 255, 0) 34%),
        linear-gradient(135deg, rgba(98, 168, 255, 0.13), rgba(79, 196, 139, 0.08) 48%, rgba(240, 201, 106, 0.09));
    }
    .player-showcase.active {
      display: block;
    }
    .showcase-theme-1 {
      --accent: #4fc48b;
      --accent-2: #f0c96a;
    }
    .showcase-theme-2 {
      --accent: #62a8ff;
      --accent-2: #ff6f81;
    }
    .showcase-theme-3 {
      --accent: #ff6f81;
      --accent-2: #b596ff;
    }
    .showcase-theme-4 {
      --accent: #b596ff;
      --accent-2: #4fc48b;
    }
    .showcase-hero {
      position: relative;
      min-height: min(760px, calc(100vh - 150px));
      display: grid;
      grid-template-columns: minmax(0, 1.02fr) minmax(280px, 0.62fr) minmax(360px, 0.94fr);
      gap: clamp(22px, 4vw, 54px);
      align-items: center;
      padding: clamp(28px, 5vw, 70px);
      overflow: hidden;
      border-bottom: 1px solid rgba(232, 238, 246, 0.12);
    }
    .showcase-watermark {
      position: absolute;
      right: clamp(18px, 5vw, 78px);
      top: clamp(20px, 5vw, 70px);
      width: min(38vw, 470px);
      opacity: 0.1;
      image-rendering: auto;
      pointer-events: none;
      filter: saturate(1.25);
    }
    .showcase-kicker {
      color: var(--accent);
      font-size: 0.8rem;
      font-weight: 950;
      text-transform: uppercase;
    }
    .showcase-title h2 {
      margin: 0;
      color: #f7fbff;
      font-size: clamp(3.2rem, 10vw, 8.6rem);
      line-height: 0.88;
    }
    .showcase-summary {
      max-width: 820px;
      margin: 18px 0 0;
      color: #c7d6e7;
      font-size: clamp(1.02rem, 2vw, 1.35rem);
      line-height: 1.45;
    }
    .showcase-fingerprint {
      position: relative;
      z-index: 1;
      border: 1px solid rgba(232, 238, 246, 0.14);
      border-radius: 8px;
      background: rgba(10, 16, 24, 0.70);
      box-shadow: 0 16px 36px rgba(0, 0, 0, 0.24);
      padding: 16px;
    }
    .showcase-fingerprint-heading {
      display: flex;
      align-items: start;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 6px;
    }
    .showcase-fingerprint-heading span {
      color: var(--muted);
      display: block;
      font-size: 0.74rem;
      font-weight: 950;
      text-transform: uppercase;
    }
    .showcase-fingerprint-heading strong {
      color: var(--accent);
      display: block;
      font-size: 2rem;
      line-height: 1;
      margin-top: 3px;
    }
    .showcase-fingerprint-heading small {
      color: #aebdcc;
      font-weight: 850;
      line-height: 1.35;
      max-width: 150px;
      text-align: right;
    }
    .showcase-fingerprint .fingerprint-radar {
      margin: 0 auto;
      max-width: 320px;
    }
    .showcase-fingerprint .radar-grid polygon {
      fill: none;
      stroke: rgba(174, 189, 204, 0.28);
      stroke-width: 1;
    }
    .showcase-fingerprint .radar-axis line {
      stroke: rgba(174, 189, 204, 0.22);
      stroke-width: 1;
    }
    .showcase-fingerprint .radar-fill {
      fill: color-mix(in srgb, var(--accent) 28%, transparent);
      stroke: var(--accent);
      stroke-width: 3;
    }
    .showcase-fingerprint .radar-labels text {
      fill: #c7d6e7;
      font-size: 0.62rem;
      font-weight: 950;
      letter-spacing: 0;
    }
    .showcase-fingerprint-metrics {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
      margin-top: 4px;
    }
    .showcase-fingerprint-metric {
      border-top: 1px solid rgba(232, 238, 246, 0.1);
      padding-top: 7px;
    }
    .showcase-fingerprint-metric span {
      color: var(--muted);
      display: block;
      font-size: 0.67rem;
      font-weight: 900;
      text-transform: uppercase;
    }
    .showcase-fingerprint-metric b {
      color: #f7fbff;
      display: block;
      font-size: 0.95rem;
      margin-top: 2px;
    }
    .showcase-hero-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
      position: relative;
      z-index: 1;
    }
    .showcase-stat,
    .showcase-feature,
    .showcase-award,
    .showcase-moment,
    .showcase-champ,
    .showcase-insight {
      border: 1px solid rgba(232, 238, 246, 0.14);
      border-radius: 8px;
      background: rgba(10, 16, 24, 0.78);
      box-shadow: 0 16px 36px rgba(0, 0, 0, 0.24);
      min-width: 0;
    }
    .showcase-stat {
      min-height: 122px;
      padding: 14px;
      display: grid;
      align-content: space-between;
      gap: 12px;
    }
    .showcase-stat span,
    .showcase-feature span,
    .showcase-award span,
    .showcase-moment span,
    .showcase-champ span,
    .showcase-insight span {
      color: var(--muted);
      font-size: 0.74rem;
      font-weight: 900;
      text-transform: uppercase;
    }
    .showcase-stat strong {
      color: #ffffff;
      font-size: clamp(1.55rem, 3vw, 2.55rem);
      line-height: 1;
    }
    .showcase-stat small,
    .showcase-feature small,
    .showcase-award small,
    .showcase-moment small,
    .showcase-champ small,
    .showcase-insight small {
      color: #aebdcc;
      font-weight: 800;
      line-height: 1.35;
    }
    .showcase-stat-ring {
      width: 62px;
      height: 62px;
      border-radius: 50%;
      background: conic-gradient(var(--accent) var(--value), #263241 0);
      display: grid;
      place-items: center;
    }
    .showcase-stat-ring::after {
      content: "";
      width: 42px;
      height: 42px;
      border-radius: 50%;
      background: #101925;
    }
    .showcase-stat-row {
      display: flex;
      justify-content: space-between;
      align-items: end;
      gap: 12px;
    }
    .showcase-feature {
      display: grid;
      grid-template-columns: 84px minmax(0, 1fr);
      gap: 14px;
      align-items: center;
      padding: 14px;
      grid-column: 1 / -1;
      border-color: color-mix(in srgb, var(--accent) 44%, rgba(232, 238, 246, 0.1));
    }
    .showcase-feature img {
      width: 82px;
      height: 82px;
      border-radius: 8px;
      border: 1px solid rgba(240, 201, 106, 0.32);
      object-fit: cover;
    }
    .showcase-feature strong {
      display: block;
      margin: 4px 0;
      font-size: 1.4rem;
      line-height: 1.1;
      overflow-wrap: anywhere;
    }
    .showcase-band {
      padding: clamp(28px, 5vw, 58px) clamp(18px, 4vw, 48px);
      border-bottom: 1px solid rgba(232, 238, 246, 0.1);
    }
    .showcase-band-inner {
      max-width: 1480px;
      margin: 0 auto;
    }
    .showcase-band-title {
      display: flex;
      justify-content: space-between;
      align-items: end;
      gap: 18px;
      margin-bottom: 16px;
    }
    .showcase-band-title h3 {
      font-size: clamp(1.45rem, 3vw, 2.5rem);
      line-height: 1.05;
    }
    .showcase-band-title small {
      color: var(--muted);
      font-weight: 900;
    }
    .showcase-awards,
    .showcase-insights {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 14px;
    }
    .showcase-award,
    .showcase-insight {
      padding: 16px;
      display: grid;
      gap: 8px;
      align-content: start;
    }
    .showcase-award b,
    .showcase-insight b {
      color: var(--accent);
      font-size: 1.42rem;
      line-height: 1.08;
      overflow-wrap: anywhere;
    }
    .showcase-grid-two {
      display: grid;
      grid-template-columns: minmax(0, 1.1fr) minmax(340px, 0.9fr);
      gap: 18px;
      align-items: start;
    }
    .showcase-champ-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
    }
    .showcase-champ {
      display: grid;
      grid-template-columns: 58px minmax(0, 1fr);
      gap: 12px;
      padding: 12px;
      align-items: center;
    }
    .showcase-champ img {
      width: 56px;
      height: 56px;
      border-radius: 8px;
      border: 1px solid rgba(232, 238, 246, 0.16);
      object-fit: cover;
    }
    .showcase-champ strong {
      display: block;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .showcase-mini-bar {
      height: 6px;
      margin-top: 7px;
      border-radius: 999px;
      background: #263241;
      overflow: hidden;
    }
    .showcase-mini-bar i {
      display: block;
      height: 100%;
      width: var(--value);
      background: linear-gradient(90deg, var(--accent), var(--accent-2));
    }
    .showcase-role-panel {
      display: grid;
      gap: 12px;
    }
    .showcase-role-row {
      display: grid;
      grid-template-columns: 78px minmax(0, 1fr) 54px;
      gap: 10px;
      align-items: center;
      color: #d7e3ef;
      font-weight: 900;
    }
    .showcase-role-track {
      height: 12px;
      border-radius: 999px;
      background: #1b2532;
      overflow: hidden;
    }
    .showcase-role-track i {
      display: block;
      width: var(--value);
      height: 100%;
      background: var(--accent);
    }
    .showcase-moments {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 14px;
    }
    .showcase-moment {
      padding: 14px;
      min-height: 160px;
      display: grid;
      align-content: space-between;
      gap: 10px;
    }
    .showcase-moment b {
      color: #ffffff;
      font-size: 1.18rem;
      line-height: 1.1;
      overflow-wrap: anywhere;
    }
    .showcase-form-panel {
      background: rgba(10, 16, 24, 0.78);
      border: 1px solid rgba(232, 238, 246, 0.13);
      border-top: 4px solid var(--blue);
      border-radius: 8px;
      padding: 16px;
    }
    .showcase-form-panel.status-heating-up,
    .showcase-form-panel.status-hot-form {
      border-top-color: var(--green);
    }
    .showcase-form-panel.status-cooling-down,
    .showcase-form-panel.status-cold-spell {
      border-top-color: var(--red);
    }
    .showcase-form-panel.status-small-sample {
      border-top-color: #8a94a6;
    }
    .showcase-form-heading {
      display: grid;
      gap: 5px;
      margin-bottom: 14px;
    }
    .showcase-form-heading span,
    .showcase-form-grid span {
      color: var(--muted);
      font-size: 0.76rem;
      font-weight: 950;
      text-transform: uppercase;
    }
    .showcase-form-heading strong {
      font-size: 1.45rem;
      line-height: 1;
    }
    .showcase-form-heading small {
      color: #aebdcc;
      font-weight: 850;
    }
    .showcase-form-grid {
      display: grid;
      gap: 10px;
      grid-template-columns: repeat(6, minmax(0, 1fr));
    }
    .showcase-form-grid div {
      background: rgba(255, 255, 255, 0.045);
      border: 1px solid rgba(232, 238, 246, 0.08);
      border-radius: 8px;
      padding: 10px;
    }
    .showcase-form-grid b {
      display: block;
      font-size: 1rem;
      margin-top: 4px;
    }
    .showcase-form-strip {
      display: flex;
      gap: 8px;
      margin-top: 14px;
      overflow-x: auto;
      padding-bottom: 3px;
    }
    .showcase-form-pick {
      border: 2px solid rgba(232, 238, 246, 0.14);
      border-radius: 8px;
      display: block;
      flex: 0 0 auto;
      height: 46px;
      overflow: hidden;
      position: relative;
      width: 46px;
    }
    .showcase-form-pick.win {
      border-color: var(--green);
    }
    .showcase-form-pick.loss {
      border-color: var(--red);
    }
    .showcase-form-pick img {
      display: block;
      height: 100%;
      object-fit: cover;
      width: 100%;
    }
    .showcase-form-pick b {
      background: rgba(6, 10, 16, 0.82);
      bottom: 0;
      color: #fff;
      font-size: 0.68rem;
      font-weight: 950;
      line-height: 1;
      padding: 3px 4px;
      position: absolute;
      right: 0;
    }
    .showcase-timeline {
      display: grid;
      grid-template-columns: repeat(12, minmax(112px, 1fr));
      gap: 10px;
      overflow-x: auto;
      padding-bottom: 6px;
    }
    .showcase-timeline-item {
      min-height: 142px;
      padding: 12px;
      border-radius: 8px;
      background: rgba(10, 16, 24, 0.78);
      border: 1px solid rgba(232, 238, 246, 0.13);
      display: grid;
      align-content: space-between;
      gap: 8px;
    }
    .showcase-timeline-item.win {
      border-top: 3px solid var(--green);
    }
    .showcase-timeline-item.loss {
      border-top: 3px solid var(--red);
    }
    .showcase-timeline-item b {
      font-size: 0.92rem;
      overflow-wrap: anywhere;
    }
    .showcase-timeline-item span {
      color: var(--muted);
      font-size: 0.74rem;
      font-weight: 900;
      text-transform: uppercase;
    }
    .showcase-timeline-item small {
      color: #aebdcc;
      font-weight: 800;
    }
    @media (max-width: 1120px) {
      .showcase-hero,
      .showcase-grid-two {
        grid-template-columns: 1fr;
      }
      .showcase-hero {
        align-items: start;
      }
      .showcase-awards,
      .showcase-insights,
      .showcase-champ-grid,
      .showcase-moments,
      .showcase-form-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }
    }
    @media (max-width: 720px) {
      .showcase-toolbar {
        align-items: stretch;
        flex-direction: column;
      }
      .showcase-count {
        white-space: normal;
      }
      .showcase-hero {
        min-height: 0;
        padding: 28px 18px;
      }
      .showcase-watermark {
        width: 260px;
        right: -36px;
        top: 24px;
      }
      .showcase-hero-grid,
      .showcase-awards,
      .showcase-insights,
      .showcase-champ-grid,
      .showcase-moments,
      .showcase-form-grid {
        grid-template-columns: 1fr;
      }
      .showcase-feature {
        grid-template-columns: 66px minmax(0, 1fr);
      }
      .showcase-feature img {
        width: 64px;
        height: 64px;
      }
    }
    """


def render_showcase_stat(label: str, value: str, detail: str, ring_value: float | None = None) -> str:
    ring = ""
    if ring_value is not None:
        ring = (
            f'<div class="showcase-stat-ring" style="--value: '
            f'{clamp(ring_value) * 100:.1f}%"></div>'
        )
    return f"""
    <article class="showcase-stat">
      <span>{escape(label)}</span>
      <div class="showcase-stat-row">
        <strong>{escape(value)}</strong>
        {ring}
      </div>
      <small>{escape(detail)}</small>
    </article>
    """


def render_showcase_award(title: str, value: str, detail: str) -> str:
    return f"""
    <article class="showcase-award">
      <span>{escape(title)}</span>
      <b>{escape(value)}</b>
      <small>{escape(detail)}</small>
    </article>
    """


def render_showcase_insight(title: str, value: str, detail: str) -> str:
    return f"""
    <article class="showcase-insight">
      <span>{escape(title)}</span>
      <b>{escape(value)}</b>
      <small>{escape(detail)}</small>
    </article>
    """


def render_showcase_champion(row: dict[str, object]) -> str:
    champion = str(row.get("champion", "-"))
    winrate = float(row.get("winrate", 0))
    games = int(row.get("games", 0))
    wins = int(row.get("wins", 0))
    return f"""
    <article class="showcase-champ">
      <img src="{html_attr(champion_icon_url(champion))}" alt="{html_attr(champion)}">
      <div>
        <strong>{escape(champion)}</strong>
        <small>{games}g, {wins}-{games - wins}, {pct(winrate)} WR</small>
        <div class="showcase-mini-bar" style="--value: {clamp(winrate) * 100:.1f}%"><i></i></div>
      </div>
    </article>
    """


def render_showcase_moment(title: str, value: str, detail: str) -> str:
    return f"""
    <article class="showcase-moment">
      <span>{escape(title)}</span>
      <b>{escape(value)}</b>
      <small>{escape(detail)}</small>
    </article>
    """


def render_showcase_role_bars(
    role_rows: Sequence[dict[str, object]], total_games: int
) -> str:
    rows_by_role = {str(row.get("role", "")): row for row in role_rows}
    rendered = []
    for role in ROLE_ORDER:
        row = rows_by_role.get(role, {})
        games = int(row.get("games", 0))
        share = safe_div(games, total_games)
        rendered.append(
            f"""
            <div class="showcase-role-row">
              <span>{escape(role)}</span>
              <div class="showcase-role-track" style="--value: {share * 100:.1f}%"><i></i></div>
              <small>{games}g</small>
            </div>
            """
        )
    return f'<div class="showcase-role-panel">{"".join(rendered)}</div>'


def render_showcase_timeline(records: Sequence[Appearance], limit: int = 12) -> str:
    recent = list(records[-limit:])
    if not recent:
        return '<div class="empty-state">No match history yet.</div>'
    rendered = []
    for row in recent:
        result_class = "win" if row.win else "loss"
        rendered.append(
            f"""
            <article class="showcase-timeline-item {result_class}">
              <span>{escape(row.result)} - {escape(row.role)}</span>
              <b>{escape(row.champion)}</b>
              <small>{escape(showcase_kda(row))} KDA line</small>
              <small>{escape(showcase_match_label(row))}</small>
            </article>
            """
        )
    return f'<div class="showcase-timeline">{"".join(rendered)}</div>'


def render_showcase_recent_form(row: dict[str, object]) -> str:
    if not row:
        return """
        <article class="showcase-form-panel">
          <div class="showcase-form-heading">
            <span>Recent Status</span>
            <strong>No recent form data</strong>
            <small>Needs match appearances in the current data.</small>
          </div>
        </article>
        """
    status = str(row.get("status", "Stable"))
    status_class = f"status-{status.lower().replace(' ', '-')}"
    movement = float(row.get("mvp_movement", 0))
    timeline_items = []
    for item in list(row.get("timeline", []))[-10:]:
        result = str(item.get("result", "Loss"))
        result_class = "win" if result == "Win" else "loss"
        champion = str(item.get("champion", "-"))
        title = (
            f"Match {item.get('match_id', '-')} - {champion} "
            f"{item.get('role', '-')} - {item.get('kda', '-')}"
        )
        timeline_items.append(
            f"""
            <span class="showcase-form-pick {result_class}" title="{html_attr(title)}">
              <img src="{html_attr(champion_icon_url(champion))}" alt="{html_attr(champion)}">
              <b>{'W' if result == 'Win' else 'L'}</b>
            </span>
            """
        )
    return f"""
    <article class="showcase-form-panel {html_attr(status_class)}">
      <div class="showcase-form-heading">
        <span>Recent Status</span>
        <strong>{escape(status)}</strong>
        <small>{escape(str(row.get('streak_label', 'No streak')))}</small>
      </div>
      <div class="showcase-form-grid">
        <div><span>Recent Score</span><b>{score(float(row.get('recent_score', 0)))}</b></div>
        <div><span>Last {integer(row.get('recent_games', 0))}</span><b>{escape(str(row.get('recent_record', '-')))}</b></div>
        <div><span>Recent WR</span><b>{pct(float(row.get('recent_winrate', 0)))}</b></div>
        <div><span>KDA Trend</span><b>{two_decimal(float(row.get('recent_kda', 0)))} vs {two_decimal(float(row.get('overall_kda', 0)))}</b></div>
        <div><span>Recent KP</span><b>{pct(float(row.get('recent_kp', 0)))}</b></div>
        <div><span>MVP Move</span><b>{signed_integer(round(movement))}</b></div>
      </div>
      <div class="showcase-form-strip">{"".join(timeline_items)}</div>
    </article>
    """


def render_player_showcase_page(
    *,
    shared_style: str,
    appearances: Sequence[Appearance],
    player_rows: Sequence[dict[str, object]],
    player_role_rows: Sequence[dict[str, object]],
    player_champion_rows: Sequence[dict[str, object]],
    target_ban_rows: Sequence[dict[str, object]],
    practice_pick_rows: Sequence[dict[str, object]],
    mvp_rows: Sequence[dict[str, object]],
    role_score_rows: Sequence[dict[str, object]],
    fingerprint_rows: Sequence[dict[str, object]],
    form_rows: Sequence[dict[str, object]],
    generated_at: str,
    main_page_name: str,
    teams_page_name: str,
    draft_coach_page_name: str,
    head_to_head_page_name: str,
    experimental_page_name: str,
) -> str:
    showcase_player_rows = without_spotlight_excluded_players(player_rows)
    showcase_player_names = {str(row.get("name", "")) for row in showcase_player_rows}
    player_by_name = {str(row.get("name", "")): row for row in showcase_player_rows}
    mvp_by_name = {
        str(row.get("name", "")): row
        for row in mvp_rows
        if str(row.get("name", "")) in showcase_player_names
    }
    fingerprint_by_name = {
        str(row.get("name", "")): row
        for row in fingerprint_rows
        if str(row.get("name", "")) in showcase_player_names
    }
    form_by_name = {
        str(row.get("name", "")): row
        for row in form_rows
        if str(row.get("name", "")) in showcase_player_names
    }
    records_by_name: dict[str, list[Appearance]] = defaultdict(list)
    for appearance in appearances:
        if appearance.name in showcase_player_names:
            records_by_name[appearance.name].append(appearance)
    for records in records_by_name.values():
        records.sort(key=lambda row: (row.timestamp, row.match_id))

    ordered_names = [
        str(row.get("name", ""))
        for row in mvp_rows
        if str(row.get("name", "")) in showcase_player_names
    ]
    for name in sorted(player_by_name):
        if name not in ordered_names:
            ordered_names.append(name)

    games_rank = {
        str(row.get("name", "")): index
        for index, row in enumerate(
            sorted(showcase_player_rows, key=lambda row: (-int(row.get("games", 0)), str(row.get("name", "")))),
            start=1,
        )
    }
    unique_champ_rank = {
        str(row.get("name", "")): index
        for index, row in enumerate(
            sorted(
                showcase_player_rows,
                key=lambda row: (-int(row.get("unique_champions", 0)), -int(row.get("games", 0)), str(row.get("name", ""))),
            ),
            start=1,
        )
    }
    pool_rate_rank = {
        str(row.get("name", "")): index
        for index, row in enumerate(
            sorted(
                [row for row in showcase_player_rows if int(row.get("games", 0)) >= MIN_PLAYER_GAMES],
                key=lambda row: (
                    -float(row.get("champion_pool_rate", 0)),
                    -int(row.get("unique_champions", 0)),
                    str(row.get("name", "")),
                ),
            ),
            start=1,
        )
    }
    field_avg_deaths = safe_div(
        sum(float(row.get("avg_deaths", 0)) for row in showcase_player_rows),
        len(showcase_player_rows),
    )

    options = []
    sections = []
    for index, name in enumerate(ordered_names):
        player = player_by_name.get(name)
        records = records_by_name.get(name, [])
        if not player or not records:
            continue
        slug = player_showcase_slug(name)
        options.append(
            f'<option value="{html_attr(slug)}">{escape(name)}</option>'
        )
        player_games = int(player.get("games", 0))
        wins = int(player.get("wins", 0))
        winrate = float(player.get("winrate", 0))
        pool_rate = float(player.get("champion_pool_rate", 0))
        pool_rank_detail = (
            f"#{pool_rate_rank.get(name, 0)} by rate"
            if name in pool_rate_rank
            else f"below {MIN_PLAYER_GAMES}-game rate ranking"
        )
        mvp = mvp_by_name.get(name, {})
        mvp_eligible = bool(mvp)
        mvp_score = float(mvp.get("mvp_score", 0))
        mvp_rank = int(mvp.get("mvp_rank", 0))
        mvp_rank_label = f"#{mvp_rank} MVP Rank" if mvp_eligible else "MVP Rank: minimum 10 games"
        mvp_stat_detail = (
            f"Rank #{mvp_rank} on the 10+ game MVP board"
            if mvp_eligible
            else f"Needs {max(0, MIN_PLAYER_GAMES - player_games)} more games for MVP board"
        )
        role_rows = sorted(
            [row for row in player_role_rows if str(row.get("name", "")) == name],
            key=lambda row: role_sort(str(row.get("role", ""))),
        )
        champion_rows = sorted(
            [row for row in player_champion_rows if str(row.get("name", "")) == name],
            key=lambda row: (-int(row.get("games", 0)), -float(row.get("winrate", 0)), str(row.get("champion", ""))),
        )
        best_role = find_first(
            sorted(
                [row for row in role_score_rows if str(row.get("name", "")) == name],
                key=lambda row: (-float(row.get("role_score", 0)), -int(row.get("games", 0))),
            )
        ) or find_first(
            sorted(role_rows, key=lambda row: (-float(row.get("winrate", 0)), -int(row.get("games", 0))))
        )
        signature = find_first(champion_rows)
        signature_champion = str(signature.get("champion", "Unknown"))
        signature_games = int(signature.get("games", 0))
        signature_winrate = float(signature.get("winrate", 0))
        power_pick = find_first(
            sorted(
                [
                    row
                    for row in target_ban_rows
                    if str(row.get("name", "")) == name and int(row.get("games", 0)) >= 2
                ],
                key=lambda row: (-float(row.get("ban_score", 0)), -int(row.get("games", 0))),
            )
        )
        practice_pick = find_first(
            sorted(
                [row for row in practice_pick_rows if str(row.get("name", "")) == name],
                key=lambda row: (-float(row.get("practice_score", 0)), -int(row.get("games", 0))),
            )
        )
        zero_win_pick = find_first(
            sorted(
                [
                    row
                    for row in champion_rows
                    if int(row.get("games", 0)) >= 1
                    and int(row.get("wins", 0)) == 0
                    and float(row.get("winrate", 0)) == 0
                ],
                key=lambda row: (-int(row.get("games", 0)), str(row.get("champion", ""))),
            )
        )
        best_match = max(records, key=lambda row: (row.takedowns, row.kills, row.win, -row.deaths))
        kill_record = max(records, key=lambda row: (row.kills, row.assists, -row.deaths))
        assist_record = max(records, key=lambda row: (row.assists, row.kills, -row.deaths))
        hardest_game = max(records, key=lambda row: (row.deaths, not row.win, row.takedowns))
        streaks = player_streaks(records)
        recent = records[-8:]
        recent_wins = sum(row.win for row in recent)
        recent_winrate = safe_div(recent_wins, len(recent))
        halfway = max(1, len(records) // 2)
        early = records[:halfway]
        late = records[halfway:] or records[-halfway:]
        early_winrate = safe_div(sum(row.win for row in early), len(early))
        late_winrate = safe_div(sum(row.win for row in late), len(late))
        trend_delta = late_winrate - early_winrate
        if trend_delta >= 0.12:
            arc_value = "Late surge"
            arc_detail = f"Second-half winrate is {signed_pct(trend_delta)} above the opening half."
        elif trend_delta <= -0.12:
            arc_value = "Hot start"
            arc_detail = f"Opening-half winrate is {signed_pct(-trend_delta)} above the second half."
        else:
            arc_value = "Steady line"
            arc_detail = f"Only {signed_pct(trend_delta)} separates first half from second half."

        main_role = str(best_role.get("role", "-"))
        main_role_games = int(best_role.get("games", 0))
        main_role_share = safe_div(main_role_games, player_games)
        top_champion_rows = champion_rows[:6]
        if not top_champion_rows:
            top_champion_rows = [{"champion": "Unknown", "games": 0, "wins": 0, "winrate": 0}]

        summary = (
            f"{name} has logged {player_games} games at {pct(winrate)} winrate, "
            f"{'ranking #' + str(mvp_rank) + ' on MVP score' if mvp_eligible else 'below the MVP-board game minimum'}. "
            f"The identity so far is {main_role} first, "
            f"with {signature_champion} as the most repeated pick."
        )
        if practice_pick:
            practice_champion = str(practice_pick.get("champion", "-"))
            practice_detail = str(
                practice_pick.get(
                    "practice_detail",
                    (
                        f"{pct(float(practice_pick.get('winrate', 0)))} WR over "
                        f"{int(practice_pick.get('games', 0))} games"
                    ),
                )
            )
        elif zero_win_pick:
            zero_games = int(zero_win_pick.get("games", 0))
            zero_wins = int(zero_win_pick.get("wins", 0))
            zero_losses = zero_games - zero_wins
            practice_champion = str(zero_win_pick.get("champion", "-"))
            practice_detail = (
                f"{zero_wins}-{zero_losses}, {zero_games} "
                f"{'game' if zero_games == 1 else 'games'}, 0.0% WR. "
                "Small sample, but worth another lab run."
            )
        else:
            practice_champion = "No clear project"
            practice_detail = (
                f"No {PRACTICE_PICK_MIN_GAMES}+ game pick is below "
                f"{pct(PRACTICE_PICK_MAX_WINRATE)} WR and at least "
                f"{pct(PRACTICE_PICK_BASELINE_GAP)} below player baseline, "
                "and no 0% one-game pick exists yet."
            )

        power_value = str(power_pick.get("champion", signature_champion))
        power_detail = (
            f"{int(power_pick.get('games', signature_games))} games, "
            f"{pct(float(power_pick.get('winrate', signature_winrate)))} WR"
            if power_pick
            else f"{signature_games} games, {pct(signature_winrate)} WR"
        )
        role_detail = (
            f"{main_role_games} games, {pct(float(best_role.get('winrate', 0)))} WR"
            if best_role
            else "No role sample yet"
        )

        awards_html = "".join(
            [
                render_showcase_award(
                    "Signature Pick",
                    signature_champion,
                    f"{signature_games} games, {pct(signature_winrate)} WR",
                ),
                render_showcase_award("Power Pick", power_value, power_detail),
                render_showcase_award("Best Role", main_role, role_detail),
                render_showcase_award(
                    "Longest Win Streak",
                    f"{streaks['longest_win']} wins",
                    f"Longest losing streak: {streaks['longest_loss']} games",
                ),
                render_showcase_award(
                    "Champion Pool",
                    f"{int(player.get('unique_champions', 0))} champs",
                    (
                        f"{pct(pool_rate)} unique-pick rate; "
                        f"{pool_rank_detail}, "
                        f"#{unique_champ_rank.get(name, 0)} by count"
                    ),
                ),
                render_showcase_award("Lab Pick", practice_champion, practice_detail),
            ]
        )

        death_delta = field_avg_deaths - float(player.get("avg_deaths", 0))
        if death_delta >= 0.25:
            death_value = "Cleaner than field"
            death_detail = f"{one_decimal(abs(death_delta))} fewer deaths per game than the player average."
        elif death_delta <= -0.25:
            death_value = "High-risk line"
            death_detail = f"{one_decimal(abs(death_delta))} more deaths per game than the player average."
        else:
            death_value = "Middle lane chaos"
            death_detail = "Death rate sits close to the group average."

        insights_html = "".join(
            [
                render_showcase_insight(
                    "Comfort Zone",
                    f"{main_role} {pct(main_role_share)}",
                    f"{main_role_games} of {player_games} games came in this role.",
                ),
                render_showcase_insight(
                    "Recent Form",
                    f"{recent_wins}-{len(recent) - recent_wins}",
                    f"Last {len(recent)} games: {pct(recent_winrate)} WR vs {pct(winrate)} overall.",
                ),
                render_showcase_insight("Season Arc", arc_value, arc_detail),
                render_showcase_insight(
                    "Peak Damage",
                    f"{kill_record.kills} kills",
                    f"{kill_record.champion} {kill_record.role}, {showcase_match_label(kill_record)}.",
                ),
                render_showcase_insight("Death Profile", death_value, death_detail),
                render_showcase_insight(
                    "Current Thread",
                    f"{streaks['active_length']} {streaks['active_result']}",
                    f"Most recent run entering the latest match in the data.",
                ),
            ]
        )

        champion_html = "".join(render_showcase_champion(row) for row in top_champion_rows)
        role_html = render_showcase_role_bars(role_rows, player_games)
        fingerprint_html = render_showcase_fingerprint(fingerprint_by_name.get(name))
        recent_form_html = render_showcase_recent_form(form_by_name.get(name, {}))
        player_kda = two_decimal(float(player.get("kda_ratio", 0)))
        player_average_line = (
            f"{one_decimal(float(player.get('avg_kills', 0)))} / "
            f"{one_decimal(float(player.get('avg_deaths', 0)))} / "
            f"{one_decimal(float(player.get('avg_assists', 0)))} avg"
        )
        signature_kda = two_decimal(float(signature.get("kda_ratio", 0)))
        moments_html = "".join(
            [
                render_showcase_moment(
                    "Peak Match",
                    f"{best_match.takedowns} takedowns",
                    f"{best_match.champion} {best_match.role}, {showcase_kda(best_match)}, {showcase_match_label(best_match)}.",
                ),
                render_showcase_moment(
                    "Kill Record",
                    f"{kill_record.kills} kills",
                    f"{kill_record.champion}, {showcase_kda(kill_record)}, {showcase_match_label(kill_record)}.",
                ),
                render_showcase_moment(
                    "Assist Record",
                    f"{assist_record.assists} assists",
                    f"{assist_record.champion}, {showcase_kda(assist_record)}, {showcase_match_label(assist_record)}.",
                ),
                render_showcase_moment(
                    "Hardest Lesson",
                    f"{hardest_game.deaths} deaths",
                    f"{hardest_game.champion} {hardest_game.role}, {showcase_match_label(hardest_game)}.",
                ),
            ]
        )

        sections.append(
            f"""
            <section class="player-showcase showcase-theme-{index % 5}" data-showcase="{html_attr(slug)}" id="{html_attr(slug)}">
              <div class="showcase-hero">
                <img class="showcase-watermark" src="{html_attr(champion_icon_url(signature_champion))}" alt="">
                <div class="showcase-title">
                  <div class="showcase-kicker">Player Showcase / {escape(mvp_rank_label)}</div>
                  <h2>{escape(name)}</h2>
                  <p class="showcase-summary">{escape(summary)}</p>
                </div>
                {fingerprint_html}
                <div class="showcase-hero-grid">
                  {render_showcase_stat("Games", integer(player_games), f"#{games_rank.get(name, 0)} by volume", None)}
                  {render_showcase_stat("Winrate", pct(winrate), f"{wins}-{player_games - wins} record", winrate)}
                  {render_showcase_stat("KDA", player_kda, player_average_line, None)}
                  {render_showcase_stat("MVP Score", score(mvp_score) if mvp_eligible else "N/A", mvp_stat_detail, safe_div(mvp_score, 100) if mvp_eligible else None)}
                  <article class="showcase-feature">
                    <img src="{html_attr(champion_icon_url(signature_champion))}" alt="{html_attr(signature_champion)}">
                    <div>
                      <span>Most Played Champion</span>
                      <strong>{escape(signature_champion)}</strong>
                      <small>{signature_games} games, {pct(signature_winrate)} WR, {signature_kda} KDA</small>
                    </div>
                  </article>
                </div>
              </div>

              <div class="showcase-band">
                <div class="showcase-band-inner">
                  <div class="showcase-band-title">
                    <h3>Personal Awards</h3>
                    <small>Built only from this custom-games history</small>
                  </div>
                  <div class="showcase-awards">{awards_html}</div>
                </div>
              </div>

              <div class="showcase-band">
                <div class="showcase-band-inner showcase-grid-two">
                  <div>
                    <div class="showcase-band-title">
                      <h3>Champion Identity</h3>
                      <small>Most played picks</small>
                    </div>
                    <div class="showcase-champ-grid">{champion_html}</div>
                  </div>
                  <div>
                    <div class="showcase-band-title">
                      <h3>Role Shape</h3>
                      <small>{escape(main_role)} leads the profile</small>
                    </div>
                    {role_html}
                  </div>
                </div>
              </div>

              <div class="showcase-band">
                <div class="showcase-band-inner">
                  <div class="showcase-band-title">
                    <h3>Hidden Gems</h3>
                    <small>Trend, comfort, and risk signals</small>
                  </div>
                  <div class="showcase-insights">{insights_html}</div>
                </div>
              </div>

              <div class="showcase-band">
                <div class="showcase-band-inner">
                  <div class="showcase-band-title">
                    <h3>Ups And Downs</h3>
                    <small>Peaks, pain points, and the latest run</small>
                  </div>
                  <div class="showcase-moments">{moments_html}</div>
                </div>
              </div>

              <div class="showcase-band">
                <div class="showcase-band-inner">
                  <div class="showcase-band-title">
                    <h3>Recent Form</h3>
                    <small>Momentum snapshot from the last 10 games</small>
                  </div>
                  {recent_form_html}
                </div>
              </div>

              <div class="showcase-band">
                <div class="showcase-band-inner">
                  <div class="showcase-band-title">
                    <h3>Recent Match Tape</h3>
                    <small>Last {min(12, len(records))} appearances</small>
                  </div>
                  {render_showcase_timeline(records)}
                </div>
              </div>
            </section>
            """
        )

    first_slug = player_showcase_slug(ordered_names[0]) if ordered_names else ""
    showcase_script = """
    const showcaseSelect = document.querySelector("[data-showcase-select]");
    const showcasePanels = Array.from(document.querySelectorAll("[data-showcase]"));

    function showPlayerShowcase(id, updateHash = true) {
      const target = showcasePanels.find(panel => panel.dataset.showcase === id) || showcasePanels[0];
      if (!target) return;
      showcasePanels.forEach(panel => panel.classList.toggle("active", panel === target));
      if (showcaseSelect) showcaseSelect.value = target.dataset.showcase;
      if (updateHash) {
        history.replaceState(null, "", `#${target.dataset.showcase}`);
      }
    }

    if (showcaseSelect && showcasePanels.length) {
      showcaseSelect.addEventListener("change", () => showPlayerShowcase(showcaseSelect.value));
      const initial = window.location.hash.replace(/^#/, "");
      showPlayerShowcase(initial || showcaseSelect.value || showcasePanels[0].dataset.showcase, false);
    }
    """

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>LoL Player Showcases</title>
  <style>{shared_style}{render_showcase_css()}</style>
</head>
<body class="showcase-body">
  {render_hidden_head_to_head_link(head_to_head_page_name)}
  <header>
    <div class="topline">
      <div>
        <h1>LoL Player Showcases</h1>
        <p>Full-page player recaps, signature picks, personal awards, and match-history arcs from the same custom-games dataset.</p>
      </div>
      {render_refresh_control(generated_at)}
    </div>
  </header>
  <nav>
    <a href="{html_attr(main_page_name)}#overview">Overview</a>
    <a href="{html_attr(main_page_name)}#awards">Awards</a>
    <a href="{html_attr(main_page_name)}#match-history">Matches</a>
    <a href="{html_attr(main_page_name)}#players">Players</a>
    <a href="{html_attr(main_page_name)}#champion-pools">Champion Pools</a>
    <a href="{html_attr(main_page_name)}#champions">Champions</a>
    <a href="{html_attr(main_page_name)}#role-pools">Role Pools</a>
    <a href="{html_attr(main_page_name)}#combos">Combos</a>
    <a href="{html_attr(teams_page_name)}#teams">Teams</a>
    <a href="{html_attr(draft_coach_page_name)}#draft-coach">Draft Coach</a>
    <a href="#{html_attr(first_slug)}">Showcases</a>
    <a href="{html_attr(experimental_page_name)}#custom-meta">Experimental</a>
  </nav>
  <main>
    <div class="showcase-toolbar">
      <label>
        <span>Player Showcase</span>
        <select data-showcase-select>{"".join(options)}</select>
      </label>
      <div class="showcase-count">{len(options)} player recaps</div>
    </div>
    {"".join(sections)}
  </main>
  <script>{showcase_script}{render_refresh_script()}</script>
</body>
</html>
"""


def render_role_champion_browser(role_rows: Sequence[dict[str, object]]) -> str:
    role_accents = {
        "TOP": "#4fc48b",
        "JUNGLE": "#62a8ff",
        "MID": "#b596ff",
        "BOT": "#ff6f81",
        "SUPP": "#f0c96a",
    }
    buttons = []
    panels = []
    for index, row in enumerate(role_rows):
        role = str(row["role"])
        active_class = " active" if index == 0 else ""
        buttons.append(
            f'<button type="button" class="role-tab{active_class}" data-role-tab="{html_attr(role)}">{escape(role)}</button>'
        )
        champion_counts = row.get("champion_counts", Counter())
        max_games = max(champion_counts.values(), default=1)
        champion_rows = []
        for champion, games in sorted(
            champion_counts.items(), key=lambda item: (-item[1], str(item[0]))
        ):
            width = max(3.0, games / max_games * 100)
            champion_name = str(champion)
            accent = role_accents.get(role, "#62a8ff")
            champion_rows.append(
                f"""
                <div class="role-champion-row" style="--bar-accent: {accent};">
                  <span><img src="{html_attr(champion_icon_url(champion_name))}" alt="{html_attr(champion_name)}">{escape(champion_name)}</span>
                  <b>{games}</b>
                  <div class="bar-track"><div class="bar-fill" style="width: {width:.2f}%"></div></div>
                </div>
                """
            )
        panels.append(
            f"""
            <article class="role-pool-panel{active_class}" data-role-panel="{html_attr(role)}">
              <div class="role-pool-summary">
                <strong>{escape(role)}</strong>
                <span>{row['unique_champions']} unique champions</span>
                <span>{pct(float(row.get('champion_pool_rate', 0)))} unique-pick rate</span>
                <small>{row.get('matches', '-')} matches</small>
              </div>
              <div class="role-champion-list">{''.join(champion_rows)}</div>
            </article>
            """
        )
    return f"""
    <section class="role-pool-browser">
      <div class="role-tabs">{''.join(buttons)}</div>
      <div class="role-pool-panels">{''.join(panels)}</div>
    </section>
    """


def role_filter_control(table_id: str) -> str:
    options = ['<option value="">All roles</option>']
    options.extend(
        f'<option value="{html_attr(role)}">{escape(role)}</option>' for role in ROLE_ORDER
    )
    return (
        f'<select class="table-role-filter" data-role-filter="{html_attr(table_id)}" '
        f'aria-label="Filter by role">{"".join(options)}</select>'
    )


def render_scoring_formula_explainer(
    mvp_rows: Sequence[dict[str, object]],
    role_score_rows: Sequence[dict[str, object]],
    player_rows: Sequence[dict[str, object]],
    player_role_rows: Sequence[dict[str, object]],
    *,
    example_player: str = "Felix",
) -> str:
    if not mvp_rows:
        return ""

    mvp_by_name = {str(row.get("name", "")): row for row in mvp_rows}
    player_example = mvp_by_name.get(example_player, mvp_rows[0])
    example_name = str(player_example.get("name", example_player))
    example_roles = [
        row for row in role_score_rows if str(row.get("name", "")) == example_name
    ]
    role_example = next(
        (row for row in example_roles if str(row.get("role", "")) == "JUNGLE"),
        None,
    )
    if role_example is None and example_roles:
        role_example = max(example_roles, key=lambda row: float(row.get("role_score", 0)))

    eligible_player_rows = qualify(
        without_spotlight_excluded_players(player_rows), MIN_PLAYER_GAMES
    )
    net_win_low, net_win_high = metric_bounds(eligible_player_rows, "net_wins")
    kda_low, kda_high = metric_bounds(eligible_player_rows, "kda_ratio")
    kp_low, kp_high = metric_bounds(eligible_player_rows, "kill_participation")
    role_net_win_low, role_net_win_high = metric_bounds(player_role_rows, "net_wins")
    role_kda_low, role_kda_high = metric_bounds(player_role_rows, "kda_ratio")
    role_kp_low, role_kp_high = metric_bounds(player_role_rows, "kill_participation")

    def weighted_points(component_score: float, weight: float) -> str:
        return score(component_score * weight * 100)

    def weighted_formula(weights: dict[str, float]) -> str:
        return " + ".join(
            f"({name} score x {weight:.2f})" for name, weight in weights.items()
        )

    def formula_rows(rows: Sequence[tuple[str, str, str, str, str, str]]) -> str:
        return "\n".join(
            f"""
            <tr>
              <td><b>{escape(metric)}</b><small>{escape(detail)}</small></td>
              <td>{escape(raw)}</td>
              <td class="number-cell">{escape(converted)}</td>
              <td class="number-cell">{escape(weight)}</td>
              <td class="number-cell">{escape(points)}</td>
            </tr>
            """
            for metric, detail, raw, converted, weight, points in rows
        )

    def formula_table(
        title: str,
        note: str,
        rows: Sequence[tuple[str, str, str, str, str, str]],
        total_label: str,
        total_score: float,
    ) -> str:
        return f"""
        <section class="table-panel formula-example-panel">
          <div class="section-heading">
            <h3>{escape(title)}</h3>
            <small>{escape(note)}</small>
          </div>
          <div class="table-wrap">
            <table class="formula-table">
              <thead>
                <tr>
                  <th>Metric</th>
                  <th>Raw input</th>
                  <th>Converted score</th>
                  <th>Weight</th>
                  <th>Points</th>
                </tr>
              </thead>
              <tbody>{formula_rows(rows)}</tbody>
            </table>
          </div>
          <div class="formula-total">
            <b>{escape(total_label)}</b>
            <strong>{score(total_score)}</strong>
          </div>
        </section>
        """

    mvp_net_win_score = float(player_example.get("net_win_score", 0))
    mvp_kda_score = float(player_example.get("kda_score", 0))
    mvp_kp_score = float(player_example.get("kill_participation_score", 0))
    mvp_pool_score = float(player_example.get("champion_pool_score", 0))
    mvp_games_score = float(player_example.get("games_score", 0))
    player_games = int(player_example.get("games", 0))
    player_wins = int(player_example.get("wins", 0))
    player_losses = int(player_example.get("losses", 0))
    player_net_wins = int(player_example.get("net_wins", 0))
    player_kills = int(player_example.get("kills", 0))
    player_deaths = int(player_example.get("deaths", 0))
    player_assists = int(player_example.get("assists", 0))
    player_unique_champs = int(player_example.get("unique_champions", 0))
    player_pool_rate = float(player_example.get("champion_pool_rate", 0))
    player_kp = float(player_example.get("kill_participation", 0))

    mvp_example_rows = [
        (
            "Net Wins",
            f"Wins minus losses after meeting the {MIN_PLAYER_GAMES}-game MVP-board minimum. This rewards players who keep adding wins over a larger sample.",
            f"{player_wins}-{player_losses}, net {signed_integer(player_net_wins)}; range {signed_integer(net_win_low)} to {signed_integer(net_win_high)}",
            pct(mvp_net_win_score),
            pct(MVP_WEIGHTS["Net Wins"]),
            weighted_points(mvp_net_win_score, MVP_WEIGHTS["Net Wins"]),
        ),
        (
            "KDA",
            "KDA = (kills + assists) / deaths, then normalized against the current player range.",
            f"({player_kills} + {player_assists}) / {max(1, player_deaths)} = {two_decimal(float(player_example.get('kda_ratio', 0)))}; range {two_decimal(kda_low)} to {two_decimal(kda_high)}",
            pct(mvp_kda_score),
            pct(MVP_WEIGHTS["KDA"]),
            weighted_points(mvp_kda_score, MVP_WEIGHTS["KDA"]),
        ),
        (
            "Kill Participation",
            "Average per-game share of team kills: (kills + assists) / team kills.",
            f"{pct(player_kp)} average KP; range {pct(kp_low)} to {pct(kp_high)}",
            pct(mvp_kp_score),
            pct(MVP_WEIGHTS["Kill Participation"]),
            weighted_points(mvp_kp_score, MVP_WEIGHTS["Kill Participation"]),
        ),
        (
            "Champion Pool",
            "Unique-pick rate with a square-root curve: sqrt(unique champions / games).",
            f"{player_unique_champs} unique champions / {player_games} games = {pct(player_pool_rate)}",
            pct(mvp_pool_score),
            pct(MVP_WEIGHTS["Champion Pool"]),
            weighted_points(mvp_pool_score, MVP_WEIGHTS["Champion Pool"]),
        ),
        (
            "Games",
            f"Capped sample score: min(sqrt(games / {GAME_SCORE_TARGET}), 1).",
            f"{player_games} games; min(sqrt({player_games} / {GAME_SCORE_TARGET}), 1)",
            pct(mvp_games_score),
            pct(MVP_WEIGHTS["Games"]),
            weighted_points(mvp_games_score, MVP_WEIGHTS["Games"]),
        ),
    ]

    definition_rows = [
        (
            "Net Wins",
            f"Wins minus losses for players with at least {MIN_PLAYER_GAMES} games. It rewards strong records over a bigger sample without making raw winrate carry the score.",
        ),
        (
            "KDA / Role KDA",
            "Kills plus assists divided by deaths. The dashboard converts this to a 0-100% component by comparing it to the lowest and highest KDA in the current dataset.",
        ),
        (
            "Kill Participation / Role Kill Participation",
            "Average per-game share of team kills where kills and assists both count. For example, 0/2/15 in a 30-kill team game is 50% KP.",
        ),
        (
            "Champion Pool / Role Champion Pool",
            "Unique-pick rate rather than raw unique champion count. A player with 16 unique champions in 17 games rates higher than a player with 20 unique champions in 60 games.",
        ),
        (
            "Games / Role Games",
            f"A small capped sample-size component: min(sqrt(games / {GAME_SCORE_TARGET}), 1). Twenty or more games gets full credit.",
        ),
        (
            "Role Reliability",
            f"Role games also pull role-only KDA, KP, and champion pool metrics toward neutral until that role reaches {ROLE_RELIABILITY_GAMES} games.",
        ),
        (
            "Role Preference",
            "Role fit does not add visible score points. The team builder uses it only as a small assignment tiebreaker after role score, ranked by games played then role winrate.",
        ),
        (
            "Overall MVP",
            "The player's overall MVP score divided by 100. It now carries most of the team role score, so stronger players are prioritized while role-only stats break ties.",
        ),
    ]
    definition_html = "\n".join(
        f"<li><b>{escape(title)}</b><small>{escape(detail)}</small></li>"
        for title, detail in definition_rows
    )

    role_table_html = ""
    if role_example:
        role = str(role_example.get("role", "Role"))
        role_reliability = float(role_example.get("reliability", 0))
        role_net_win_score = float(role_example.get("role_net_win_score", 0))
        role_kda_score = float(role_example.get("role_kda_score", 0))
        role_kp_score = float(role_example.get("role_kp_score", 0))
        role_pool_score = float(role_example.get("role_pool_score", 0))
        role_games_score = float(role_example.get("role_games_score", 0))
        overall_mvp_score = float(role_example.get("overall_mvp_score", 0))
        role_games = int(role_example.get("games", 0))
        role_wins = int(role_example.get("wins", 0))
        role_losses = int(role_example.get("losses", 0))
        role_net_wins = int(role_example.get("net_wins", 0))
        role_kills = int(role_example.get("kills", 0))
        role_deaths = int(role_example.get("deaths", 0))
        role_assists = int(role_example.get("assists", 0))
        role_unique_champs = int(role_example.get("unique_champions", 0))
        role_pool_rate = float(role_example.get("champion_pool_rate", 0))
        role_kp = float(role_example.get("kill_participation", 0))
        role_example_rows = [
            (
                "Role Net Wins",
                "Wins minus losses in this role, normalized against every player-role record.",
                f"{role_wins}-{role_losses}, net {signed_integer(role_net_wins)} {role}; range {signed_integer(role_net_win_low)} to {signed_integer(role_net_win_high)}",
                pct(role_net_win_score),
                pct(ROLE_SCORE_WEIGHTS["Role Net Wins"]),
                weighted_points(
                    role_net_win_score, ROLE_SCORE_WEIGHTS["Role Net Wins"]
                ),
            ),
            (
                "Role KDA",
                "Role KDA is normalized against every player-role KDA in the current dataset, then reliability-adjusted for small role samples.",
                f"({role_kills} + {role_assists}) / {max(1, role_deaths)} = {two_decimal(float(role_example.get('kda_ratio', 0)))}; range {two_decimal(role_kda_low)} to {two_decimal(role_kda_high)}; reliability {pct(role_reliability)}",
                pct(role_kda_score),
                pct(ROLE_SCORE_WEIGHTS["Role KDA"]),
                weighted_points(role_kda_score, ROLE_SCORE_WEIGHTS["Role KDA"]),
            ),
            (
                "Role Kill Participation",
                "Role KP is average per-game share of team kills while playing this role, reliability-adjusted for small role samples.",
                f"{pct(role_kp)} {role} KP; range {pct(role_kp_low)} to {pct(role_kp_high)}; reliability {pct(role_reliability)}",
                pct(role_kp_score),
                pct(ROLE_SCORE_WEIGHTS["Role Kill Participation"]),
                weighted_points(
                    role_kp_score, ROLE_SCORE_WEIGHTS["Role Kill Participation"]
                ),
            ),
            (
                "Role Champion Pool",
                "Role-specific unique-pick rate with role reliability.",
                f"{role_unique_champs} unique {role} champions / {role_games} games = {pct(role_pool_rate)}; reliability {pct(role_reliability)}",
                pct(role_pool_score),
                pct(ROLE_SCORE_WEIGHTS["Role Champion Pool"]),
                weighted_points(
                    role_pool_score, ROLE_SCORE_WEIGHTS["Role Champion Pool"]
                ),
            ),
            (
                "Role Games",
                f"Capped role sample score: min(sqrt(role games / {GAME_SCORE_TARGET}), 1).",
                f"{role_games} {role} games; min(sqrt({role_games} / {GAME_SCORE_TARGET}), 1)",
                pct(role_games_score),
                pct(ROLE_SCORE_WEIGHTS["Role Games"]),
                weighted_points(role_games_score, ROLE_SCORE_WEIGHTS["Role Games"]),
            ),
            (
                "Overall MVP",
                "The largest role-score component, using the player's overall MVP score.",
                f"{example_name} MVP score {score(float(player_example.get('mvp_score', 0)))} / 100",
                pct(overall_mvp_score),
                pct(ROLE_SCORE_WEIGHTS["Overall MVP"]),
                weighted_points(
                    overall_mvp_score, ROLE_SCORE_WEIGHTS["Overall MVP"]
                ),
            ),
        ]
        role_table_html = formula_table(
            f"{example_name} {role} Role Score Example",
            f"These points add up to the {role} score used when building drafted teams.",
            role_example_rows,
            f"{example_name} {role} Role Score",
            float(role_example.get("role_score", 0)),
        )

    return f"""
    <section id="scoring-guide" class="section scoring-guide">
      <div class="section-title">
        <div>
          <h2>How MVP & Team Scores Work</h2>
          <p class="note">Every component is converted into a 0-100% score, multiplied by its weight, then added together. Normalized components are relative to the current match history, so new data can slightly move the ranges.</p>
        </div>
      </div>
      <div class="formula-grid">
        <section class="table-panel formula-definition-panel">
          <div class="section-heading">
            <h3>Metric Meanings</h3>
            <small>What each part is trying to reward</small>
          </div>
          <ul class="formula-list">
            {definition_html}
          </ul>
        </section>
        <section class="table-panel formula-definition-panel">
          <div class="section-heading">
            <h3>Final Formulas</h3>
            <small>The exact weights used by the dashboard</small>
          </div>
          <div class="formula-copy">
            <p><b>MVP score</b> = 100 x ({escape(weighted_formula(MVP_WEIGHTS))}).</p>
            <p><b>Team role score</b> = 100 x ({escape(weighted_formula(ROLE_SCORE_WEIGHTS))}).</p>
            <p>Overall MVP only includes players with at least {MIN_PLAYER_GAMES} games. After that, games add a small capped 5% sample score and can also help through positive net wins. Role Share does not score directly. Role games score 5% directly and also affect role-metric reliability, which reaches full strength at {ROLE_RELIABILITY_GAMES} games. Role preference is assignment-only and does not add visible score points.</p>
          </div>
        </section>
      </div>
      <div class="formula-example-grid">
        {formula_table(
            f"{example_name} MVP Score Example",
            "The Points column is the converted score multiplied by that metric's weight.",
            mvp_example_rows,
            f"{example_name} MVP Score",
            float(player_example.get("mvp_score", 0)),
        )}
        {role_table_html}
      </div>
    </section>
    """


def build_dashboard(
    input_path: Path, output_path: Path, *, api_url: str = "", api_key: str = ""
) -> None:
    _raw_matches, appearances = load_appearances(
        input_path, api_url=api_url, api_key=api_key
    )
    matches = match_summaries(appearances)
    weekday_rows = weekday_volume_rows(matches)
    busiest_weekday = max(
        weekday_rows,
        key=lambda row: (int(row["games"]), WEEKDAY_ORDER.index(str(row["weekday"]))),
    )

    player_rows = sorted(
        aggregate(appearances, ("name",)),
        key=lambda row: (-float(row["winrate"]), -int(row["games"]), str(row["name"])),
    )
    champion_rows = sorted(
        aggregate(appearances, ("champion",)),
        key=lambda row: (-int(row["games"]), -float(row["winrate"]), str(row["champion"])),
    )
    unplayed_champions = unplayed_champion_rows(appearances)
    champion_winrate_rows = sorted(
        champion_rows,
        key=lambda row: (-float(row["winrate"]), -int(row["games"]), str(row["champion"])),
    )
    champion_role_rows = sorted(
        aggregate(appearances, ("champion", "role")),
        key=lambda row: (
            str(row["champion"]),
            role_sort(str(row["role"])),
            -int(row["games"]),
        ),
    )
    player_role_rows = sorted(
        aggregate(appearances, ("name", "role")),
        key=lambda row: (-int(row["games"]), str(row["name"]), role_sort(str(row["role"]))),
    )
    player_champion_rows = sorted(
        aggregate(appearances, ("name", "champion")),
        key=lambda row: (-int(row["games"]), -float(row["winrate"]), str(row["name"])),
    )
    player_champion_role_rows = sorted(
        aggregate(appearances, ("name", "champion", "role")),
        key=lambda row: (-int(row["games"]), -float(row["winrate"]), str(row["name"])),
    )
    role_rows = sorted(
        aggregate(appearances, ("role",)), key=lambda row: role_sort(str(row["role"]))
    )
    role_champion_pool = role_champion_pool_rows(appearances)
    for row in role_champion_pool:
        row["matches"] = len(matches)
    player_role_champion_pool = player_role_champion_pool_rows(appearances)
    duo_rows = team_combo_rows(appearances, 2, TEAM_COMBO_MIN_GAMES[2])
    trio_rows = team_combo_rows(appearances, 3, TEAM_COMBO_MIN_GAMES[3])
    four_rows = team_combo_rows(appearances, 4, TEAM_COMBO_MIN_GAMES[4])
    five_rows = team_combo_rows(appearances, 5, TEAM_COMBO_MIN_GAMES[5])
    h2h_rows = head_to_head_rows(appearances)
    champion_h2h_rows = champion_head_to_head_rows(appearances)
    pilot_champion_h2h_rows = pilot_champion_head_to_head_rows(appearances)
    add_player_role_breakdowns(player_rows, player_role_rows)
    visible_appearances = [
        appearance
        for appearance in appearances
        if not is_spotlight_excluded_player(appearance.name)
    ]
    display_player_rows = without_spotlight_excluded_players(player_rows)
    display_player_role_rows = without_spotlight_excluded_players(player_role_rows)
    display_player_champion_rows = without_spotlight_excluded_players(
        player_champion_rows
    )
    display_player_champion_role_rows = without_spotlight_excluded_players(
        player_champion_role_rows
    )
    display_player_role_champion_pool = without_spotlight_excluded_players(
        player_role_champion_pool
    )
    mvp_rows = mvp_score_rows(player_rows)
    target_ban_rows = target_ban_score_rows(player_champion_rows, player_rows, mvp_rows)
    target_pick_rows = target_ban_score_rows(
        player_champion_role_rows, player_rows, mvp_rows
    )
    practice_pick_rows = practice_pick_score_rows(player_champion_rows, player_rows)
    display_target_ban_rows = without_spotlight_excluded_players(target_ban_rows)
    display_target_pick_rows = without_spotlight_excluded_players(target_pick_rows)
    display_practice_pick_rows = without_spotlight_excluded_players(practice_pick_rows)
    best_mvp = find_first(mvp_rows)
    role_score_rows = player_role_score_rows(player_rows, player_role_rows, mvp_rows)
    tiered_teams, unused_team_players = build_tiered_teams(player_rows, role_score_rows)
    experimental_champion_rows = sorted(
        aggregate(visible_appearances, ("champion",)),
        key=lambda row: (-int(row["games"]), -float(row["winrate"]), str(row["champion"])),
    )
    experimental_champion_role_rows = sorted(
        aggregate(visible_appearances, ("champion", "role")),
        key=lambda row: (
            str(row["champion"]),
            role_sort(str(row["role"])),
            -int(row["games"]),
        ),
    )
    custom_meta_rows = custom_meta_tier_rows(
        experimental_champion_role_rows, display_player_champion_role_rows
    )
    fingerprint_rows = player_fingerprint_rows(
        visible_appearances, display_player_rows, display_player_champion_role_rows
    )
    form_rows = recent_form_rows(visible_appearances, display_player_rows, mvp_rows)
    hall_rows = experimental_hall_rows(
        visible_appearances,
        experimental_champion_rows,
        display_player_role_rows,
        display_player_champion_rows,
        display_player_champion_role_rows,
    )
    chemistry_data = experimental_chemistry_data(visible_appearances, display_player_rows)
    upset_data = experimental_upset_rows(
        visible_appearances,
        display_player_rows,
        mvp_rows,
        role_score_rows,
        display_player_champion_role_rows,
    )
    ownership_rows = champion_ownership_rows(
        visible_appearances,
        experimental_champion_rows,
        experimental_champion_role_rows,
        display_player_champion_rows,
        display_target_ban_rows,
    )
    awards = build_awards(
        appearances,
        player_rows,
        champion_rows,
        player_role_rows,
        player_champion_rows,
        player_champion_role_rows,
        matches,
    )

    first_timestamp = min((row.timestamp for row in appearances if row.timestamp), default="")
    last_timestamp = max((row.timestamp for row in appearances if row.timestamp), default="")
    first_date = format_date(first_timestamp)
    last_date = format_date(last_timestamp)
    generated_at = format_refresh_timestamp(datetime.now(LOCAL_TZ))
    teams_output_path = teams_page_path(output_path)
    draft_coach_output_path = draft_coach_page_path(output_path)
    showcase_output_path = showcases_page_path(output_path)
    head_to_head_output_path = head_to_head_page_path(output_path)
    experimental_output_path = experimental_page_path(output_path)
    main_page_name = output_path.name
    teams_page_name = teams_output_path.name
    draft_coach_page_name = draft_coach_output_path.name
    showcases_page_name = showcase_output_path.name
    head_to_head_page_name = head_to_head_output_path.name
    experimental_page_name = experimental_output_path.name

    metric_cards = "".join(
        [
            render_metric_card("Matches", integer(len(matches)), f"{first_date} to {last_date}"),
            render_metric_card(
                "Players", integer(len(player_rows)), "Unique real-name entries"
            ),
            render_metric_card(
                "Champions", integer(len(champion_rows)), "Unique champions played"
            ),
            render_metric_card(
                "Avg Kills",
                one_decimal(sum(row.kills for row in appearances) / len(matches)),
                "Combined kills per game",
            ),
            render_metric_card(
                "MVP",
                str(best_mvp.get("name", "-")),
                f"{score(float(best_mvp.get('mvp_score', 0)))} score, {best_mvp.get('games', 0)} games",
            ),
            render_metric_card(
                "Busiest Day",
                str(busiest_weekday["weekday"]),
                f"{busiest_weekday['games']} games, {pct(float(busiest_weekday['share']))} of matches",
            ),
        ]
    )

    winrate_chart_player_rows = qualify(
        without_spotlight_excluded_players(player_rows), WINRATE_CHART_MIN_GAMES
    )
    top_player_chart_rows = sorted(
        winrate_chart_player_rows,
        key=lambda row: (-float(row["winrate"]), -int(row["games"])),
    )
    top_player_chart_names = {
        str(row.get("name", "")).casefold() for row in top_player_chart_rows[:10]
    }
    bottom_player_chart_rows = sorted(
        [
            row
            for row in winrate_chart_player_rows
            if str(row.get("name", "")).casefold() not in top_player_chart_names
        ],
        key=lambda row: (float(row["winrate"]), -int(row["games"])),
    )
    top_kda_chart_rows = sorted(
        qualify(display_player_rows, MIN_PLAYER_GAMES),
        key=lambda row: (-float(row["kda_ratio"]), -int(row["games"])),
    )
    most_played_champion_rows = sorted(champion_rows, key=lambda row: -int(row["games"]))
    popular_champion_strip_rows = [
        row
        for row in most_played_champion_rows
        if not is_most_contested_excluded_champion(row.get("champion", ""))
    ]
    top_champion_winrate_rows = sorted(
        qualify(champion_rows, MIN_CHAMPION_GAMES),
        key=lambda row: (-float(row["winrate"]), -int(row["games"])),
    )
    bottom_champion_winrate_rows = sorted(
        qualify(champion_rows, MIN_CHAMPION_GAMES),
        key=lambda row: (float(row["winrate"]), -int(row["games"])),
    )

    player_columns: list[Column] = [
        ("Player", "name", str, "text"),
        ("Games", "games", integer, "number"),
        ("W", "wins", integer, "number"),
        ("L", "losses", integer, "number"),
        ("Winrate", "winrate", lambda value: pct(float(value)), "number"),
        ("KDA", "kda_ratio", lambda value: two_decimal(float(value)), "number"),
        ("KP", "kill_participation", lambda value: pct(float(value)), "number"),
        ("K", "avg_kills", lambda value: one_decimal(float(value)), "number"),
        ("D", "avg_deaths", lambda value: one_decimal(float(value)), "number"),
        ("A", "avg_assists", lambda value: one_decimal(float(value)), "number"),
        ("Unique Champs", "unique_champions", integer, "number"),
        ("Roles Played", "unique_roles", integer, "number"),
        ("TOP", "role_top", str, "text"),
        ("JUNGLE", "role_jungle", str, "text"),
        ("MID", "role_mid", str, "text"),
        ("BOT", "role_bot", str, "text"),
        ("SUPP", "role_supp", str, "text"),
        ("Main Champs", "most_played_champion", str, "text"),
    ]
    mvp_columns: list[Column] = [
        ("Rank", "mvp_rank", integer, "number"),
        ("Player", "name", str, "text"),
        ("MVP Score", "mvp_score", score, "number"),
        ("Games", "games", integer, "number"),
        ("Net W", "net_wins", signed_integer, "number"),
        ("KDA", "kda_ratio", lambda value: two_decimal(float(value)), "number"),
        ("KP", "kill_participation", lambda value: pct(float(value)), "number"),
        ("Unique Champs", "unique_champions", integer, "number"),
        ("Unique Pick %", "champion_pool_rate", lambda value: pct(float(value)), "number"),
    ]
    champion_columns: list[Column] = [
        ("Champion", "champion", str, "text"),
        ("Games", "games", integer, "number"),
        ("W", "wins", integer, "number"),
        ("L", "losses", integer, "number"),
        ("Winrate", "winrate", lambda value: pct(float(value)), "number"),
        ("KDA", "kda_ratio", lambda value: two_decimal(float(value)), "number"),
        ("KP", "kill_participation", lambda value: pct(float(value)), "number"),
        ("K", "avg_kills", lambda value: one_decimal(float(value)), "number"),
        ("D", "avg_deaths", lambda value: one_decimal(float(value)), "number"),
        ("A", "avg_assists", lambda value: one_decimal(float(value)), "number"),
        ("Roles", "top_roles", str, "text"),
    ]
    champion_role_columns: list[Column] = [
        ("Champion", "champion", str, "text"),
        ("Role", "role", str, "text"),
        ("Games", "games", integer, "number"),
        ("W", "wins", integer, "number"),
        ("Winrate", "winrate", lambda value: pct(float(value)), "number"),
        ("KDA", "kda_ratio", lambda value: two_decimal(float(value)), "number"),
        ("KP", "kill_participation", lambda value: pct(float(value)), "number"),
        ("K", "avg_kills", lambda value: one_decimal(float(value)), "number"),
        ("D", "avg_deaths", lambda value: one_decimal(float(value)), "number"),
        ("A", "avg_assists", lambda value: one_decimal(float(value)), "number"),
    ]
    player_role_columns: list[Column] = [
        ("Player", "name", str, "text"),
        ("Role", "role", str, "text"),
        ("Fit", "role_fit", str, "text"),
        ("Games", "games", integer, "number"),
        ("W", "wins", integer, "number"),
        ("Winrate", "winrate", lambda value: pct(float(value)), "number"),
        ("KDA", "kda_ratio", lambda value: two_decimal(float(value)), "number"),
        ("KP", "kill_participation", lambda value: pct(float(value)), "number"),
        ("K", "avg_kills", lambda value: one_decimal(float(value)), "number"),
        ("D", "avg_deaths", lambda value: one_decimal(float(value)), "number"),
        ("A", "avg_assists", lambda value: one_decimal(float(value)), "number"),
        ("Main Champs", "most_played_champion", str, "text"),
    ]
    role_champion_pool_columns: list[Column] = [
        ("Role", "role", str, "text"),
        ("Unique Champs", "unique_champions", integer, "number"),
        ("Games", "games", integer, "number"),
        ("Champions", "champions", str, "text"),
    ]
    player_role_pool_columns: list[Column] = [
        ("Player", "name", str, "text"),
        ("Role", "role", str, "text"),
        ("Unique Champs", "unique_champions", integer, "number"),
        ("Games", "games", integer, "number"),
        ("W", "wins", integer, "number"),
        ("Winrate", "winrate", lambda value: pct(float(value)), "number"),
        ("Champions", "champions", str, "text"),
    ]
    player_champion_role_columns: list[Column] = [
        ("Player", "name", str, "text"),
        ("Champion", "champion", str, "text"),
        ("Role", "role", str, "text"),
        ("Games", "games", integer, "number"),
        ("W", "wins", integer, "number"),
        ("Winrate", "winrate", lambda value: pct(float(value)), "number"),
        ("KDA", "kda_ratio", lambda value: two_decimal(float(value)), "number"),
        ("KP", "kill_participation", lambda value: pct(float(value)), "number"),
        ("K", "avg_kills", lambda value: one_decimal(float(value)), "number"),
        ("D", "avg_deaths", lambda value: one_decimal(float(value)), "number"),
        ("A", "avg_assists", lambda value: one_decimal(float(value)), "number"),
    ]

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>LoL Customs Dashboard</title>
  <style>
    :root {{
      --bg: #080d13;
      --panel: #111923;
      --ink: #e8eef6;
      --muted: #9ba8b7;
      --line: #263241;
      --blue: #62a8ff;
      --green: #4fc48b;
      --red: #ff6f81;
      --gold: #f0c96a;
      --violet: #b596ff;
      --shadow: 0 16px 36px rgba(0, 0, 0, 0.32);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, Segoe UI, Roboto, Arial, sans-serif;
      color: var(--ink);
      background: var(--bg);
      letter-spacing: 0;
    }}
    header {{
      background: #17212b;
      color: white;
      padding: 28px max(24px, calc((100vw - 1320px) / 2)) 22px;
      border-bottom: 5px solid var(--green);
    }}
    header h1 {{
      margin: 0 0 8px;
      font-size: clamp(2rem, 4vw, 3.8rem);
      line-height: 0.95;
      letter-spacing: 0;
    }}
    header p {{
      margin: 0;
      color: #c8d4df;
      max-width: 900px;
      line-height: 1.5;
    }}
    .topline {{
      display: flex;
      justify-content: space-between;
      gap: 20px;
      align-items: flex-start;
    }}
    .generated {{
      flex: 0 0 auto;
      color: #17212b;
      background: #f0c76a;
      border-radius: 6px;
      padding: 8px 10px;
      font-size: 0.86rem;
      font-weight: 700;
    }}
    .header-actions {{
      display: grid;
      justify-items: end;
      gap: 8px;
      min-width: 220px;
    }}
    .refresh-data-button {{
      min-height: 34px;
      border: 1px solid rgba(255, 255, 255, 0.25);
      border-radius: 6px;
      background: #0f1721;
      color: #f7fbff;
      padding: 7px 10px;
      font-weight: 900;
      cursor: pointer;
    }}
    .refresh-data-button:hover {{
      background: #1d2b3b;
    }}
    .refresh-data-button:disabled {{
      cursor: wait;
      opacity: 0.68;
    }}
    .refresh-data-note,
    .refresh-data-status {{
      min-height: 1rem;
      color: #c8d4df;
      font-size: 0.76rem;
      font-weight: 800;
      line-height: 1.3;
      text-align: right;
      max-width: 320px;
    }}
    .refresh-data-note {{
      color: #f0c96a;
    }}
    .refresh-data-status[data-state="ok"] {{
      color: #a9f0ca;
    }}
    .refresh-data-status[data-state="error"] {{
      color: #ffb3bd;
    }}
    nav {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      padding: 12px max(24px, calc((100vw - 1320px) / 2));
      background: #ffffff;
      border-bottom: 1px solid var(--line);
      position: sticky;
      top: 0;
      z-index: 10;
    }}
    nav a {{
      color: var(--ink);
      text-decoration: none;
      font-weight: 700;
      font-size: 0.91rem;
      padding: 8px 10px;
      border-radius: 6px;
    }}
    nav a:hover {{ background: #eef3f8; }}
    .hidden-page-link {{
      position: fixed;
      top: 0;
      right: 0;
      z-index: 9999;
      width: 14px;
      height: 14px;
      display: block;
      background: transparent;
      text-indent: -999px;
    }}
    .hidden-page-link::after {{
      content: "";
      position: absolute;
      top: 0;
      right: 0;
      width: 2px;
      height: 2px;
      background: rgba(240, 201, 106, 0.22);
      border-radius: 0 0 0 1px;
    }}
    .hidden-page-link:hover::after,
    .hidden-page-link:focus-visible::after {{
      background: rgba(240, 201, 106, 0.8);
      box-shadow: 0 0 0 2px rgba(240, 201, 106, 0.18);
    }}
    .hidden-page-link:focus-visible {{
      outline: 1px solid rgba(240, 201, 106, 0.8);
    }}
    main {{
      max-width: 1320px;
      margin: 0 auto;
      padding: 24px;
    }}
    .section {{
      margin: 0 0 32px;
      scroll-margin-top: 76px;
    }}
    .section-title {{
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
      gap: 16px;
      margin: 0 0 14px;
    }}
    h2 {{
      margin: 0;
      font-size: clamp(1.45rem, 2.6vw, 2.2rem);
      letter-spacing: 0;
    }}
    h3 {{
      margin: 0;
      font-size: 1rem;
      letter-spacing: 0;
    }}
    .note {{
      margin: 0;
      color: var(--muted);
      font-size: 0.94rem;
      line-height: 1.4;
    }}
    .metric-grid {{
      display: grid;
      grid-template-columns: repeat(6, minmax(0, 1fr));
      gap: 12px;
    }}
    .metric-card, .chart-panel, .table-panel, .award-card, .svg-panel, .popular-champions-panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
      min-width: 0;
    }}
    .metric-card {{
      min-height: 118px;
      padding: 16px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      border-top: 4px solid var(--blue);
    }}
    .metric-card:nth-child(2) {{ border-top-color: var(--green); }}
    .metric-card:nth-child(3) {{ border-top-color: var(--gold); }}
    .metric-card:nth-child(4) {{ border-top-color: var(--red); }}
    .metric-card:nth-child(5) {{ border-top-color: var(--violet); }}
    .metric-card span, .award-card span {{
      color: var(--muted);
      font-size: 0.78rem;
      text-transform: uppercase;
      font-weight: 800;
    }}
    .metric-card strong {{
      font-size: 2rem;
      line-height: 1;
      margin: 8px 0;
    }}
    small {{
      color: var(--muted);
      line-height: 1.35;
    }}
    .popular-champions-panel {{
      margin-top: 12px;
      overflow: hidden;
    }}
    .popular-champions-panel .section-heading {{
      padding: 12px 16px;
    }}
    .popular-champion-row {{
      display: grid;
      grid-template-columns: repeat(10, minmax(72px, 1fr));
      overflow-x: hidden;
    }}
    .popular-champion-item {{
      min-height: 112px;
      padding: 12px 10px;
      border-right: 1px solid var(--line);
      display: grid;
      gap: 4px;
      align-content: center;
      justify-items: center;
      text-align: center;
    }}
    .popular-champion-item:last-child {{
      border-right: 0;
    }}
    .popular-champion-item span {{
      color: var(--blue);
      font-size: 0.72rem;
      font-weight: 900;
    }}
    .popular-champion-item img {{
      width: 48px;
      height: 48px;
      border-radius: 8px;
      border: 1px solid var(--line);
      display: block;
    }}
    .popular-champion-item b {{
      color: var(--green);
      font-size: 0.82rem;
    }}
    .chart-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
      margin-top: 14px;
    }}
    .chart-grid.single {{
      grid-template-columns: 1fr;
    }}
    .chart-grid.single .bar-row {{
      grid-template-columns: 1fr;
      gap: 6px;
    }}
    .chart-grid.single .bar-row b {{
      text-align: left;
    }}
    .compact-bar-chart .bar-chart {{
      gap: 7px;
    }}
    .compact-bar-chart .bar-row {{
      grid-template-columns: minmax(90px, 140px) 34px minmax(120px, 360px);
      gap: 8px;
      min-height: 24px;
      max-width: 560px;
      padding: 5px 6px;
    }}
    .compact-bar-chart .bar-row::before {{
      display: none;
    }}
    .compact-bar-chart .bar-label {{
      display: grid;
      grid-template-columns: 1fr;
      gap: 0;
    }}
    .compact-bar-chart .bar-label-text {{
      font-size: 0.92rem;
    }}
    .compact-bar-chart .bar-label small {{
      display: none;
    }}
    .compact-bar-chart .bar-track {{
      grid-column: 3;
      grid-row: 1;
      height: 10px;
    }}
    .compact-bar-chart .bar-row b {{
      grid-column: 2;
      grid-row: 1;
      text-align: center;
      color: var(--muted);
      font-size: 0.86rem;
    }}
    .chart-grid.single .compact-bar-chart .bar-row {{
      grid-template-columns: minmax(90px, 140px) 34px minmax(120px, 360px);
      gap: 8px;
      max-width: 560px;
    }}
    .chart-grid.single .compact-bar-chart .bar-track {{
      grid-column: 3;
      grid-row: 1;
    }}
    .chart-grid.single .compact-bar-chart .bar-row b {{
      grid-column: 2;
      grid-row: 1;
      text-align: center;
    }}
    .chart-panel, .svg-panel {{
      padding: 16px;
    }}
    .chart-panel h3 {{
      display: flex;
      align-items: center;
      gap: 10px;
    }}
    .chart-panel h3::after {{
      content: "";
      height: 1px;
      flex: 1;
      background: linear-gradient(90deg, var(--line), transparent);
    }}
    .unplayed-panel {{
      display: flex;
      flex-direction: column;
      gap: 12px;
    }}
    .unplayed-summary {{
      display: grid;
      grid-template-columns: auto 1fr;
      gap: 2px 10px;
      align-items: end;
    }}
    .unplayed-summary strong {{
      font-size: 2rem;
      line-height: 1;
    }}
    .unplayed-summary span {{
      color: var(--ink);
      font-weight: 800;
    }}
    .unplayed-summary small {{
      grid-column: 1 / -1;
    }}
    .champion-chip-list {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      max-height: 190px;
      overflow: auto;
      padding-right: 4px;
    }}
    .champion-chip {{
      border: 1px solid var(--line);
      border-radius: 999px;
      background: #f2f6fa;
      color: #334253;
      font-size: 0.8rem;
      font-weight: 800;
      line-height: 1;
      padding: 6px 8px;
      white-space: nowrap;
    }}
    .empty-list {{
      color: var(--muted);
      font-weight: 700;
    }}
    .roster-source a {{
      color: var(--blue);
      font-weight: 800;
      text-decoration: none;
    }}
    .bar-chart {{
      display: grid;
      gap: 10px;
      margin-top: 14px;
    }}
    .bar-row {{
      --bar-accent: var(--blue);
      display: grid;
      grid-template-columns: 34px minmax(150px, 1fr) 3fr minmax(56px, auto);
      align-items: center;
      gap: 10px;
      min-height: 46px;
      padding: 7px 8px;
      border: 1px solid rgba(151, 164, 181, 0.16);
      border-radius: 8px;
      background:
        linear-gradient(90deg, color-mix(in srgb, var(--bar-accent) 20%, transparent), transparent 62%),
        #101924;
    }}
    .bar-row::before {{
      content: attr(data-rank);
      width: 28px;
      height: 28px;
      border-radius: 7px;
      display: grid;
      place-items: center;
      color: var(--bar-accent);
      background: rgba(8, 13, 19, 0.92);
      border: 1px solid color-mix(in srgb, var(--bar-accent) 38%, var(--line));
      font-size: 0.7rem;
      font-weight: 900;
      font-variant-numeric: tabular-nums;
    }}
    .bar-label {{
      min-width: 0;
      display: grid;
      gap: 2px;
    }}
    .bar-label-main {{
      min-width: 0;
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 800;
    }}
    .bar-label-text {{
      display: block;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .bar-label-icon {{
      width: 30px;
      height: 30px;
      flex: 0 0 30px;
      object-fit: cover;
      border-radius: 7px;
      border: 1px solid rgba(17, 25, 35, 0.18);
      box-shadow: 0 6px 14px rgba(17, 25, 35, 0.14);
      background: #0d141d;
    }}
    .bar-label small {{
      display: block;
      padding-left: 0;
    }}
    .bar-track {{
      position: relative;
      height: 13px;
      background: #233246;
      border-radius: 999px;
      overflow: hidden;
      box-shadow: inset 0 1px 2px rgba(17, 25, 35, 0.12);
    }}
    .bar-fill {{
      height: 100%;
      background: linear-gradient(90deg, var(--bar-accent, var(--blue)), var(--green));
      border-radius: inherit;
      box-shadow: 0 0 14px color-mix(in srgb, var(--bar-accent, var(--blue)) 36%, transparent);
    }}
    .bar-fill::after {{
      content: "";
      display: block;
      width: 100%;
      height: 45%;
      border-radius: inherit;
      background: rgba(255, 255, 255, 0.22);
    }}
    .bar-row b {{
      text-align: right;
      font-variant-numeric: tabular-nums;
      color: #eef4fb;
    }}
    .combo-chart {{
      display: grid;
      gap: 8px;
      margin-top: 10px;
    }}
    .combo-comparison-stack {{
      display: grid;
      gap: 14px;
      margin-top: 14px;
    }}
    .combo-comparison-panel {{
      padding: 16px;
    }}
    .combo-comparison-heading {{
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 12px;
    }}
    .combo-compare-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
    }}
    .combo-compare-column {{
      min-width: 0;
    }}
    .combo-compare-column h4 {{
      margin: 0;
      color: var(--ink);
      font-size: 0.9rem;
      text-transform: uppercase;
      letter-spacing: 0;
    }}
    .combo-compare-best h4 {{
      color: var(--green);
    }}
    .combo-compare-worst h4 {{
      color: var(--red);
    }}
    .combo-row {{
      --bar-accent: var(--green);
      display: grid;
      grid-template-columns: 34px minmax(220px, 1.35fr) 2fr minmax(58px, auto);
      gap: 10px;
      align-items: center;
      min-height: 44px;
      padding: 7px;
      border: 1px solid color-mix(in srgb, var(--bar-accent) 30%, var(--line));
      border-radius: 8px;
      background:
        linear-gradient(90deg, color-mix(in srgb, var(--bar-accent) 19%, transparent), transparent 62%),
        #101924;
    }}
    .combo-row::before {{
      content: attr(data-rank);
      width: 28px;
      height: 28px;
      border-radius: 7px;
      display: grid;
      place-items: center;
      color: var(--bar-accent);
      background: rgba(8, 13, 19, 0.92);
      border: 1px solid color-mix(in srgb, var(--bar-accent) 42%, var(--line));
      font-size: 0.7rem;
      font-weight: 900;
      font-variant-numeric: tabular-nums;
    }}
    .combo-label {{
      min-width: 0;
    }}
    .combo-label span {{
      display: block;
      font-weight: 800;
      line-height: 1.25;
      white-space: normal;
    }}
    .combo-label small {{
      display: block;
      margin-top: 3px;
    }}
    .combo-row b {{
      text-align: right;
      font-variant-numeric: tabular-nums;
      color: #eef4fb;
    }}
    .combo-row-worst .bar-fill {{
      background: linear-gradient(90deg, var(--bar-accent, var(--red)), var(--gold));
      box-shadow: 0 0 14px color-mix(in srgb, var(--bar-accent, var(--red)) 36%, transparent);
    }}
    .chart-note {{
      margin: 6px 0 0;
      color: var(--muted);
      font-size: 0.85rem;
      font-weight: 700;
    }}
    .empty-state {{
      color: var(--muted);
      background: #f6f8fb;
      border: 1px dashed var(--line);
      border-radius: 8px;
      padding: 18px;
      font-weight: 700;
    }}
    .role-pool-browser {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
      overflow: hidden;
    }}
    .role-tabs {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      padding: 12px 16px;
      border-bottom: 1px solid var(--line);
      background: #fbfcfe;
    }}
    .role-tab {{
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #ffffff;
      color: var(--ink);
      min-height: 36px;
      padding: 8px 12px;
      font-weight: 800;
      cursor: pointer;
    }}
    .role-tab:hover {{
      background: #eef3f8;
    }}
    .role-tab.active {{
      background: #dff2ea;
      border-color: #7cc6a8;
      color: #166547;
    }}
    .role-pool-panel {{
      display: none;
      padding: 14px 16px 16px;
    }}
    .role-pool-panel.active {{
      display: block;
    }}
    .role-pool-summary {{
      display: flex;
      align-items: baseline;
      gap: 12px;
      flex-wrap: wrap;
      margin-bottom: 12px;
    }}
    .role-pool-summary strong {{
      font-size: 1.1rem;
    }}
    .role-pool-summary span {{
      font-weight: 800;
      color: var(--blue);
    }}
    .role-champion-list {{
      display: grid;
      grid-template-columns: 1fr;
      gap: 7px;
      max-height: 400px;
      overflow: auto;
      padding-right: 4px;
    }}
    .role-champion-row {{
      --bar-accent: var(--blue);
      display: grid;
      grid-template-columns: minmax(170px, 240px) 34px minmax(150px, 440px);
      align-items: center;
      gap: 8px;
      min-height: 34px;
      max-width: 760px;
      padding: 4px 7px;
      border: 1px solid rgba(151, 164, 181, 0.15);
      border-radius: 7px;
      background:
        linear-gradient(90deg, color-mix(in srgb, var(--bar-accent) 16%, transparent), transparent 62%),
        rgba(16, 25, 36, 0.62);
    }}
    .role-champion-row span {{
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      font-weight: 800;
      display: flex;
      align-items: center;
      gap: 8px;
      min-width: 0;
    }}
    .role-champion-row img {{
      width: 24px;
      height: 24px;
      flex: 0 0 24px;
      object-fit: cover;
      border-radius: 6px;
      border: 1px solid rgba(232, 238, 246, 0.16);
      background: #0d141d;
    }}
    .role-champion-row b {{
      text-align: center;
      font-variant-numeric: tabular-nums;
      color: #dce5ef;
      font-size: 0.86rem;
    }}
    .role-champion-row .bar-track {{
      height: 9px;
    }}
    .award-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 14px;
    }}
    .award-card {{
      position: relative;
      min-height: 182px;
      padding: 16px;
      display: grid;
      grid-template-columns: 70px minmax(0, 1fr);
      gap: 14px;
      align-items: start;
      overflow: hidden;
      border-color: rgba(240, 201, 106, 0.22);
      background:
        linear-gradient(135deg, rgba(240, 201, 106, 0.12), rgba(17, 25, 35, 0) 42%),
        var(--panel);
      color: inherit;
      text-decoration: none;
      transition: transform 150ms ease, border-color 150ms ease, box-shadow 150ms ease;
    }}
    .award-card::before {{
      content: "";
      position: absolute;
      inset: 0 0 auto;
      height: 3px;
      background: var(--gold);
    }}
    .award-card:hover {{
      transform: translateY(-2px);
      border-color: rgba(240, 201, 106, 0.48);
      box-shadow: 0 18px 40px rgba(0, 0, 0, 0.42);
    }}
    a.award-card {{
      cursor: pointer;
    }}
    .award-icon {{
      width: 64px;
      height: 64px;
      border-radius: 12px;
      border: 1px solid rgba(240, 201, 106, 0.34);
      background: #0d141d;
      display: grid;
      place-items: center;
      overflow: hidden;
      box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.04);
    }}
    .award-icon img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
    }}
    .award-badge {{
      color: var(--gold);
      position: relative;
      background:
        radial-gradient(circle at 50% 42%, rgba(240, 201, 106, 0.22), rgba(13, 20, 29, 0) 58%),
        #0d141d;
    }}
    .award-symbol {{
      place-items: center;
    }}
    .award-symbol-svg {{
      width: 43px;
      height: 43px;
      display: block;
      filter: drop-shadow(0 6px 14px rgba(0, 0, 0, 0.28));
    }}
    .award-copy {{
      position: relative;
      display: grid;
      gap: 6px;
      padding-right: 22px;
    }}
    .award-card strong {{
      font-size: 1.24rem;
      line-height: 1.2;
    }}
    .award-card b {{
      font-size: 1rem;
      color: var(--gold);
    }}
    .award-card small {{
      display: block;
    }}
    .award-theme-blue {{
      border-color: rgba(98, 168, 255, 0.24);
      background:
        linear-gradient(135deg, rgba(98, 168, 255, 0.13), rgba(17, 25, 35, 0) 42%),
        var(--panel);
    }}
    .award-theme-blue::before {{
      background: var(--blue);
    }}
    .award-theme-blue .award-icon {{
      border-color: rgba(98, 168, 255, 0.34);
    }}
    .award-theme-blue .award-badge,
    .award-theme-blue b {{
      color: var(--blue);
    }}
    .award-theme-green {{
      border-color: rgba(79, 196, 139, 0.24);
      background:
        linear-gradient(135deg, rgba(79, 196, 139, 0.13), rgba(17, 25, 35, 0) 42%),
        var(--panel);
    }}
    .award-theme-green::before {{
      background: var(--green);
    }}
    .award-theme-green .award-icon {{
      border-color: rgba(79, 196, 139, 0.34);
    }}
    .award-theme-green .award-badge,
    .award-theme-green b {{
      color: var(--green);
    }}
    .award-theme-red {{
      border-color: rgba(255, 111, 129, 0.24);
      background:
        linear-gradient(135deg, rgba(255, 111, 129, 0.13), rgba(17, 25, 35, 0) 42%),
        var(--panel);
    }}
    .award-theme-red::before {{
      background: var(--red);
    }}
    .award-theme-red .award-icon {{
      border-color: rgba(255, 111, 129, 0.34);
    }}
    .award-theme-red .award-badge,
    .award-theme-red b {{
      color: var(--red);
    }}
    .award-theme-violet {{
      border-color: rgba(181, 150, 255, 0.24);
      background:
        linear-gradient(135deg, rgba(181, 150, 255, 0.13), rgba(17, 25, 35, 0) 42%),
        var(--panel);
    }}
    .award-theme-violet::before {{
      background: var(--violet);
    }}
    .award-theme-violet .award-icon {{
      border-color: rgba(181, 150, 255, 0.34);
    }}
    .award-theme-violet .award-badge,
    .award-theme-violet b {{
      color: var(--violet);
    }}
    .mvp-team-grid {{
      display: grid;
      grid-template-columns: 1fr;
      gap: 16px;
    }}
    .team-builder-panel {{
      overflow: hidden;
    }}
    .team-tier-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
      padding: 14px 16px 16px;
    }}
    .team-tier-card {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #ffffff;
      overflow: hidden;
    }}
    .team-tier-heading {{
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 2px 10px;
      align-items: baseline;
      padding: 12px;
      border-bottom: 1px solid var(--line);
      background: #f7fafd;
    }}
    .team-tier-heading span {{
      font-size: 0.78rem;
      font-weight: 900;
      text-transform: uppercase;
      color: var(--blue);
    }}
    .team-tier-heading strong {{
      font-size: 1.35rem;
    }}
    .team-tier-heading small {{
      grid-column: 1 / -1;
    }}
    .tier-s .team-tier-heading {{
      background: #fff8e7;
    }}
    .tier-a .team-tier-heading {{
      background: #eef8f3;
    }}
    .tier-b .team-tier-heading {{
      background: #edf5fb;
    }}
    .tier-c .team-tier-heading {{
      background: #f4f1fb;
    }}
    .tier-d .team-tier-heading, .tier-f .team-tier-heading {{
      background: #fff0f2;
    }}
    .team-role-list {{
      display: grid;
    }}
    .team-role-row {{
      display: grid;
      grid-template-columns: 58px minmax(84px, 1fr) minmax(130px, 1.7fr) 48px;
      gap: 8px;
      align-items: center;
      padding: 9px 10px;
      border-bottom: 1px solid #edf1f5;
      font-size: 0.86rem;
    }}
    .team-role-row:nth-child(even) {{
      background: #f7fafd;
    }}
    .team-role-row:last-child {{
      border-bottom: 0;
    }}
    .team-role-row b {{
      color: var(--muted);
      font-size: 0.72rem;
    }}
    .team-role-row span {{
      font-weight: 900;
      color: var(--ink);
    }}
    .team-role-row small {{
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .team-role-row strong {{
      text-align: right;
      color: var(--green);
      font-variant-numeric: tabular-nums;
    }}
    .unused-players {{
      padding: 0 16px 16px;
    }}
    .formula-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
    }}
    .formula-example-grid {{
      display: grid;
      grid-template-columns: 1fr;
      gap: 14px;
      margin-top: 14px;
    }}
    .formula-definition-panel,
    .formula-example-panel {{
      overflow: hidden;
    }}
    .formula-list {{
      display: grid;
      gap: 10px;
      list-style: none;
      margin: 0;
      padding: 0 16px 16px;
    }}
    .formula-list li {{
      border-top: 1px solid var(--line);
      padding-top: 10px;
    }}
    .formula-list li:first-child {{
      border-top: 0;
      padding-top: 0;
    }}
    .formula-list b,
    .formula-table b,
    .formula-copy b {{
      color: var(--ink);
    }}
    .formula-list small,
    .formula-table small {{
      display: block;
      margin-top: 3px;
    }}
    .formula-copy {{
      display: grid;
      gap: 10px;
      padding: 0 16px 16px;
      color: var(--muted);
      line-height: 1.45;
    }}
    .formula-copy p {{
      margin: 0;
    }}
    .formula-table td {{
      vertical-align: top;
    }}
    .formula-table td:first-child {{
      min-width: 190px;
    }}
    .formula-total {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 14px;
      padding: 12px 16px;
      border-top: 1px solid var(--line);
      background: rgba(98, 168, 255, 0.08);
    }}
    .formula-total strong {{
      color: var(--gold);
      font-size: 1.35rem;
      font-variant-numeric: tabular-nums;
    }}
    {render_ban_planner_css()}
    .match-history-grid {{
      display: grid;
      gap: 14px;
    }}
    .match-browser, .player-pool-browser {{
      display: grid;
      grid-template-columns: auto minmax(180px, 1fr) auto minmax(220px, 1.4fr) auto;
      gap: 10px;
      align-items: center;
      margin-bottom: 14px;
    }}
    .player-pool-browser {{
      grid-template-columns: auto minmax(180px, 1fr) auto minmax(220px, 1.4fr) auto auto auto;
    }}
    .match-browser button, .match-browser select, .player-pool-browser button, .player-pool-browser select {{
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #ffffff;
      color: var(--ink);
      min-height: 38px;
      padding: 8px 10px;
      font-weight: 700;
    }}
    .match-browser button, .player-pool-browser button {{
      cursor: pointer;
    }}
    .match-browser button:hover, .player-pool-browser button:hover {{
      background: #eef3f8;
    }}
    .match-browser select, .player-pool-browser select {{
      width: 100%;
    }}
    .orientation-button.active {{
      background: #dff2ea;
      border-color: #7cc6a8;
      color: #166547;
    }}
    .match-count, .pool-count {{
      color: var(--muted);
      font-size: 0.9rem;
      font-weight: 700;
      white-space: nowrap;
    }}
    .match-card, .player-pool-card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
      overflow: hidden;
      scroll-margin-top: 76px;
    }}
    .match-card {{
      display: none;
    }}
    .match-card.active {{
      display: block;
    }}
    .search-highlight {{
      background: #ffe45c;
      color: #101820;
      border-radius: 3px;
      padding: 0 2px;
      box-shadow: 0 0 0 1px rgba(255, 228, 92, 0.5);
    }}
    .match-card-heading, .player-pool-heading {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      padding: 14px 16px;
      border-bottom: 1px solid var(--line);
      background: #fbfcfe;
    }}
    .match-card-heading h3, .player-pool-heading h3 {{
      margin: 0 0 3px;
    }}
    .match-score {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      justify-content: flex-end;
      font-weight: 800;
      font-variant-numeric: tabular-nums;
    }}
    .match-score span {{
      border-radius: 6px;
      padding: 6px 8px;
    }}
    .win-score {{
      background: #dff2ea;
      color: #166547;
    }}
    .loss-score {{
      background: #f8e3e6;
      color: #9d2837;
    }}
    .match-scoreboard {{
      min-width: 0;
    }}
    .match-scoreboard-heading {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
      align-items: stretch;
      border-bottom: 1px solid var(--line);
    }}
    .match-scoreboard-heading > div {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
      min-width: 0;
      padding: 12px 16px;
    }}
    .match-scoreboard-heading > span {{
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 0 14px;
      border-left: 1px solid var(--line);
      border-right: 1px solid var(--line);
      color: var(--muted);
      font-size: 0.72rem;
      font-weight: 900;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      white-space: nowrap;
    }}
    .match-scoreboard-heading h4 {{
      margin: 0;
      font-size: 0.9rem;
      letter-spacing: 0;
      text-transform: uppercase;
    }}
    .match-scoreboard-heading .winning-team {{
      background: #eef8f3;
      color: #166547;
    }}
    .match-scoreboard-heading .losing-team {{
      background: #fff0f2;
      color: #9d2837;
    }}
    .match-scoreboard-wrap {{
      overflow-x: auto;
    }}
    .match-scoreboard-table {{
      min-width: 1120px;
      table-layout: fixed;
      font-size: 0.86rem;
    }}
    .match-role-col {{
      width: 66px;
    }}
    .match-player-col {{
      width: 145px;
    }}
    .match-champion-col {{
      width: 145px;
    }}
    .match-score-col {{
      width: 76px;
    }}
    .match-kda-col {{
      width: 54px;
    }}
    .match-versus-col {{
      width: 42px;
    }}
    .match-scoreboard-table thead th {{
      position: static;
      padding: 8px 10px;
    }}
    .match-scoreboard-table td {{
      padding: 9px 10px;
      vertical-align: middle;
    }}
    .match-scoreboard-table th:nth-child(n+7),
    .match-scoreboard-table td:nth-child(n+7) {{
      text-align: right;
    }}
    .match-player-cell strong {{
      display: block;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .match-player-cell small {{
      display: block;
      margin-top: 2px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .match-player-cell.mirrored {{
      text-align: right;
    }}
    .match-champion-cell {{
      display: flex;
      align-items: center;
      gap: 8px;
      min-width: 0;
    }}
    .match-champion-cell img {{
      width: 30px;
      height: 30px;
      flex: 0 0 30px;
      object-fit: cover;
      border-radius: 7px;
      border: 1px solid rgba(232, 238, 246, 0.16);
      background: #0d141d;
      box-shadow: 0 6px 14px rgba(0, 0, 0, 0.16);
    }}
    .match-champion-cell span {{
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      font-weight: 800;
    }}
    .match-champion-cell.mirrored {{
      justify-content: flex-end;
    }}
    .match-champion-cell.mirrored img {{
      order: 2;
    }}
    .match-versus-cell {{
      color: var(--gold);
      font-size: 0.72rem;
      font-weight: 900;
      letter-spacing: 0.04em;
      text-align: center;
      text-transform: uppercase;
    }}
    .match-score-cell,
    .match-kda-cell {{
      white-space: nowrap;
      overflow-wrap: normal;
      word-break: normal;
      text-align: right;
      font-weight: 800;
      font-variant-numeric: tabular-nums;
    }}
    .role-pill {{
      display: inline-flex;
      min-width: 58px;
      justify-content: center;
      border-radius: 6px;
      background: #eef3f8;
      padding: 4px 6px;
      font-size: 0.74rem;
      font-weight: 800;
    }}
    .player-pool-grid {{
      display: grid;
      gap: 14px;
    }}
    .player-pool-card {{
      display: none;
    }}
    .player-pool-card.active {{
      display: block;
    }}
    .champ-pool-chart {{
      padding: 10px 14px 12px;
      overflow-x: hidden;
      background: #ffffff;
    }}
    .champ-pool-svg {{
      width: 100%;
      min-width: 0;
      height: auto;
      display: block;
    }}
    .vertical-chart-wrap {{
      display: none;
      overflow-x: hidden;
    }}
    .pool-orientation-vertical .horizontal-chart {{
      display: none;
    }}
    .pool-orientation-vertical .vertical-chart-wrap {{
      display: block;
    }}
    .pool-track {{
      fill: #dfe7f1;
    }}
    .pool-bar {{
      fill: #62a8ff;
      filter: drop-shadow(0 1px 3px rgba(23, 33, 43, 0.16));
    }}
    .pool-icon-frame {{
      fill: #ffffff;
      stroke: #c9d6e5;
      stroke-width: 1;
    }}
    .pool-row image {{
      image-rendering: auto;
    }}
    .pool-axis-label {{
      fill: var(--muted);
      font-size: 12px;
      font-weight: 800;
    }}
    .pool-axis-label-right {{
      text-anchor: end;
    }}
    .pool-label {{
      fill: #17212b;
      font-size: 12.5px;
      font-weight: 800;
    }}
    .horizontal-label {{
      text-anchor: end;
    }}
    .vertical-label {{
      text-anchor: start;
      font-size: 11px;
    }}
    .pool-value, .pool-winrate {{
      fill: #334253;
      font-size: 12px;
      font-weight: 800;
      font-variant-numeric: tabular-nums;
    }}
    .pool-winrate {{
      text-anchor: end;
    }}
    .pool-value.centered {{
      text-anchor: middle;
    }}
    .section-heading {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      padding: 14px 16px;
      border-bottom: 1px solid var(--line);
    }}
    .table-search {{
      width: min(280px, 45vw);
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 8px 10px;
      color: var(--ink);
      background: #fbfcfe;
    }}
    .table-controls {{
      display: flex;
      align-items: center;
      justify-content: flex-end;
      gap: 8px;
      flex-wrap: wrap;
    }}
    .table-role-filter {{
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 8px 10px;
      min-height: 37px;
      color: var(--ink);
      background: #fbfcfe;
      font-weight: 700;
    }}
    .card-search {{
      width: min(340px, 100%);
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 9px 10px;
      color: var(--ink);
      background: #fbfcfe;
    }}
    .table-wrap {{
      overflow-y: auto;
      overflow-x: auto;
      max-height: 620px;
      min-width: 0;
    }}
    table {{
      width: 100%;
      max-width: 100%;
      min-width: 860px;
      border-collapse: collapse;
      font-size: 0.91rem;
      table-layout: auto;
    }}
    th, td {{
      padding: 9px 10px;
      border-bottom: 1px solid #d8e0e8;
      text-align: left;
      vertical-align: top;
      white-space: normal;
      overflow-wrap: normal;
      word-break: normal;
    }}
    th + th, td + td {{
      border-left: 1px solid #edf1f5;
    }}
    tbody tr:nth-child(even) td {{
      background: #f7fafd;
    }}
    tbody tr:nth-child(even) th {{
      background: #f7fafd;
    }}
    tbody tr:nth-child(odd) td {{
      background: #ffffff;
    }}
    tbody tr:nth-child(odd) th {{
      background: #ffffff;
    }}
    td {{
      color: #273443;
      font-variant-numeric: tabular-nums;
    }}
    td.name-cell,
    td.mvp-name-cell {{
      min-width: 12ch;
      white-space: nowrap;
      overflow-wrap: normal;
      word-break: normal;
    }}
    td.number-cell {{
      white-space: nowrap;
      overflow-wrap: normal;
      word-break: normal;
    }}
    #player-summary {{
      min-width: 1280px;
    }}
    thead th {{
      position: sticky;
      top: 0;
      z-index: 2;
      background: #e8eff6;
      color: #334253;
      font-size: 0.78rem;
      text-transform: uppercase;
      cursor: pointer;
      border-bottom-color: #c9d4df;
      overflow-wrap: normal;
    }}
    tbody tr:hover td, tbody tr:hover th {{
      background: #edf5fb;
    }}
    th.sorted-asc::after {{ content: " ^"; }}
    th.sorted-desc::after {{ content: " v"; }}
    .tables-grid {{
      display: grid;
      grid-template-columns: 1fr;
      gap: 16px;
    }}
    .heatmap-panel .table-wrap {{
      overflow-x: hidden;
    }}
    .heatmap-table {{
      width: 100%;
      table-layout: fixed;
    }}
    .heatmap-table th, .heatmap-table td {{
      padding: 8px 8px;
    }}
    .heatmap-table th:first-child {{
      width: 150px;
      min-width: 0;
      max-width: none;
    }}
    .heatmap-table tbody th {{
      position: sticky;
      left: 0;
      z-index: 1;
    }}
    .heatmap-table tbody tr:nth-child(even) th {{
      background: #f7fafd;
    }}
    .heatmap-table tbody tr:nth-child(odd) th {{
      background: #ffffff;
    }}
    .heatmap-table th small {{
      display: block;
      text-transform: none;
      font-weight: 600;
      margin-top: 3px;
    }}
    .heatmap-table td {{
      width: auto;
      min-width: 0;
      text-align: center;
      font-weight: 800;
    }}
    .heatmap-table td small {{
      display: block;
      color: currentColor;
      opacity: 0.8;
      margin-top: 2px;
    }}
    .heatmap-table .empty-cell {{
      background: #f0f3f6;
      color: #9aa6b2;
      font-weight: 700;
    }}
    .svg-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
      margin-top: 14px;
    }}
    .svg-grid.single {{
      grid-template-columns: 1fr;
    }}
    svg {{
      width: 100%;
      height: auto;
      display: block;
    }}
    .svg-axis {{
      stroke: #c8d2de;
      stroke-width: 2;
    }}
    .svg-role-bar {{
      fill: var(--blue);
    }}
    .svg-value {{
      text-anchor: middle;
      fill: #17212b;
      font-size: 18px;
      font-weight: 800;
    }}
    .svg-label {{
      text-anchor: middle;
      fill: #17212b;
      font-size: 17px;
      font-weight: 800;
    }}
    .svg-sub {{
      fill: var(--muted);
      font-size: 14px;
      font-weight: 700;
    }}
    .svg-sub.end {{
      text-anchor: end;
    }}
    .svg-line {{
      fill: none;
      stroke: var(--green);
      stroke-width: 4;
      stroke-linejoin: round;
      stroke-linecap: round;
    }}
    .svg-dot {{
      fill: #ffffff;
      stroke: var(--green);
      stroke-width: 3;
    }}
    header {{
      background: #0a1018;
    }}
    header p {{
      color: #aebdcc;
    }}
    .generated {{
      color: #101820;
      background: var(--gold);
    }}
    nav {{
      background: #0f1721;
    }}
    nav a:hover {{
      background: #1a2633;
    }}
    .champion-chip, .role-pill {{
      background: #172331;
      color: var(--ink);
    }}
    .bar-track {{
      background: #243142;
    }}
    .empty-state {{
      background: #111923;
    }}
    .role-tabs, .match-card-heading, .player-pool-heading {{
      background: #131d29;
    }}
    .role-tab,
    .match-browser button,
    .match-browser select,
    .player-pool-browser button,
    .player-pool-browser select,
    .table-search,
    .table-role-filter,
    .card-search {{
      background: #0d141d;
      color: var(--ink);
      border-color: var(--line);
    }}
    .role-tab:hover,
    .match-browser button:hover,
    .player-pool-browser button:hover {{
      background: #1a2633;
    }}
    .role-tab.active,
    .orientation-button.active {{
      background: rgba(79, 196, 139, 0.16);
      border-color: #3fa477;
      color: #8ee1b8;
    }}
    .team-tier-card {{
      background: #0d141d;
    }}
    .team-tier-heading {{
      background: #162231;
    }}
    .tier-s .team-tier-heading {{
      background: rgba(240, 201, 106, 0.16);
    }}
    .tier-a .team-tier-heading {{
      background: rgba(79, 196, 139, 0.14);
    }}
    .tier-b .team-tier-heading {{
      background: rgba(98, 168, 255, 0.14);
    }}
    .tier-c .team-tier-heading {{
      background: rgba(181, 150, 255, 0.14);
    }}
    .tier-d .team-tier-heading,
    .tier-f .team-tier-heading {{
      background: rgba(255, 111, 129, 0.14);
    }}
    .team-role-row {{
      border-bottom-color: #202b39;
    }}
    .team-role-row:nth-child(even) {{
      background: #131d29;
    }}
    .win-score,
    .match-scoreboard-heading .winning-team {{
      background: rgba(79, 196, 139, 0.16);
      color: #8ee1b8;
    }}
    .loss-score,
    .match-scoreboard-heading .losing-team {{
      background: rgba(255, 111, 129, 0.14);
      color: #ff9aa7;
    }}
    .champ-pool-chart {{
      background: var(--panel);
    }}
    .pool-track {{
      fill: #243142;
    }}
    .pool-icon-frame {{
      fill: #172231;
      stroke: #344255;
    }}
    .pool-label,
    .pool-value,
    .pool-winrate,
    .svg-value,
    .svg-label {{
      fill: var(--ink);
    }}
    th, td {{
      border-bottom-color: #263241;
    }}
    th + th,
    td + td {{
      border-left-color: #1d2836;
    }}
    tbody tr:nth-child(even) td,
    tbody tr:nth-child(even) th,
    .heatmap-table tbody tr:nth-child(even) th {{
      background: #131d29;
    }}
    tbody tr:nth-child(odd) td,
    tbody tr:nth-child(odd) th,
    .heatmap-table tbody tr:nth-child(odd) th {{
      background: #0f1721;
    }}
    td {{
      color: #dce5ef;
    }}
    thead th {{
      background: #1a2633;
      color: #c7d4e2;
      border-bottom-color: #344255;
    }}
    tbody tr:hover td,
    tbody tr:hover th {{
      background: #1b2a3a;
    }}
    tbody tr td.table-heat-cell {{
      border-color: rgba(255, 255, 255, 0.14);
      text-shadow: 0 1px 1px rgba(0, 0, 0, 0.18);
    }}
    tbody tr:hover td.table-heat-cell {{
      filter: brightness(1.06);
    }}
    td.mvp-name-cell {{
      background: linear-gradient(90deg, rgba(240, 201, 106, 0.10), rgba(98, 168, 255, 0.04));
    }}
    .heatmap-table .empty-cell {{
      background: #17212d;
      color: #7f8d9c;
    }}
    .svg-axis {{
      stroke: #344255;
    }}
    .svg-dot {{
      fill: var(--panel);
    }}
    @media (max-width: 1040px) {{
      .metric-grid {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
      .chart-grid, .svg-grid, .award-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .mvp-team-grid {{ grid-template-columns: 1fr; }}
      .player-pool-browser {{ grid-template-columns: auto minmax(160px, 1fr) auto; }}
      .player-pool-browser .card-search, .player-pool-browser .pool-count {{ grid-column: 1 / -1; }}
      .topline {{ flex-direction: column; }}
      .header-actions {{ justify-items: start; }}
      .refresh-data-note, .refresh-data-status {{ text-align: left; }}
    }}
    @media (max-width: 720px) {{
      header {{ padding: 22px 16px 18px; }}
      nav {{ padding: 10px 16px; }}
      main {{ padding: 16px; }}
      .metric-grid, .chart-grid, .svg-grid, .award-grid, .team-tier-grid, .formula-grid {{ grid-template-columns: 1fr; }}
      .combo-compare-grid {{ grid-template-columns: 1fr; }}
      .combo-comparison-heading {{ align-items: flex-start; flex-direction: column; }}
      .popular-champion-row {{ grid-template-columns: repeat(5, minmax(0, 1fr)); }}
      .match-card-heading, .player-pool-heading {{ align-items: flex-start; flex-direction: column; }}
      .match-browser {{ grid-template-columns: 1fr 1fr; }}
      .match-browser select, .match-browser .card-search, .match-count {{ grid-column: 1 / -1; }}
      .player-pool-browser {{ grid-template-columns: 1fr 1fr; }}
      .player-pool-browser select, .player-pool-browser .card-search, .pool-count {{ grid-column: 1 / -1; }}
      .match-scoreboard-heading {{ grid-template-columns: 1fr; }}
      .match-scoreboard-heading > span {{ min-height: 34px; border-left: 0; border-right: 0; }}
      .bar-row {{ grid-template-columns: 34px minmax(0, 1fr) auto; gap: 8px; }}
      .bar-row::before {{ grid-column: 1; grid-row: 1; }}
      .bar-label {{ grid-column: 2; grid-row: 1; }}
      .bar-track {{ grid-column: 1 / -1; grid-row: 2; }}
      .bar-row b {{ grid-column: 3; grid-row: 1; text-align: right; }}
      .combo-row {{ grid-template-columns: 34px minmax(0, 1fr) auto; gap: 8px; }}
      .combo-row::before {{ grid-column: 1; grid-row: 1; }}
      .combo-label {{ grid-column: 2; grid-row: 1; }}
      .combo-row .bar-track {{ grid-column: 1 / -1; grid-row: 2; }}
      .combo-row b {{ grid-column: 3; grid-row: 1; text-align: right; }}
      .role-champion-list {{ grid-template-columns: 1fr; }}
      .role-champion-row {{ grid-template-columns: minmax(120px, 1fr) 34px minmax(100px, 1.6fr); max-width: none; }}
      .team-role-row {{ grid-template-columns: 48px minmax(84px, 1fr) 42px; }}
      .team-role-row small {{ grid-column: 2 / -1; }}
      .heatmap-panel .table-wrap {{ overflow-x: hidden; }}
      .heatmap-table th, .heatmap-table td {{ padding: 6px 6px; }}
      .heatmap-table th:first-child {{ width: 90px; min-width: 0; max-width: none; }}
      .heatmap-table td {{ width: auto; min-width: 0; font-size: 0.72rem; }}
      .heatmap-table td small {{ font-size: 0.68rem; }}
      .section-heading {{ align-items: stretch; flex-direction: column; }}
      .table-controls {{ justify-content: stretch; }}
      .table-role-filter {{ width: 100%; }}
      .table-search {{ width: 100%; }}
      table {{ table-layout: fixed; font-size: 0.76rem; }}
      th, td {{ padding: 6px 5px; }}
    }}
  </style>
</head>
<body>
  {render_hidden_head_to_head_link(head_to_head_page_name)}
  <header>
    <div class="topline">
      <div>
        <h1>LoL Customs Dashboard</h1>
        <p>{len(matches)} matches, {len(player_rows)} players, and {len(champion_rows)} champions. Stats are aggregated by real name, not summoner name.</p>
      </div>
      {render_refresh_control(generated_at)}
    </div>
  </header>
  <nav>
    <a href="#overview">Overview</a>
    <a href="#awards">Awards</a>
    <a href="#match-history">Matches</a>
    <a href="#players">Players</a>
    <a href="#champion-pools">Champion Pools</a>
    <a href="#champions">Champions</a>
    <a href="#role-pools">Role Pools</a>
    <a href="#combos">Combos</a>
    <a href="{html_attr(teams_page_name)}#teams">Teams</a>
    <a href="{html_attr(draft_coach_page_name)}#draft-coach">Draft Coach</a>
    <a href="{html_attr(showcases_page_name)}">Showcases</a>
    <a href="{html_attr(experimental_page_name)}#custom-meta">Experimental</a>
    <a href="#deep-dive">Deep Dive</a>
  </nav>
  <main>
    <section id="overview" class="section">
      <div class="section-title">
        <h2>Overview</h2>
        <p class="note">Dates are mapped from UTC timestamps into {LOCAL_TZ_NAME}. KDA ratio uses (kills + assists) / deaths, with zero deaths counted as one for aggregate ratios.</p>
      </div>
      <div class="metric-grid">{metric_cards}</div>
      {render_popular_champions_strip(popular_champion_strip_rows)}
      <section id="awards" class="section">
        <div class="section-title">
          <h2>Award Ceremony</h2>
          <p class="note">Regular-player awards use at least {MIN_PLAYER_GAMES} games where possible; pocket-pick awards use at least {MIN_COMBO_GAMES} games.</p>
        </div>
        <div class="award-grid">{render_awards(awards)}</div>
      </section>
      <div class="chart-grid">
        {render_bar_chart(f"Top Player Win Rate ({WINRATE_CHART_MIN_GAMES}+ Games)", top_player_chart_rows, "name", "winrate", pct, limit=10, max_value=1.0, footer_key="games", footer_formatter=lambda value: f"{integer(value)} games")}
        {render_bar_chart(f"Bottom Player Win Rate ({WINRATE_CHART_MIN_GAMES}+ Games)", bottom_player_chart_rows, "name", "winrate", pct, limit=10, max_value=1.0, footer_key="games", footer_formatter=lambda value: f"{integer(value)} games")}
        {render_bar_chart("Player KDA", top_kda_chart_rows, "name", "kda_ratio", two_decimal, limit=10, footer_key="games", footer_formatter=lambda value: f"{integer(value)} games")}
        {render_bar_chart("Most Played Champions", most_played_champion_rows, "champion", "games", integer, limit=10, footer_key="winrate", footer_formatter=lambda value: f"{pct(float(value))} WR")}
        {render_bar_chart("Top Champion Win Rate", top_champion_winrate_rows, "champion", "winrate", pct, limit=10, max_value=1.0, footer_key="games", footer_formatter=lambda value: f"{integer(value)} games")}
        {render_bar_chart("Bottom Champion Win Rate", bottom_champion_winrate_rows, "champion", "winrate", pct, limit=10, max_value=1.0, footer_key="games", footer_formatter=lambda value: f"{integer(value)} games")}
        {render_bar_chart("Match Volume By Weekday", weekday_rows, "weekday", "games", integer, limit=7, footer_key="share", footer_formatter=lambda value: f"{pct(float(value))} of matches")}
        {render_unplayed_champions_panel(unplayed_champions)}
      </div>
    </section>

    <section id="match-history" class="section">
      <div class="section-title">
        <div>
          <h2>Match History</h2>
          <p class="note">Browse one recreated match at a time. Search by match number, player, champion, role, or date.</p>
        </div>
      </div>
      <div class="match-browser">
        <button type="button" data-match-prev aria-label="Previous match" title="Previous match">&larr;</button>
        <select id="match-picker" aria-label="Select match"></select>
        <button type="button" data-match-next aria-label="Next match" title="Next match">&rarr;</button>
        <input class="card-search" type="search" placeholder="Search matches" data-match-search>
        <span class="match-count" data-match-count></span>
      </div>
      <div class="match-history-grid" data-card-container="match-history">
        {render_match_history(appearances)}
      </div>
    </section>

    <section id="players" class="section tables-grid">
      <div class="section-title"><h2>Players</h2></div>
      {render_player_role_heatmap(display_player_rows, display_player_role_rows)}
      {render_table("player-summary", "Player Summary", display_player_rows, player_columns)}
      {render_table("player-role", "Player Performance By Role", role_score_rows, player_role_columns)}
    </section>

    <section id="champion-pools" class="section">
      <div class="section-title">
        <div>
          <h2>Player Champion Pools</h2>
          <p class="note">Browse one player at a time. Unique-pick rate is unique champions divided by games, so champion pool depth is not just raw volume.</p>
        </div>
      </div>
      <div class="player-pool-browser">
        <button type="button" data-pool-prev aria-label="Previous player champion pool" title="Previous player champion pool">&larr;</button>
        <select id="player-pool-picker" aria-label="Select player champion pool"></select>
        <button type="button" data-pool-next aria-label="Next player champion pool" title="Next player champion pool">&rarr;</button>
        <input class="card-search" type="search" placeholder="Search players or champions" data-pool-search>
        <span class="pool-count" data-pool-count></span>
        <button type="button" class="orientation-button active" data-pool-orientation="horizontal">Horizontal</button>
        <button type="button" class="orientation-button" data-pool-orientation="vertical">Vertical</button>
      </div>
      <div class="player-pool-grid pool-orientation-horizontal" data-card-container="champion-pools">
        {render_player_champion_pools(display_player_rows, display_player_champion_rows)}
      </div>
    </section>

    <section id="champions" class="section tables-grid">
      <div class="section-title"><h2>Champions</h2></div>
      {render_champion_role_heatmap(champion_rows, champion_role_rows)}
      {render_table("champion-summary", "Champion Summary", champion_winrate_rows, champion_columns)}
      {render_table("champion-role", "Champion Role Detail", champion_role_rows, champion_role_columns)}
    </section>

    <section id="role-pools" class="section tables-grid">
      <div class="section-title">
        <div>
          <h2>Role Champion Pools</h2>
          <p class="note">Champion diversity by role, plus each player's unique champion pool within each role. Unique-pick rate compares variety against games played.</p>
        </div>
      </div>
      <div class="chart-grid single">
        {render_bar_chart("Unique Champions By Role", role_champion_pool, "role", "unique_champions", integer, limit=5, footer_key="matches", footer_formatter=lambda value: f"{integer(value)} matches", class_name="compact-bar-chart")}
      </div>
      {render_role_champion_browser(role_champion_pool)}
      {render_table("player-role-champion-pools", "Player Unique Champions By Role", display_player_role_champion_pool, player_role_pool_columns, controls_html=role_filter_control("player-role-champion-pools"))}
    </section>

    <section id="combos" class="section">
      <div class="section-title">
        <div>
          <h2>Best / Worst Player Combos</h2>
          <p class="note">Same-side real-name combinations. Best ranks by highest winrate; worst ranks by lowest winrate. Minimum samples: duos {TEAM_COMBO_MIN_GAMES[2]} games, trios {TEAM_COMBO_MIN_GAMES[3]}, fours {TEAM_COMBO_MIN_GAMES[4]}, fives {TEAM_COMBO_MIN_GAMES[5]}.</p>
        </div>
      </div>
      <div class="combo-comparison-stack">
        {render_combo_comparison("Duos", duo_rows, TEAM_COMBO_MIN_GAMES[2])}
        {render_combo_comparison("Trios", trio_rows, TEAM_COMBO_MIN_GAMES[3])}
        {render_combo_comparison("Fours", four_rows, TEAM_COMBO_MIN_GAMES[4])}
        {render_combo_comparison("Fives", five_rows, TEAM_COMBO_MIN_GAMES[5])}
      </div>
    </section>

    <section id="deep-dive" class="section tables-grid">
      <div class="section-title">
        <h2>Player Champion Deep Dive</h2>
        <p class="note">Use the filters to find any player, champion, or role combination.</p>
      </div>
      {render_table("player-champion", "Player Champion Summary", display_player_champion_rows, [column for column in player_champion_role_columns if column[1] != "role"])}
      {render_table("player-champion-role", "Player Champion Role Summary", display_player_champion_role_rows, player_champion_role_columns)}
    </section>
  </main>
  <script>
    function compareCells(a, b, type, direction) {{
      const av = a?.dataset.sort || a?.textContent || "";
      const bv = b?.dataset.sort || b?.textContent || "";
      let result;
      if (type === "number") {{
        const aNumber = Number(av);
        const bNumber = Number(bv);
        result = Number.isFinite(aNumber) && Number.isFinite(bNumber)
          ? aNumber - bNumber
          : av.localeCompare(bv, undefined, {{ numeric: true, sensitivity: "base" }});
      }} else {{
        result = av.localeCompare(bv, undefined, {{ numeric: true, sensitivity: "base" }});
      }}
      return direction === "asc" ? result : -result;
    }}

    document.querySelectorAll(".sortable-table th").forEach(th => {{
      th.addEventListener("click", () => {{
        const table = th.closest("table");
        const tbody = table.querySelector("tbody");
        const index = Array.from(th.parentElement.children).indexOf(th);
        const currentDirection = th.classList.contains("sorted-asc") ? "asc" : "desc";
        const nextDirection = currentDirection === "asc" ? "desc" : "asc";
        table.querySelectorAll("th").forEach(header => header.classList.remove("sorted-asc", "sorted-desc"));
        th.classList.add(nextDirection === "asc" ? "sorted-asc" : "sorted-desc");
        const rows = Array.from(tbody.querySelectorAll("tr"));
        rows.sort((left, right) => compareCells(left.children[index], right.children[index], th.dataset.type, nextDirection));
        rows.forEach(row => tbody.appendChild(row));
      }});
    }});

    function applyTableFilters(tableId) {{
      const table = document.getElementById(tableId);
      if (!table) return;
      const textInput = document.querySelector(`[data-table-filter="${{tableId}}"]`);
      const roleSelect = document.querySelector(`[data-role-filter="${{tableId}}"]`);
      const term = textInput ? textInput.value.toLowerCase().trim() : "";
      const role = roleSelect ? roleSelect.value : "";
      const headers = Array.from(table.querySelectorAll("thead th")).map(th => th.textContent.trim().toLowerCase());
      const roleIndex = headers.indexOf("role");

      table.querySelectorAll("tbody tr").forEach(row => {{
        const textMatches = !term || row.textContent.toLowerCase().includes(term);
        const roleMatches = !role || (roleIndex >= 0 && row.children[roleIndex].textContent.trim() === role);
        row.style.display = textMatches && roleMatches ? "" : "none";
      }});
    }}

    document.querySelectorAll("[data-table-filter]").forEach(input => {{
      input.addEventListener("input", () => applyTableFilters(input.dataset.tableFilter));
    }});

    document.querySelectorAll("[data-role-filter]").forEach(select => {{
      select.addEventListener("change", () => applyTableFilters(select.dataset.roleFilter));
    }});

    const matchCards = Array.from(document.querySelectorAll(".match-card"));
    const matchPicker = document.getElementById("match-picker");
    const matchSearch = document.querySelector("[data-match-search]");
    const matchCount = document.querySelector("[data-match-count]");
    const previousMatchButton = document.querySelector("[data-match-prev]");
    const nextMatchButton = document.querySelector("[data-match-next]");

    if (matchCards.length && matchPicker) {{
      let filteredMatchCards = [...matchCards];

      function escapeRegExp(value) {{
        const specials = new Set([92, 94, 36, 42, 43, 63, 46, 40, 41, 124, 123, 125, 91, 93]);
        return Array.from(value)
          .map(char => specials.has(char.charCodeAt(0)) ? `\\\\${{char}}` : char)
          .join("");
      }}

      function clearMatchHighlights(card) {{
        card.querySelectorAll("mark.search-highlight").forEach(mark => {{
          const parent = mark.parentNode;
          if (!parent) return;
          parent.replaceChild(document.createTextNode(mark.textContent), mark);
          parent.normalize();
        }});
      }}

      function matchHighlightTerms() {{
        const rawTerm = matchSearch ? matchSearch.value.trim() : "";
        return Array.from(new Set(
          rawTerm
            .split(/\\s+/)
            .map(value => value.trim())
            .filter(value => value.length > 1 || /^\\d+$/.test(value))
        )).sort((a, b) => b.length - a.length);
      }}

      function highlightMatchCard(card) {{
        const terms = matchHighlightTerms();
        if (!terms.length) return;
        const termPattern = new RegExp(`(${{terms.map(escapeRegExp).join("|")}})`, "gi");
        const lowerTerms = terms.map(value => value.toLowerCase());
        const walker = document.createTreeWalker(card, NodeFilter.SHOW_TEXT, {{
          acceptNode(node) {{
            const parent = node.parentElement;
            if (!parent || parent.closest("script, style, mark")) {{
              return NodeFilter.FILTER_REJECT;
            }}
            termPattern.lastIndex = 0;
            return node.nodeValue && termPattern.test(node.nodeValue)
              ? NodeFilter.FILTER_ACCEPT
              : NodeFilter.FILTER_REJECT;
          }}
        }});
        const nodes = [];
        let node = walker.nextNode();
        while (node) {{
          nodes.push(node);
          node = walker.nextNode();
        }}
        nodes.forEach(textNode => {{
          const fragment = document.createDocumentFragment();
          textNode.nodeValue.split(termPattern).forEach(part => {{
            if (!part) return;
            if (lowerTerms.includes(part.toLowerCase())) {{
              const mark = document.createElement("mark");
              mark.className = "search-highlight";
              mark.textContent = part;
              fragment.appendChild(mark);
            }} else {{
              fragment.appendChild(document.createTextNode(part));
            }}
          }});
          textNode.parentNode.replaceChild(fragment, textNode);
        }});
      }}

      function updateMatchHighlights() {{
        matchCards.forEach(clearMatchHighlights);
        const active = document.querySelector(".match-card.active");
        if (active) {{
          highlightMatchCard(active);
        }}
      }}

      function selectedMatchId() {{
        const active = document.querySelector(".match-card.active");
        return active ? active.dataset.matchId : matchCards[matchCards.length - 1].dataset.matchId;
      }}

      function showMatch(matchId, updateHash = false) {{
        matchCards.forEach(card => {{
          card.classList.toggle("active", card.dataset.matchId === String(matchId));
        }});
        matchPicker.value = String(matchId);
        updateMatchHighlights();
        if (updateHash) {{
          history.replaceState(null, "", `#match-${{matchId}}`);
        }}
      }}

      function matchIdFromHash() {{
        const hashMatch = window.location.hash.match(/^#match-(\\d+)$/);
        return hashMatch ? hashMatch[1] : "";
      }}

      function rebuildMatchPicker(preferredMatchId = selectedMatchId()) {{
        const term = matchSearch ? matchSearch.value.toLowerCase().trim() : "";
        filteredMatchCards = matchCards.filter(card => card.dataset.cardText.toLowerCase().includes(term));
        matchPicker.innerHTML = "";
        filteredMatchCards.forEach(card => {{
          const option = document.createElement("option");
          option.value = card.dataset.matchId;
          option.textContent = card.dataset.matchLabel;
          matchPicker.appendChild(option);
        }});

        if (matchCount) {{
          const suffix = filteredMatchCards.length === 1 ? "match" : "matches";
          matchCount.textContent = `${{filteredMatchCards.length}} ${{suffix}}`;
        }}

        if (!filteredMatchCards.length) {{
          matchCards.forEach(card => card.classList.remove("active"));
          updateMatchHighlights();
          return;
        }}

        const preferred = filteredMatchCards.find(card => card.dataset.matchId === String(preferredMatchId));
        showMatch((preferred || filteredMatchCards[0]).dataset.matchId);
      }}

      function activateLinkedMatch(matchId, scrollToHistory = false) {{
        const target = matchCards.find(card => card.dataset.matchId === String(matchId));
        if (!target) return false;
        if (matchSearch) {{
          matchSearch.value = "";
        }}
        rebuildMatchPicker(matchId);
        showMatch(matchId);
        if (scrollToHistory) {{
          document.getElementById("match-history")?.scrollIntoView({{ behavior: "smooth", block: "start" }});
        }}
        return true;
      }}

      function stepMatch(offset) {{
        if (!filteredMatchCards.length) return;
        const currentId = selectedMatchId();
        const currentIndex = Math.max(0, filteredMatchCards.findIndex(card => card.dataset.matchId === currentId));
        const nextIndex = (currentIndex + offset + filteredMatchCards.length) % filteredMatchCards.length;
        showMatch(filteredMatchCards[nextIndex].dataset.matchId, true);
      }}

      matchPicker.addEventListener("change", () => showMatch(matchPicker.value, true));
      if (matchSearch) {{
        matchSearch.addEventListener("input", () => rebuildMatchPicker());
      }}
      if (previousMatchButton) {{
        previousMatchButton.addEventListener("click", () => stepMatch(-1));
      }}
      if (nextMatchButton) {{
        nextMatchButton.addEventListener("click", () => stepMatch(1));
      }}

      document.querySelectorAll("[data-award-match-id]").forEach(link => {{
        link.addEventListener("click", event => {{
          const matchId = link.dataset.awardMatchId;
          if (!activateLinkedMatch(matchId, true)) return;
          event.preventDefault();
          history.replaceState(null, "", `#match-${{matchId}}`);
        }});
      }});

      window.addEventListener("hashchange", () => {{
        const hashMatchId = matchIdFromHash();
        if (hashMatchId) {{
          activateLinkedMatch(hashMatchId, true);
        }}
      }});

      const initialMatchId = matchIdFromHash() || matchCards[matchCards.length - 1].dataset.matchId;
      rebuildMatchPicker(initialMatchId);
    }}

    const poolCards = Array.from(document.querySelectorAll(".player-pool-card"));
    const poolPicker = document.getElementById("player-pool-picker");
    const poolSearch = document.querySelector("[data-pool-search]");
    const poolCount = document.querySelector("[data-pool-count]");
    const previousPoolButton = document.querySelector("[data-pool-prev]");
    const nextPoolButton = document.querySelector("[data-pool-next]");
    const poolContainer = document.querySelector("[data-card-container='champion-pools']");
    const orientationButtons = Array.from(document.querySelectorAll("[data-pool-orientation]"));

    if (poolCards.length && poolPicker) {{
      let filteredPoolCards = [...poolCards];

      function selectedPoolId() {{
        const active = document.querySelector(".player-pool-card.active");
        return active ? active.dataset.playerPoolId : poolCards[0].dataset.playerPoolId;
      }}

      function showPool(poolId) {{
        poolCards.forEach(card => {{
          card.classList.toggle("active", card.dataset.playerPoolId === String(poolId));
        }});
        poolPicker.value = String(poolId);
      }}

      function rebuildPoolPicker(preferredPoolId = selectedPoolId()) {{
        const term = poolSearch ? poolSearch.value.toLowerCase().trim() : "";
        filteredPoolCards = poolCards.filter(card => card.dataset.cardText.toLowerCase().includes(term));
        poolPicker.innerHTML = "";
        filteredPoolCards.forEach(card => {{
          const option = document.createElement("option");
          option.value = card.dataset.playerPoolId;
          option.textContent = card.dataset.playerPoolLabel;
          poolPicker.appendChild(option);
        }});

        if (poolCount) {{
          const suffix = filteredPoolCards.length === 1 ? "player" : "players";
          poolCount.textContent = `${{filteredPoolCards.length}} ${{suffix}}`;
        }}

        if (!filteredPoolCards.length) {{
          poolCards.forEach(card => card.classList.remove("active"));
          return;
        }}

        const preferred = filteredPoolCards.find(card => card.dataset.playerPoolId === String(preferredPoolId));
        showPool((preferred || filteredPoolCards[0]).dataset.playerPoolId);
      }}

      function stepPool(offset) {{
        if (!filteredPoolCards.length) return;
        const currentId = selectedPoolId();
        const currentIndex = Math.max(0, filteredPoolCards.findIndex(card => card.dataset.playerPoolId === currentId));
        const nextIndex = (currentIndex + offset + filteredPoolCards.length) % filteredPoolCards.length;
        showPool(filteredPoolCards[nextIndex].dataset.playerPoolId);
      }}

      poolPicker.addEventListener("change", () => showPool(poolPicker.value));
      if (poolSearch) {{
        poolSearch.addEventListener("input", () => rebuildPoolPicker());
      }}
      if (previousPoolButton) {{
        previousPoolButton.addEventListener("click", () => stepPool(-1));
      }}
      if (nextPoolButton) {{
        nextPoolButton.addEventListener("click", () => stepPool(1));
      }}
      orientationButtons.forEach(button => {{
        button.addEventListener("click", () => {{
          const orientation = button.dataset.poolOrientation;
          orientationButtons.forEach(item => item.classList.toggle("active", item === button));
          if (poolContainer) {{
            poolContainer.classList.toggle("pool-orientation-vertical", orientation === "vertical");
            poolContainer.classList.toggle("pool-orientation-horizontal", orientation === "horizontal");
          }}
        }});
      }});

      rebuildPoolPicker(poolCards[0].dataset.playerPoolId);
    }}

    document.querySelectorAll("[data-role-tab]").forEach(button => {{
      button.addEventListener("click", () => {{
        const role = button.dataset.roleTab;
        document.querySelectorAll("[data-role-tab]").forEach(tab => {{
          tab.classList.toggle("active", tab === button);
        }});
        document.querySelectorAll("[data-role-panel]").forEach(panel => {{
          panel.classList.toggle("active", panel.dataset.rolePanel === role);
        }});
      }});
    }});

    document.querySelectorAll("[data-card-filter]").forEach(input => {{
      input.addEventListener("input", () => {{
        const container = document.querySelector(`[data-card-container="${{input.dataset.cardFilter}}"]`);
        const term = input.value.toLowerCase().trim();
        container.querySelectorAll("[data-card-text]").forEach(card => {{
          card.style.display = card.dataset.cardText.toLowerCase().includes(term) ? "" : "none";
        }});
      }});
    }});
    {render_refresh_script()}
  </script>
</body>
</html>
"""

    shared_style = html.split("<style>", 1)[1].split("</style>", 1)[0]
    shared_script = html.split("<script>", 1)[1].split("</script>", 1)[0]
    teams_html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>LoL Teams</title>
  <style>{shared_style}</style>
</head>
<body>
  {render_hidden_head_to_head_link(head_to_head_page_name)}
  <header>
    <div class="topline">
      <div>
        <h1>LoL Teams</h1>
        <p>Drafted team tiers, MVP scores, and scoring formulas for the same {len(matches)} match dataset.</p>
      </div>
      {render_refresh_control(generated_at)}
    </div>
  </header>
  <nav>
    <a href="{html_attr(main_page_name)}#overview">Overview</a>
    <a href="{html_attr(main_page_name)}#awards">Awards</a>
    <a href="{html_attr(main_page_name)}#match-history">Matches</a>
    <a href="{html_attr(main_page_name)}#players">Players</a>
    <a href="{html_attr(main_page_name)}#champion-pools">Champion Pools</a>
    <a href="{html_attr(main_page_name)}#champions">Champions</a>
    <a href="{html_attr(main_page_name)}#role-pools">Role Pools</a>
    <a href="{html_attr(main_page_name)}#combos">Combos</a>
    <a href="#teams">Teams</a>
    <a href="{html_attr(draft_coach_page_name)}#draft-coach">Draft Coach</a>
    <a href="{html_attr(showcases_page_name)}">Showcases</a>
    <a href="{html_attr(experimental_page_name)}#custom-meta">Experimental</a>
    <a href="{html_attr(main_page_name)}#deep-dive">Deep Dive</a>
  </nav>
  <main>
    <section id="teams" class="section">
      <div class="section-title">
        <div>
          <h2>MVP & Drafted Teams</h2>
          <p class="note">MVP formula: {escape(weight_summary(MVP_WEIGHTS))}. MVP board requires at least {MIN_PLAYER_GAMES} games; after that, games add a small capped sample score and can also help through positive net wins. Team role score: {escape(weight_summary(ROLE_SCORE_WEIGHTS))}. Role preference does not add visible score points; the builder uses it only as a small assignment tiebreaker after role score, ranked by games then role winrate. Role Share does not score directly; role games score 5% directly and also affect role-metric reliability. Drafted teams use one TOP, JUNGLE, MID, BOT, and SUPP, without reusing players.</p>
        </div>
      </div>
      <div class="mvp-team-grid">
        {render_table("mvp-scoreboard", "MVP Scoreboard", mvp_rows, mvp_columns)}
        <section class="table-panel team-builder-panel">
          <div class="section-heading">
            <h3>Tiered Teams</h3>
            <small>{len(tiered_teams)} complete teams before running out of role-fit players</small>
          </div>
          {render_tiered_teams(tiered_teams, unused_team_players)}
        </section>
      </div>
    </section>

    {render_scoring_formula_explainer(mvp_rows, role_score_rows, display_player_rows, display_player_role_rows)}
  </main>
  <script>{shared_script}</script>
</body>
</html>
"""

    draft_coach_html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>LoL Draft Coach</title>
  <style>{shared_style}</style>
</head>
<body>
  {render_hidden_head_to_head_link(head_to_head_page_name)}
  <header>
    <div class="topline">
      <div>
        <h1>LoL Draft Coach</h1>
        <p>Target bans, tournament draft simulation, pick recommendations, and practice picks for 40-champion custom drafts.</p>
      </div>
      {render_refresh_control(generated_at)}
    </div>
  </header>
  <nav>
    <a href="{html_attr(main_page_name)}#overview">Overview</a>
    <a href="{html_attr(main_page_name)}#awards">Awards</a>
    <a href="{html_attr(main_page_name)}#match-history">Matches</a>
    <a href="{html_attr(main_page_name)}#players">Players</a>
    <a href="{html_attr(main_page_name)}#champion-pools">Champion Pools</a>
    <a href="{html_attr(main_page_name)}#champions">Champions</a>
    <a href="{html_attr(main_page_name)}#role-pools">Role Pools</a>
    <a href="{html_attr(main_page_name)}#combos">Combos</a>
    <a href="{html_attr(teams_page_name)}#teams">Teams</a>
    <a href="#draft-coach">Draft Coach</a>
    <a href="{html_attr(showcases_page_name)}">Showcases</a>
    <a href="{html_attr(experimental_page_name)}#custom-meta">Experimental</a>
    <a href="{html_attr(main_page_name)}#deep-dive">Deep Dive</a>
  </nav>
  <main>
    {render_target_ban_section(display_target_ban_rows, display_practice_pick_rows, display_player_rows)}
  </main>
  <script>{shared_script}{render_ban_planner_script(display_target_ban_rows, display_target_pick_rows, display_player_rows, champion_h2h_rows)}</script>
</body>
</html>
"""

    showcase_html = render_player_showcase_page(
        shared_style=shared_style,
        appearances=appearances,
        player_rows=display_player_rows,
        player_role_rows=display_player_role_rows,
        player_champion_rows=display_player_champion_rows,
        target_ban_rows=display_target_ban_rows,
        practice_pick_rows=display_practice_pick_rows,
        mvp_rows=mvp_rows,
        role_score_rows=role_score_rows,
        fingerprint_rows=fingerprint_rows,
        form_rows=form_rows,
        generated_at=generated_at,
        main_page_name=main_page_name,
        teams_page_name=teams_page_name,
        draft_coach_page_name=draft_coach_page_name,
        head_to_head_page_name=head_to_head_page_name,
        experimental_page_name=experimental_page_name,
    )

    head_to_head_html = render_head_to_head_page(
        shared_style=shared_style,
        rows=h2h_rows,
        champion_rows=champion_h2h_rows,
        pilot_champion_rows=pilot_champion_h2h_rows,
        generated_at=generated_at,
        main_page_name=main_page_name,
        teams_page_name=teams_page_name,
        draft_coach_page_name=draft_coach_page_name,
        showcases_page_name=showcases_page_name,
        experimental_page_name=experimental_page_name,
    )

    experimental_html = render_experimental_page(
        shared_style=shared_style,
        shared_script=shared_script,
        meta_rows=custom_meta_rows,
        form_rows=form_rows,
        hall_rows=hall_rows,
        chemistry_data=chemistry_data,
        upset_data=upset_data,
        ownership_rows=ownership_rows,
        generated_at=generated_at,
        main_page_name=main_page_name,
        teams_page_name=teams_page_name,
        draft_coach_page_name=draft_coach_page_name,
        showcases_page_name=showcases_page_name,
        head_to_head_page_name=head_to_head_page_name,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    teams_output_path.write_text(teams_html, encoding="utf-8")
    draft_coach_output_path.write_text(draft_coach_html, encoding="utf-8")
    showcase_output_path.write_text(showcase_html, encoding="utf-8")
    head_to_head_output_path.write_text(head_to_head_html, encoding="utf-8")
    experimental_output_path.write_text(experimental_html, encoding="utf-8")


def serve_dashboard(output_path: Path, host: str, port: int) -> None:
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

    class Handler(SimpleHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Serving {output_path.name} at http://{host}:{port}/{output_path.name}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a LoL customs HTML dashboard.")
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Path to match_history.json")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="HTML output path")
    parser.add_argument(
        "--input-url",
        default=os.environ.get("MATCHES_API_URL", ""),
        help="Optional matches API URL. Uses local JSON when omitted.",
    )
    parser.add_argument(
        "--api-key-env",
        default=MATCHES_API_KEY_ENV,
        help="Environment variable containing the matches API key.",
    )
    parser.add_argument("--serve", action="store_true", help="Serve the generated dashboard")
    parser.add_argument("--host", default="127.0.0.1", help="Host for --serve")
    parser.add_argument("--port", default=8000, type=int, help="Port for --serve")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    api_key = os.environ.get(args.api_key_env, "")
    api_url = args.input_url or (DEFAULT_MATCHES_API_URL if api_key else "")
    build_dashboard(input_path, output_path, api_url=api_url, api_key=api_key)
    print(f"Wrote {output_path.resolve()}")
    print(f"Wrote {teams_page_path(output_path).resolve()}")
    print(f"Wrote {draft_coach_page_path(output_path).resolve()}")
    print(f"Wrote {showcases_page_path(output_path).resolve()}")
    print(f"Wrote {head_to_head_page_path(output_path).resolve()}")
    print(f"Wrote {experimental_page_path(output_path).resolve()}")
    if args.serve:
        serve_dashboard(output_path, args.host, args.port)


if __name__ == "__main__":
    main()
