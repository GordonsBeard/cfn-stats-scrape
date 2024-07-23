"""Generates the LP/MR/Kudos leaderboards"""

import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

from constants import charid_map, fetch_league_name, get_kudos_class, get_mr_class


def generate_leaderboards() -> (
    tuple[dict[str, list[dict[str, str | int]]], dict[str, list[dict[str, str | int]]]]
):
    """Returns a tuple with the lp/mr leaderboards"""

    conn: sqlite3.Connection = sqlite3.connect("cfn-stats.db")

    today: datetime = datetime.now(tz=ZoneInfo("America/Los_Angeles")).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    latest_lp_scores: str = (
        """SELECT r.date, r.player_id, cm.player_name, r.char_id, r.lp, r.mr
        FROM ranking r
        INNER JOIN club_members cm ON cm.player_id = r.player_id
        GROUP BY r.date, r.player_id, r.char_id
        ORDER BY r.date DESC;"""
    )

    inactive_player_scores: str = (
        """SELECT hs.date, hs.player_id, hs.player_name, hs.selected_char as char_id, hs.lp, hs.mr
        FROM historic_stats hs
        GROUP BY hs.date, hs.player_id, char_id
        ORDER BY hs.date DESC;"""
    )

    latest_kudos_amounts_query: str = (
        """SELECT hs.date, hs.player_id, cm.player_name, hs.total_kudos
        FROM historic_stats hs
        INNER JOIN club_members cm ON cm.player_id = hs.player_id
        ORDER BY date DESC;"""
    )

    rank_df: pd.DataFrame = pd.read_sql_query(latest_lp_scores, conn)
    rank_df["char_id"] = rank_df["char_id"].replace(charid_map)
    rank_df["date"] = pd.to_datetime(rank_df["date"], format="ISO8601")
    rank_df = rank_df[rank_df["date"] > today]
    inactive_df: pd.DataFrame = pd.read_sql_query(inactive_player_scores, conn)
    inactive_df["char_id"] = inactive_df["char_id"].replace(charid_map)
    inactive_df["date"] = pd.to_datetime(inactive_df["date"], format="ISO8601")
    inactive_df = inactive_df[inactive_df["lp"] != -1]
    inactive_df = inactive_df[inactive_df["date"] > today]
    rank_df = pd.concat([inactive_df, rank_df]).drop_duplicates().reset_index(drop=True)

    hs_df: pd.DataFrame = pd.read_sql_query(latest_kudos_amounts_query, conn)
    hs_df["date"] = pd.to_datetime(hs_df["date"], format="ISO8601")
    hs_df = hs_df[hs_df["date"] > today]

    conn.close()

    lp_df: pd.DataFrame = rank_df.sort_values(by="lp", ascending=False)
    mr_df: pd.DataFrame = rank_df.sort_values(by="mr", ascending=False)
    mr_df = mr_df[mr_df["mr"] > 0]

    top_10_boards: dict[str, list[dict[str, str | int]]] = {
        "lp": [],
        "mr": [],
        "kudos": [],
    }

    top_10_grouped: dict[str, list[dict[str, str | int]]] = {
        "lp": [],
        "mr": [],
    }

    top_10_boards["lp"], top_10_grouped["lp"] = generate_lp_board(lp_df)
    top_10_boards["mr"], top_10_grouped["mr"] = generate_mr_board(mr_df)
    top_10_boards["kudos"] = generate_kudos_board(hs_df)

    return (top_10_boards, top_10_grouped)


def generate_mr_board(
    mr_df: pd.DataFrame,
) -> tuple[list[dict[str, str | int]], list[dict[str, str | int]]]:
    """Returns the sorted list for MR boards."""

    all_10_mr: list[dict[str, str | int]] = []
    group_10_mr: list[dict[str, str | int]] = []

    player_chars_mr: dict[str, list[tuple[str, int]]] = {}
    display_mr_rank = 1
    previous_mr = 0
    streak = 0

    for i, (_, player_id, player_name, char_id, _, mr) in enumerate(mr_df.values):
        i += 1

        if mr != previous_mr:
            display_mr_rank = i
        else:
            streak += 1
            display_mr_rank = i - streak

        previous_mr = mr

        all_10_mr.append(
            {
                "class": get_mr_class(mr),
                "player_name": player_name,
                "player_id": player_id,
                "char_id": char_id,
                "value": mr,
                "rank": display_mr_rank,
            }
        )

        if player_name not in player_chars_mr:
            player_chars_mr[player_name] = []

            group_10_mr.append(
                {
                    "class": get_mr_class(mr),
                    "player_name": player_name,
                    "player_id": player_id,
                    "char_id": char_id,
                    "value": mr,
                }
            )

    return (all_10_mr, group_10_mr)


def generate_lp_board(
    rank_df: pd.DataFrame,
) -> tuple[list[dict[str, str | int]], list[dict[str, str | int]]]:
    """Returns the sorted list for LP boards."""

    all_10_lp: list[dict[str, str | int]] = []
    group_10_lp: list[dict[str, str | int]] = []
    player_chars_lp: dict[str, bool] = {}

    display_lp_rank = 1
    previous_lp = 0
    streak = 0

    for i, (_, player_id, player_name, char_id, lp, _) in enumerate(rank_df.values):
        i += 1

        if lp != previous_lp:
            display_lp_rank = i
        else:
            streak += 1
            display_lp_rank = i - streak

        previous_lp = lp
        league = fetch_league_name(lp)
        all_10_lp.append(
            {
                "class": league["class"],
                "player_name": player_name,
                "player_id": player_id,
                "char_id": char_id,
                "value": lp,
                "rank": display_lp_rank,
                "league_name": league["name"],
            }
        )

        if player_name not in player_chars_lp:
            player_chars_lp[player_name] = True

            group_10_lp.append(
                {
                    "class": league["class"],
                    "player_name": player_name,
                    "player_id": player_id,
                    "char_id": char_id,
                    "value": lp,
                    "league_name": league["name"],
                }
            )

    return (all_10_lp, group_10_lp)


def generate_kudos_board(hs_df: pd.DataFrame) -> list[dict[str, str | int]]:
    """Returns the sorted list for the Kudos board."""

    kudos_leaders: list[dict[str, str | int]] = []

    top_kudos_df = hs_df.sort_values(by="total_kudos", ascending=False)

    for i, (_, player_id, player_name, total_kudos) in enumerate(top_kudos_df.values):
        class_name = "bottom" if i > 10 else ""
        class_name = class_name + " " + get_kudos_class(total_kudos)
        kudos_leaders.append(
            {
                "class": class_name,
                "player_name": player_name,
                "player_id": player_id,
                "value": total_kudos,
            }
        )

    return kudos_leaders
