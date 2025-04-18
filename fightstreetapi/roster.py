"""fightstreetapi - backend for fightstreeter.com"""

from apiflask import APIBlueprint
from marshmallow_dataclass import dataclass

from . import db

bp = APIBlueprint("roster", __name__, url_prefix="/roster")


@dataclass
class Player:
    """Class object for a club member"""

    player_name: str
    player_id: str
    last_played: str


def generate_member_list() -> list[Player]:
    """Returns the list of club players with sorting"""
    all_members_sql = """SELECT hs.player_name, hs.player_id, hs.last_played
        FROM historic_stats hs
        LEFT JOIN club_members cm ON cm.player_id = hs.player_id
        WHERE hs.date = ? AND cm.hidden = 0
        ORDER BY hs.last_played DESC, hs.player_name;"""

    all_members = db.query_db(all_members_sql, (db.latest_stats_date(),))
    all_members_list = [Player(*row) for row in all_members] if all_members else []

    return all_members_list


@bp.get("/")
@bp.output(Player.Schema(many=True))  # type: ignore # pylint: disable=no-member
@bp.doc(summary="Get club members", description="Returns a list of every club member.")
def get_club_roster() -> list[Player]:
    """Current club roster"""
    all_members_list = generate_member_list()
    return all_members_list
