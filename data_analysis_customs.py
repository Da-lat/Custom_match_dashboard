from __future__ import annotations

import argparse
import json
import os
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from html import escape
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from itertools import combinations
from pathlib import Path
from typing import Callable, Iterable, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
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
MIN_CHAMPION_GAMES = 5
MIN_COMBO_GAMES = 3
TARGET_BAN_MIN_GAMES = 3
TARGET_BAN_RELIABILITY_GAMES = 5
PRACTICE_PICK_MIN_GAMES = 2
PRACTICE_PICK_MAX_WINRATE = 0.45
PRACTICE_PICK_BASELINE_GAP = 0.05
PRACTICE_PICK_RELIABILITY_GAMES = 6
ROLE_RELIABILITY_GAMES = 8
TEAM_COMBO_MIN_GAMES = {
    2: 10,
    3: 5,
    4: 3,
    5: 2,
}
MVP_WEIGHTS = {
    "Adjusted WR": 0.35,
    "KDA": 0.25,
    "Games": 0.20,
    "Champion Pool": 0.15,
    "Low Deaths": 0.05,
}
ROLE_SCORE_WEIGHTS = {
    "Adjusted WR": 0.30,
    "Role KDA": 0.20,
    "Role Games": 0.20,
    "Role Champion Pool": 0.15,
    "Role Share": 0.10,
    "Overall MVP": 0.05,
}
TEAM_TIERS = ("S", "A", "B", "C", "D", "F")
CHAMPION_ROSTER_VERSION = "16.10.1"
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


def showcases_page_path(output_path: Path) -> Path:
    return output_path.with_name(f"{output_path.stem}_showcases{output_path.suffix}")


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
            for player_data in players:
                kills, deaths, assists = parse_kda(player_data.get("kda", "0/0/0"))
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


def champion_key(name: str) -> str:
    value = name.casefold().replace("&", "and")
    return "".join(character for character in value if character.isalnum())


