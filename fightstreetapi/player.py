"""player stats"""

from dataclasses import field

from apiflask import APIBlueprint, abort
from apiflask.validators import OneOf
from marshmallow_dataclass import dataclass

from constants import charid_map

from . import db

bp = APIBlueprint("player", __name__, url_prefix="/player")


@dataclass
class PlayerHistoricStats:  # pylint: disable=too-many-instance-attributes
    """Player's profile schema"""

    date: str
    player_name: str
    player_id: str
    date_joined: str
    selected_character: str
    selected_lp: int
    selected_mr: int
    hub_matches: int
    ranked_matches: int
    casual_matches: int
    custom_matches: int
    hub_time: int
    ranked_time: int
    casual_time: int
    custom_time: int
    extreme_time: int
    versus_time: int
    practice_time: int
    arcade_time: int
    wt_time: int
    total_kudos: int
    thumbs: int
    last_played: str
    profile_tagline: str
    title_text: str
    title_plate: str


@dataclass
class DateRangeRequest:
    """Historic stats for a player between two given dates"""

    date_start: str = field(
        metadata={
            "required": True,
            "validate": OneOf(db.dates_with_data()),
            "metadata": {"example": "2025-04-01"},
        }
    )
    date_end: str = field(
        metadata={
            "required": True,
            "validate": OneOf(db.dates_with_data()),
            "metadata": {"example": "2025-04-17"},
        }
    )


@dataclass
class CharacterRanking:
    """Individual character LP/MR stats"""

    date: str
    char_id: str
    lp: str
    mr: str


@bp.post("/overview/<string:player_id>")
@bp.input(DateRangeRequest.Schema, location="json", arg_name="dates")  # type: ignore # pylint: disable=maybe-no-member
@bp.output(PlayerHistoricStats.Schema(many=True))  # type: ignore # pylint: disable=maybe-no-member
def player_historicstats(player_id, dates) -> list[PlayerHistoricStats]:
    """Player's historic stats between two dates"""

    # Support username or id, start with username
    historic_stats_daterange_sql: str = (
        """SELECT date, hs.player_name, hs.player_id, joined_at date_joined, selected_char as selected_character,
                lp as selected_lp, mr as selected_mr, hub_matches, ranked_matches, casual_matches,
                custom_matches, hub_time, ranked_time, casual_time, custom_time, extreme_time,
                versus_time, practice_time, arcade_time, wt_time, total_kudos, thumbs, last_played,
                profile_tagline, title_text, title_plate
            FROM historic_stats hs
            INNER JOIN club_members cm ON cm.player_id = hs.player_id
            WHERE hs.date BETWEEN ? AND ? AND hs.player_id = ?"""
    )

    results = db.query_db(
        historic_stats_daterange_sql, (dates.date_start, dates.date_end, player_id)
    )

    if not results:
        abort(404)

    player_overview = [PlayerHistoricStats(**result) for result in results]
    for historicstats_entry in player_overview:
        historicstats_entry.selected_character = charid_map[
            historicstats_entry.selected_character
        ]

    return player_overview


@bp.post("/ranking/<string:player_id>")
@bp.input(DateRangeRequest.Schema, location="json", arg_name="dates")  # type: ignore # pylint: disable=maybe-no-member
@bp.output(CharacterRanking.Schema(many=True))  # type: ignore # pylint: disable=maybe-no-member
@bp.doc(
    summary="Player's characters' stats",
    description="Returns the LP/MR for every character played by a given user.",
)
def ranking_stats_range(player_id, dates) -> list[CharacterRanking]:
    """Stats on every character played by a given user"""

    # Support username or id, start with username
    player_characters_sql: str = (
        """SELECT date, char_id, lp, mr
            FROM ranking
            WHERE date BETWEEN ? AND ? AND player_id = ?;"""
    )

    result = db.query_db(
        player_characters_sql, (dates.date_start, dates.date_end, player_id)
    )

    if not result:
        abort(404)

    list_of_char_ranks = [CharacterRanking(**row) for row in result]

    return list_of_char_ranks