def champion_asset_id(name: str) -> str:
    overrides = {
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
    if name in overrides:
        return overrides[name]
    return "".join(character for character in name if character.isalnum())


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
        unique_champions = len(group["champions"])
        row.update(
            {
                "games": games,
                "wins": wins,
                "losses": games - wins,
                "winrate": safe_div(wins, games),
                "kills": kills,
                "deaths": deaths,
                "assists": assists,
                "avg_kills": safe_div(kills, games),
                "avg_deaths": safe_div(deaths, games),
                "avg_assists": safe_div(assists, games),
                "avg_takedowns": safe_div(kills + assists, games),
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
    kda_low, kda_high = metric_bounds(player_rows, "kda_ratio")
    death_low, death_high = metric_bounds(player_rows, "avg_deaths")
    max_games = max((int(row.get("games", 0)) for row in player_rows), default=1)
    rows = []
    for player in player_rows:
        games = int(player.get("games", 0))
        winrate = float(player.get("winrate", 0))
        reliability = clamp(games / MIN_PLAYER_GAMES)
        adjusted_winrate = 0.5 + ((winrate - 0.5) * reliability)
        kda_score = normalized_metric(float(player.get("kda_ratio", 0)), kda_low, kda_high)
        games_score = (safe_div(games, max_games)) ** 0.5
        champion_pool_score = (
            float(player.get("champion_pool_rate", 0)) * reliability
        ) ** 0.5
        low_death_score = normalized_metric(
            float(player.get("avg_deaths", 0)), death_low, death_high, invert=True
        )
        total_score = 100 * (
            MVP_WEIGHTS["Adjusted WR"] * clamp(adjusted_winrate)
            + MVP_WEIGHTS["KDA"] * kda_score
            + MVP_WEIGHTS["Games"] * games_score
            + MVP_WEIGHTS["Champion Pool"] * champion_pool_score
            + MVP_WEIGHTS["Low Deaths"] * low_death_score
        )
        row = dict(player)
        row.update(
            {
                "mvp_score": total_score,
                "adjusted_winrate": adjusted_winrate,
                "reliability": reliability,
                "kda_score": kda_score,
                "games_score": games_score,
                "champion_pool_score": champion_pool_score,
                "low_death_score": low_death_score,
            }
        )
        rows.append(row)
    rows.sort(
        key=lambda row: (
            -float(row["mvp_score"]),
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
    player_by_name = {str(row["name"]): row for row in player_rows}
    mvp_by_name = {str(row["name"]): row for row in mvp_rows}
    kda_low, kda_high = metric_bounds(player_role_rows, "kda_ratio")
    max_role_games = max(
        (int(row.get("games", 0)) for row in player_role_rows), default=1
    )
    rows = []
    for role_row in player_role_rows:
        role = str(role_row.get("role", ""))
        if role not in ROLE_ORDER:
            continue
        name = str(role_row["name"])
        player = player_by_name.get(name, {})
        games = int(role_row.get("games", 0))
        player_games = int(player.get("games", games)) or games or 1
        winrate = float(role_row.get("winrate", 0))
        reliability = clamp(games / ROLE_RELIABILITY_GAMES)
        adjusted_winrate = 0.5 + ((winrate - 0.5) * reliability)
        role_kda_score = normalized_metric(
            float(role_row.get("kda_ratio", 0)), kda_low, kda_high
        )
        role_games_score = (safe_div(games, max_role_games)) ** 0.5
        role_pool_score = (
            float(role_row.get("champion_pool_rate", 0)) * reliability
        ) ** 0.5
        role_share = safe_div(games, player_games)
        overall_mvp_score = safe_div(
            float(mvp_by_name.get(name, {}).get("mvp_score", 0)), 100
        )
        role_score = 100 * (
            ROLE_SCORE_WEIGHTS["Adjusted WR"] * clamp(adjusted_winrate)
            + ROLE_SCORE_WEIGHTS["Role KDA"] * role_kda_score
            + ROLE_SCORE_WEIGHTS["Role Games"] * role_games_score
            + ROLE_SCORE_WEIGHTS["Role Champion Pool"] * role_pool_score
            + ROLE_SCORE_WEIGHTS["Role Share"] * role_share
            + ROLE_SCORE_WEIGHTS["Overall MVP"] * overall_mvp_score
        )
        row = dict(role_row)
        row.update(
            {
                "role_score": role_score,
                "adjusted_winrate": adjusted_winrate,
                "role_share": role_share,
                "reliability": reliability,
                "role_kda_score": role_kda_score,
                "role_games_score": role_games_score,
                "role_pool_score": role_pool_score,
                "overall_mvp_score": overall_mvp_score,
            }
        )
        rows.append(row)
    return sorted(
        rows,
        key=lambda row: (
            role_sort(str(row["role"])),
            -float(row["role_score"]),
            -int(row["games"]),
            str(row["name"]),
        ),
    )


def build_tiered_teams(
    player_rows: Sequence[dict[str, object]],
    role_score_rows: Sequence[dict[str, object]],
) -> tuple[list[dict[str, object]], list[str]]:
    all_players = {str(row["name"]) for row in player_rows}
    candidates_by_role = {
        role: sorted(
            [row for row in role_score_rows if str(row["role"]) == role],
            key=lambda row: (-float(row["role_score"]), -int(row["games"]), str(row["name"])),
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
                cost = -round((role_score * 1000) + role_games)
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
        mvp_rating = clamp(float(mvp.get("mvp_score", player_adjusted_winrate * 100)) / 100)
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
        scored_row = dict(row)
        scored_row.update(
            {
                "ban_score": ban_score,
                "adjusted_winrate": adjusted_winrate,
                "reliability": reliability,
                "player_winrate": player_winrate,
                "player_adjusted_winrate": player_adjusted_winrate,
                "player_threat": player_threat,
                "mvp_score": float(mvp.get("mvp_score", 0)),
                "lift": lift,
                "confidence": confidence,
                "target_detail": (
                    f"{wins}-{games - wins}, {games} games, {pct(winrate)} WR, "
                    f"{two_decimal(float(row.get('kda_ratio', 0)))} KDA, "
                    f"{score(float(mvp.get('mvp_score', 0)))} MVP"
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
    player_pool = qualify(player_rows, MIN_PLAYER_GAMES) or list(player_rows)
    champion_pool = qualify(champion_rows, MIN_CHAMPION_GAMES) or list(champion_rows)
    combo_pool = qualify(player_champion_role_rows, MIN_COMBO_GAMES) or list(
        player_champion_role_rows
    )
    player_champion_pool = qualify(player_champion_rows, MIN_COMBO_GAMES) or list(
        player_champion_rows
    )
    role_pool = qualify(player_role_rows, MIN_COMBO_GAMES) or list(player_role_rows)

    best_winrate = find_first(
        sorted(player_pool, key=lambda row: (-float(row["winrate"]), -int(row["games"])))
    )
    best_kda = find_first(
        sorted(player_pool, key=lambda row: (-float(row["kda_ratio"]), -int(row["games"])))
    )
    best_avg_kills = find_first(
        sorted(player_pool, key=lambda row: (-float(row["avg_kills"]), -int(row["games"])))
    )
    most_games = find_first(sorted(player_rows, key=lambda row: -int(row["games"])))
    most_champs = find_first(
        sorted(
            player_rows,
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
        sorted(champion_rows, key=lambda row: -int(row["games"]))
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

    highest_kills = max(appearances, key=lambda row: (row.kills, row.assists, -row.deaths))
    highest_deaths = max(appearances, key=lambda row: (row.deaths, row.kills))
    highest_assists = max(appearances, key=lambda row: (row.assists, row.kills))
    zero_death_rows = [row for row in appearances if row.deaths == 0]
    perfect_game = max(
        zero_death_rows or appearances,
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
    return awards


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
    visible_rows = list(rows if limit is None else rows[:limit])
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


def team_table(title: str, rows: Sequence[Appearance], css_class: str) -> str:
    ordered_rows = sorted(rows, key=lambda row: role_sort(row.role))
    body = []
    for row in ordered_rows:
        champion = row.champion
        body.append(
            f"""
            <tr>
              <td><span class="role-pill">{escape(row.role)}</span></td>
              <td class="match-player-cell"><strong>{escape(row.name)}</strong><small>{escape(row.player)}</small></td>
              <td><span class="match-champion-cell"><img src="{html_attr(champion_icon_url(champion))}" alt="{html_attr(champion)}"><span>{escape(champion)}</span></span></td>
              <td class="match-score-cell">{row.kills}/{row.deaths}/{row.assists}</td>
              <td class="match-kda-cell">{two_decimal(row.kda_ratio)}</td>
            </tr>
            """
        )
    return f"""
    <div class="match-team {css_class}">
      <div class="team-heading">
        <h4>{escape(title)}</h4>
        <strong>{sum(row.kills for row in rows)} kills</strong>
      </div>
      <table>
        <colgroup>
          <col class="match-role-col">
          <col class="match-player-col">
          <col class="match-champion-col">
          <col class="match-score-col">
          <col class="match-kda-col">
        </colgroup>
        <thead>
          <tr><th>Role</th><th>Player</th><th>Champion</th><th>K/D/A</th><th>KDA</th></tr>
        </thead>
        <tbody>{''.join(body)}</tbody>
      </table>
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
              <div class="match-teams">
                {team_table("Winning Team", win_rows, "winning-team")}
                {team_table("Losing Team", lose_rows, "losing-team")}
              </div>
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
                  <small>{integer(row["games"])}g, {pct(float(row["winrate"]))} WR, {escape(str(row["champions"]))}</small>
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
    <section id="target-bans" class="section">
      <div class="section-title">
        <div>
          <h2>Target Ban Planner</h2>
          <p class="note">Top player/champion ban targets use adjusted winrate, sample size, KDA, takedowns, and lift against that player's baseline. General list uses at least {TARGET_BAN_MIN_GAMES} games where possible.</p>
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
    player_names = sorted(str(row.get("name", "")) for row in player_rows)
    target_json = json.dumps(target_data, ensure_ascii=True).replace("</", "<\\/")
    pick_json = json.dumps(pick_data, ensure_ascii=True).replace("</", "<\\/")
    champion_json = json.dumps(champion_data, ensure_ascii=True).replace("</", "<\\/")
    player_json = json.dumps(player_names, ensure_ascii=True).replace("</", "<\\/")
    script = """
    const banTargetData = __BAN_TARGET_DATA__;
    const pickTargetData = __PICK_TARGET_DATA__;
    const championRosterData = __CHAMPION_ROSTER_DATA__;
    const banPlayerNames = __BAN_PLAYER_NAMES__;
    const draftInputs = Array.from(document.querySelectorAll("[data-draft-team]"));
    const draftImportText = document.querySelector("[data-draft-import-text]");
    const draftImportButton = document.querySelector("[data-draft-import]");
    const draftImportStatus = document.querySelector("[data-draft-import-status]");
    const championPoolText = document.querySelector("[data-champion-pool-text]");
    const championPoolStatus = document.querySelector("[data-champion-pool-status]");
    const championPoolList = document.querySelector("[data-champion-pool-list]");
    const championPoolClear = document.querySelector("[data-champion-pool-clear]");

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

    function selectedDraftPlayers(team) {
      return selectedDraftEntries(team).map(entry => entry.player);
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

    function chooseTargetBans(targetEntries, pool, limit = 3) {
      if (!targetEntries.length) return [];
      const candidates = targetEntries
        .flatMap(entry => banCandidatesForEntry(entry))
        .filter(row => rowInChampionPool(row, pool))
        .sort((left, right) =>
          right.draftScore - left.draftScore ||
          right.score - left.score ||
          right.winrate - left.winrate ||
          right.games - left.games
        );
      const picks = [];
      const usedChampions = new Set();
      const pickCountsByPlayer = new Map();
      const addCandidate = (candidate, requireFreshPlayer, minimumScore) => {
        if (picks.length >= limit) return;
        if (candidate.draftScore < minimumScore) return;
        const championKey = candidate.champion.toLowerCase();
        if (usedChampions.has(championKey)) return;
        if (requireFreshPlayer && picks.some(row => row.player === candidate.player)) return;
        if ((pickCountsByPlayer.get(candidate.player) || 0) >= 2) return;
        usedChampions.add(championKey);
        pickCountsByPlayer.set(candidate.player, (pickCountsByPlayer.get(candidate.player) || 0) + 1);
        picks.push(candidate);
      };

      candidates.forEach(candidate => addCandidate(candidate, true, 50));
      candidates.forEach(candidate => addCandidate(candidate, false, 45));
      return picks;
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

    function bestPickForEntry(entry, usedChampions, pool) {
      const sortRows = rows => rows
        .filter(row => rowInChampionPool(row, pool))
        .filter(row => !usedChampions.has(row.champion.toLowerCase()))
        .sort((left, right) => right.score - left.score || right.winrate - left.winrate || right.games - left.games);
      const roleRows = sortRows(pickTargetData.filter(row => row.player === entry.player && row.role === entry.role));
      const fallbackRows = sortRows(
        banTargetData.filter(row => row.player === entry.player && championHasRole(row.champion, entry.role))
      );
      const pick = roleRows[0] || fallbackRows[0];
      if (!pick) return null;
      usedChampions.add(pick.champion.toLowerCase());
      return {
        ...pick,
        assignedRole: entry.role,
        fit: entry.fit,
        roleMatched: Boolean(roleRows[0]),
        roleEligibleFallback: !roleRows[0]
      };
    }

    function chooseTeamPicks(entries, pool, limit = 5) {
      const usedChampions = new Set();
      const picks = [];
      entries.forEach(entry => {
        if (picks.length >= limit) return;
        const pick = bestPickForEntry(entry, usedChampions, pool);
        if (pick) picks.push(pick);
      });
      return picks;
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
        return `
          <article class="ban-pick-row">
            <b>${index + 1}</b>
            <img src="${escapeBanHtml(row.championIcon)}" alt="${escapeBanHtml(row.champion)}">
            <div class="ban-pick-copy">
              <strong>${escapeBanHtml(row.champion)}</strong>
              <span>${escapeBanHtml(row.player)} - ${escapeBanHtml(roleNote)}${fitNote}</span>
              <small>${row.games}g, ${formatBanPercent(row.winrate)} WR, ${Number(row.kda).toFixed(2)} KDA, ${Number(row.mvpScore).toFixed(1)} MVP</small>
            </div>
            <em>${Number(row.score).toFixed(1)}</em>
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
      renderBanResults("blue", chooseTargetBans(redEntries, pool), redEntries);
      renderPickResults("blue", chooseTeamPicks(blueEntries, pool), blueEntries);
      renderBanResults("red", chooseTargetBans(blueEntries, pool), blueEntries);
      renderPickResults("red", chooseTeamPicks(redEntries, pool), redEntries);
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
      grid-template-columns: minmax(0, 1.08fr) minmax(360px, 0.92fr);
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
      .showcase-moments {
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
      .showcase-moments {
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
    generated_at: str,
    main_page_name: str,
    teams_page_name: str,
) -> str:
    player_by_name = {str(row.get("name", "")): row for row in player_rows}
    mvp_by_name = {str(row.get("name", "")): row for row in mvp_rows}
    records_by_name: dict[str, list[Appearance]] = defaultdict(list)
    for appearance in appearances:
        records_by_name[appearance.name].append(appearance)
    for records in records_by_name.values():
        records.sort(key=lambda row: (row.timestamp, row.match_id))

    ordered_names = [str(row.get("name", "")) for row in mvp_rows if str(row.get("name", ""))]
    for name in sorted(player_by_name):
        if name not in ordered_names:
            ordered_names.append(name)

    games_rank = {
        str(row.get("name", "")): index
        for index, row in enumerate(
            sorted(player_rows, key=lambda row: (-int(row.get("games", 0)), str(row.get("name", "")))),
            start=1,
        )
    }
    unique_champ_rank = {
        str(row.get("name", "")): index
        for index, row in enumerate(
            sorted(
                player_rows,
                key=lambda row: (-int(row.get("unique_champions", 0)), -int(row.get("games", 0)), str(row.get("name", ""))),
            ),
            start=1,
        )
    }
    pool_rate_rank = {
        str(row.get("name", "")): index
        for index, row in enumerate(
            sorted(
                [row for row in player_rows if int(row.get("games", 0)) >= MIN_PLAYER_GAMES],
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
        sum(float(row.get("avg_deaths", 0)) for row in player_rows), len(player_rows)
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
        mvp_score = float(mvp.get("mvp_score", 0))
        mvp_rank = int(mvp.get("mvp_rank", index + 1))
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
            f"ranking #{mvp_rank} on MVP score. The identity so far is {main_role} first, "
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
                  <div class="showcase-kicker">Player Showcase / #{mvp_rank} MVP Rank</div>
                  <h2>{escape(name)}</h2>
                  <p class="showcase-summary">{escape(summary)}</p>
                </div>
                <div class="showcase-hero-grid">
                  {render_showcase_stat("Games", integer(player_games), f"#{games_rank.get(name, 0)} by volume", None)}
                  {render_showcase_stat("Winrate", pct(winrate), f"{wins}-{player_games - wins} record", winrate)}
                  {render_showcase_stat("KDA", player_kda, player_average_line, None)}
                  {render_showcase_stat("MVP Score", score(mvp_score), f"Rank #{mvp_rank} in this dataset", safe_div(mvp_score, 100))}
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
    <a href="{html_attr(teams_page_name)}#target-bans">Bans</a>
    <a href="#{html_attr(first_slug)}">Showcases</a>
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

    kda_low, kda_high = metric_bounds(player_rows, "kda_ratio")
    death_low, death_high = metric_bounds(player_rows, "avg_deaths")
    max_games = max((int(row.get("games", 0)) for row in player_rows), default=1)
    role_kda_low, role_kda_high = metric_bounds(player_role_rows, "kda_ratio")
    max_role_games = max(
        (int(row.get("games", 0)) for row in player_role_rows), default=1
    )

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

    mvp_reliability = float(player_example.get("reliability", 0))
    mvp_kda_score = float(player_example.get("kda_score", 0))
    mvp_games_score = float(player_example.get("games_score", 0))
    mvp_pool_score = float(player_example.get("champion_pool_score", 0))
    mvp_low_death_score = float(player_example.get("low_death_score", 0))
    mvp_adjusted_wr = clamp(float(player_example.get("adjusted_winrate", 0)))
    player_games = int(player_example.get("games", 0))
    player_wins = int(player_example.get("wins", 0))
    player_losses = int(player_example.get("losses", 0))
    player_kills = int(player_example.get("kills", 0))
    player_deaths = int(player_example.get("deaths", 0))
    player_assists = int(player_example.get("assists", 0))
    player_unique_champs = int(player_example.get("unique_champions", 0))
    player_pool_rate = float(player_example.get("champion_pool_rate", 0))

    mvp_example_rows = [
        (
            "Adjusted WR",
            f"Reliability = min(games / {MIN_PLAYER_GAMES}, 1). Adjusted WR = 50% + ((raw WR - 50%) x reliability).",
            f"{player_wins}-{player_losses}, {pct(float(player_example.get('winrate', 0)))} WR; reliability {pct(mvp_reliability)}",
            pct(mvp_adjusted_wr),
            pct(MVP_WEIGHTS["Adjusted WR"]),
            weighted_points(mvp_adjusted_wr, MVP_WEIGHTS["Adjusted WR"]),
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
            "Games",
            "Sample-size credit with diminishing returns: sqrt(player games / most games by any player).",
            f"{player_games} games / {max_games} max games",
            pct(mvp_games_score),
            pct(MVP_WEIGHTS["Games"]),
            weighted_points(mvp_games_score, MVP_WEIGHTS["Games"]),
        ),
        (
            "Champion Pool",
            "Unique-pick rate with reliability: sqrt((unique champions / games) x reliability).",
            f"{player_unique_champs} unique champions / {player_games} games = {pct(player_pool_rate)}; reliability {pct(mvp_reliability)}",
            pct(mvp_pool_score),
            pct(MVP_WEIGHTS["Champion Pool"]),
            weighted_points(mvp_pool_score, MVP_WEIGHTS["Champion Pool"]),
        ),
        (
            "Low Deaths",
            "Average deaths per game, normalized against the player range and inverted so lower is better.",
            f"{one_decimal(float(player_example.get('avg_deaths', 0)))} deaths/game; range {one_decimal(death_low)} to {one_decimal(death_high)}",
            pct(mvp_low_death_score),
            pct(MVP_WEIGHTS["Low Deaths"]),
            weighted_points(mvp_low_death_score, MVP_WEIGHTS["Low Deaths"]),
        ),
    ]

    definition_rows = [
        (
            "Adjusted WR",
            "A sample-adjusted winrate. Under the reliability threshold, a player's raw winrate is pulled toward 50% so one hot or cold night does not dominate.",
        ),
        (
            "KDA / Role KDA",
            "Kills plus assists divided by deaths. The dashboard converts this to a 0-100% component by comparing it to the lowest and highest KDA in the current dataset.",
        ),
        (
            "Games / Role Games",
            "A sample-size component using square root scaling. More games help, but the benefit slows down as the sample gets larger.",
        ),
        (
            "Champion Pool / Role Champion Pool",
            "Unique-pick rate rather than raw unique champion count. A player with 16 unique champions in 17 games rates higher than a player with 20 unique champions in 60 games.",
        ),
        (
            "Low Deaths",
            "Average deaths per game. It is inverted after normalization, so fewer deaths create a higher score.",
        ),
        (
            "Role Share",
            "The share of a player's total games played in that role. This rewards actual role comfort instead of one-off role appearances.",
        ),
        (
            "Overall MVP",
            "The player's overall MVP score divided by 100. It is only 5% of role score, so role performance still matters most.",
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
        role_adjusted_wr = clamp(float(role_example.get("adjusted_winrate", 0)))
        role_kda_score = float(role_example.get("role_kda_score", 0))
        role_games_score = float(role_example.get("role_games_score", 0))
        role_pool_score = float(role_example.get("role_pool_score", 0))
        role_share = float(role_example.get("role_share", 0))
        overall_mvp_score = float(role_example.get("overall_mvp_score", 0))
        role_games = int(role_example.get("games", 0))
        role_wins = int(role_example.get("wins", 0))
        role_losses = int(role_example.get("losses", 0))
        role_kills = int(role_example.get("kills", 0))
        role_deaths = int(role_example.get("deaths", 0))
        role_assists = int(role_example.get("assists", 0))
        role_unique_champs = int(role_example.get("unique_champions", 0))
        role_pool_rate = float(role_example.get("champion_pool_rate", 0))
        role_example_rows = [
            (
                "Adjusted WR",
                f"Role reliability = min(role games / {ROLE_RELIABILITY_GAMES}, 1). Adjusted WR = 50% + ((role WR - 50%) x reliability).",
                f"{role_wins}-{role_losses}, {pct(float(role_example.get('winrate', 0)))} {role} WR; reliability {pct(role_reliability)}",
                pct(role_adjusted_wr),
                pct(ROLE_SCORE_WEIGHTS["Adjusted WR"]),
                weighted_points(
                    role_adjusted_wr, ROLE_SCORE_WEIGHTS["Adjusted WR"]
                ),
            ),
            (
                "Role KDA",
                "Role KDA is normalized against every player-role KDA in the current dataset.",
                f"({role_kills} + {role_assists}) / {max(1, role_deaths)} = {two_decimal(float(role_example.get('kda_ratio', 0)))}; range {two_decimal(role_kda_low)} to {two_decimal(role_kda_high)}",
                pct(role_kda_score),
                pct(ROLE_SCORE_WEIGHTS["Role KDA"]),
                weighted_points(role_kda_score, ROLE_SCORE_WEIGHTS["Role KDA"]),
            ),
            (
                "Role Games",
                "Sample-size credit inside the role: sqrt(role games / highest player-role game count).",
                f"{role_games} {role} games / {max_role_games} max player-role games",
                pct(role_games_score),
                pct(ROLE_SCORE_WEIGHTS["Role Games"]),
                weighted_points(role_games_score, ROLE_SCORE_WEIGHTS["Role Games"]),
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
                "Role Share",
                "How much of this player's history is in this role.",
                f"{role_games} of {player_games} {example_name} games were {role}",
                pct(role_share),
                pct(ROLE_SCORE_WEIGHTS["Role Share"]),
                weighted_points(role_share, ROLE_SCORE_WEIGHTS["Role Share"]),
            ),
            (
                "Overall MVP",
                "A small tie-breaker from the overall player score.",
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
            <p>Adjusted WR uses {MIN_PLAYER_GAMES} games for overall MVP reliability and {ROLE_RELIABILITY_GAMES} games for role-score reliability. Champion Pool uses unique-pick rate, calculated as unique champions divided by games.</p>
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
    add_player_role_breakdowns(player_rows, player_role_rows)
    mvp_rows = mvp_score_rows(player_rows)
    target_ban_rows = target_ban_score_rows(player_champion_rows, player_rows, mvp_rows)
    target_pick_rows = target_ban_score_rows(
        player_champion_role_rows, player_rows, mvp_rows
    )
    practice_pick_rows = practice_pick_score_rows(player_champion_rows, player_rows)
    best_mvp = find_first(mvp_rows)
    role_score_rows = player_role_score_rows(player_rows, player_role_rows, mvp_rows)
    tiered_teams, unused_team_players = build_tiered_teams(player_rows, role_score_rows)
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
    showcase_output_path = showcases_page_path(output_path)
    main_page_name = output_path.name
    teams_page_name = teams_output_path.name
    showcases_page_name = showcase_output_path.name

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

    top_player_chart_rows = sorted(
        qualify(player_rows, MIN_PLAYER_GAMES),
        key=lambda row: (-float(row["winrate"]), -int(row["games"])),
    )
    bottom_player_chart_rows = sorted(
        qualify(player_rows, MIN_PLAYER_GAMES),
        key=lambda row: (float(row["winrate"]), -int(row["games"])),
    )
    top_kda_chart_rows = sorted(
        qualify(player_rows, MIN_PLAYER_GAMES),
        key=lambda row: (-float(row["kda_ratio"]), -int(row["games"])),
    )
    most_played_champion_rows = sorted(champion_rows, key=lambda row: -int(row["games"]))
    popular_champion_strip_rows = [
        row
        for row in most_played_champion_rows
        if champion_key(str(row.get("champion", ""))) != champion_key("Qiyana")
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
        ("K", "avg_kills", lambda value: one_decimal(float(value)), "number"),
        ("D", "avg_deaths", lambda value: one_decimal(float(value)), "number"),
        ("A", "avg_assists", lambda value: one_decimal(float(value)), "number"),
        ("Unique Champs", "unique_champions", integer, "number"),
        ("Unique Pick %", "champion_pool_rate", lambda value: pct(float(value)), "number"),
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
        ("Winrate", "winrate", lambda value: pct(float(value)), "number"),
        ("Adj WR", "adjusted_winrate", lambda value: pct(float(value)), "number"),
        ("KDA", "kda_ratio", lambda value: two_decimal(float(value)), "number"),
        ("Unique Champs", "unique_champions", integer, "number"),
        ("Unique Pick %", "champion_pool_rate", lambda value: pct(float(value)), "number"),
        ("Avg Deaths", "avg_deaths", lambda value: one_decimal(float(value)), "number"),
    ]
    champion_columns: list[Column] = [
        ("Champion", "champion", str, "text"),
        ("Games", "games", integer, "number"),
        ("W", "wins", integer, "number"),
        ("L", "losses", integer, "number"),
        ("Winrate", "winrate", lambda value: pct(float(value)), "number"),
        ("KDA", "kda_ratio", lambda value: two_decimal(float(value)), "number"),
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
        ("K", "avg_kills", lambda value: one_decimal(float(value)), "number"),
        ("D", "avg_deaths", lambda value: one_decimal(float(value)), "number"),
        ("A", "avg_assists", lambda value: one_decimal(float(value)), "number"),
    ]
    player_role_columns: list[Column] = [
        ("Player", "name", str, "text"),
        ("Role", "role", str, "text"),
        ("Games", "games", integer, "number"),
        ("W", "wins", integer, "number"),
        ("Winrate", "winrate", lambda value: pct(float(value)), "number"),
        ("KDA", "kda_ratio", lambda value: two_decimal(float(value)), "number"),
        ("K", "avg_kills", lambda value: one_decimal(float(value)), "number"),
        ("D", "avg_deaths", lambda value: one_decimal(float(value)), "number"),
        ("A", "avg_assists", lambda value: one_decimal(float(value)), "number"),
        ("Main Champs", "most_played_champion", str, "text"),
    ]
    role_champion_pool_columns: list[Column] = [
        ("Role", "role", str, "text"),
        ("Unique Champs", "unique_champions", integer, "number"),
        ("Unique Pick %", "champion_pool_rate", lambda value: pct(float(value)), "number"),
        ("Games", "games", integer, "number"),
        ("Champions", "champions", str, "text"),
    ]
    player_role_pool_columns: list[Column] = [
        ("Player", "name", str, "text"),
        ("Role", "role", str, "text"),
        ("Unique Champs", "unique_champions", integer, "number"),
        ("Unique Pick %", "champion_pool_rate", lambda value: pct(float(value)), "number"),
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
    .match-teams {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 0;
    }}
    .match-team {{
      min-width: 0;
      overflow-x: hidden;
    }}
    .match-team + .match-team {{
      border-left: 1px solid var(--line);
    }}
    .team-heading {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
      padding: 12px 16px;
      border-bottom: 1px solid var(--line);
    }}
    .team-heading h4 {{
      margin: 0;
      font-size: 0.9rem;
      text-transform: uppercase;
      letter-spacing: 0;
    }}
    .winning-team .team-heading {{
      background: #eef8f3;
      color: #166547;
    }}
    .losing-team .team-heading {{
      background: #fff0f2;
      color: #9d2837;
    }}
    .match-team table {{
      font-size: 0.86rem;
      min-width: 0;
      table-layout: fixed;
    }}
    .match-role-col {{
      width: 78px;
    }}
    .match-player-col {{
      width: 31%;
    }}
    .match-champion-col {{
      width: 31%;
    }}
    .match-score-col {{
      width: 76px;
    }}
    .match-kda-col {{
      width: 54px;
    }}
    .match-team thead th {{
      position: static;
      padding: 8px 10px;
    }}
    .match-team td {{
      padding: 9px 10px;
      vertical-align: middle;
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
    .winning-team .team-heading {{
      background: rgba(79, 196, 139, 0.16);
      color: #8ee1b8;
    }}
    .loss-score,
    .losing-team .team-heading {{
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
      .match-teams {{ grid-template-columns: 1fr; }}
      .match-team + .match-team {{ border-left: 0; border-top: 1px solid var(--line); }}
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
    <a href="{html_attr(teams_page_name)}#target-bans">Bans</a>
    <a href="{html_attr(showcases_page_name)}">Showcases</a>
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
        {render_bar_chart("Top Player Win Rate", top_player_chart_rows, "name", "winrate", pct, limit=10, max_value=1.0, footer_key="games", footer_formatter=lambda value: f"{integer(value)} games")}
        {render_bar_chart("Bottom Player Win Rate", bottom_player_chart_rows, "name", "winrate", pct, limit=10, max_value=1.0, footer_key="games", footer_formatter=lambda value: f"{integer(value)} games")}
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
      {render_player_role_heatmap(player_rows, player_role_rows)}
      {render_table("player-summary", "Player Summary", player_rows, player_columns)}
      {render_table("player-role", "Player Performance By Role", player_role_rows, player_role_columns)}
    </section>

    <section id="champion-pools" class="section">
      <div class="section-title">
        <div>
          <h2>Player Champion Pools</h2>
          <p class="note">Browse one player at a time. Unique-pick rate is unique champions divided by games, so champion pool depth is not just raw volume.</p>
        </div>
      </div>
      <div class="player-pool-browser">
        <button type="button" data-pool-prev>Previous</button>
        <select id="player-pool-picker" aria-label="Select player champion pool"></select>
        <button type="button" data-pool-next>Next</button>
        <input class="card-search" type="search" placeholder="Search players or champions" data-pool-search>
        <span class="pool-count" data-pool-count></span>
        <button type="button" class="orientation-button active" data-pool-orientation="horizontal">Horizontal</button>
        <button type="button" class="orientation-button" data-pool-orientation="vertical">Vertical</button>
      </div>
      <div class="player-pool-grid pool-orientation-horizontal" data-card-container="champion-pools">
        {render_player_champion_pools(player_rows, player_champion_rows)}
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
      {render_table("player-role-champion-pools", "Player Unique Champions By Role", player_role_champion_pool, player_role_pool_columns, controls_html=role_filter_control("player-role-champion-pools"))}
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
      {render_table("player-champion", "Player Champion Summary", player_champion_rows, [column for column in player_champion_role_columns if column[1] != "role"])}
      {render_table("player-champion-role", "Player Champion Role Summary", player_champion_role_rows, player_champion_role_columns)}
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

      function selectedMatchId() {{
        const active = document.querySelector(".match-card.active");
        return active ? active.dataset.matchId : matchCards[matchCards.length - 1].dataset.matchId;
      }}

      function showMatch(matchId, updateHash = false) {{
        matchCards.forEach(card => {{
          card.classList.toggle("active", card.dataset.matchId === String(matchId));
        }});
        matchPicker.value = String(matchId);
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

    {render_ban_planner_script(target_ban_rows, target_pick_rows, player_rows)}

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
  <title>LoL Teams & Bans</title>
  <style>{shared_style}</style>
</head>
<body>
  <header>
    <div class="topline">
      <div>
        <h1>LoL Teams & Bans</h1>
        <p>Drafted team tiers, MVP scores, and the target-ban planner for the same {len(matches)} match dataset.</p>
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
    <a href="#target-bans">Bans</a>
    <a href="{html_attr(showcases_page_name)}">Showcases</a>
    <a href="{html_attr(main_page_name)}#deep-dive">Deep Dive</a>
  </nav>
  <main>
    <section id="teams" class="section">
      <div class="section-title">
        <div>
          <h2>MVP & Drafted Teams</h2>
          <p class="note">MVP formula: {escape(weight_summary(MVP_WEIGHTS))}. Champion Pool uses unique-pick rate with sample reliability. Team role score: {escape(weight_summary(ROLE_SCORE_WEIGHTS))}. Role Champion Pool also uses role-specific unique-pick rate. Drafted teams use one TOP, JUNGLE, MID, BOT, and SUPP, without reusing players.</p>
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

    {render_target_ban_section(target_ban_rows, practice_pick_rows, player_rows)}
    {render_scoring_formula_explainer(mvp_rows, role_score_rows, player_rows, player_role_rows)}
  </main>
  <script>{shared_script}</script>
</body>
</html>
"""

    showcase_html = render_player_showcase_page(
        shared_style=shared_style,
        appearances=appearances,
        player_rows=player_rows,
        player_role_rows=player_role_rows,
        player_champion_rows=player_champion_rows,
        target_ban_rows=target_ban_rows,
        practice_pick_rows=practice_pick_rows,
        mvp_rows=mvp_rows,
        role_score_rows=role_score_rows,
        generated_at=generated_at,
        main_page_name=main_page_name,
        teams_page_name=teams_page_name,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    teams_output_path.write_text(teams_html, encoding="utf-8")
    showcase_output_path.write_text(showcase_html, encoding="utf-8")


def serve_dashboard(output_path: Path, host: str, port: int) -> None:
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
    print(f"Wrote {showcases_page_path(output_path).resolve()}")
    if args.serve:
        serve_dashboard(output_path, args.host, args.port)


if __name__ == "__main__":
    main()
