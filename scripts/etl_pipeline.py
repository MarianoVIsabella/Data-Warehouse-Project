#Extraction: extract what you need from world_cups_recdb schema
#Transformation: 
# Add the correct Federation to each nation
# Create the Date -> Year -> Decade -> Century hierarchy for Date Dimension
# Compute the n_measures
#Load: Load everything to world_cups_star_schema
import logging
from collections import defaultdict
import psycopg
from psycopg.rows import dict_row
import os
from dotenv import load_dotenv
load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("etl")
passw=os.environ["POSTGRES_PASSWORD"]
port=os.environ["POSTGRES_PORT"]
SRC_DSN = "dbname=world_cups_recdb user=postgres password=" + passw +" host=localhost port=" + port
DST_DSN = "dbname=world_cups_star_schema user=postgres password=" + passw +" host=localhost port=" + port
CATEGORY_TO_MEASURE_COLUMN = {
    "HomeYellowCard": "n_home_yellow_card",
    "AwayYellowCard": "n_away_yellow_card",
    "HomeRedCard": "n_home_red_card",
    "AwayRedCard": "n_away_red_card",
    "HomePenaltyMiss": "n_home_penalty_miss",
    "AwayPenaltyMiss": "n_away_penalty_miss",
    "HomePenaltyGoal": "n_home_penalty_goal",
    "AwayPenaltyGoal": "n_away_penalty_goal",
}
EVENT_CATEGORY= list(CATEGORY_TO_MEASURE_COLUMN.keys())
MEASURE_COLUMNS = list(CATEGORY_TO_MEASURE_COLUMN.values())

NATION_FEDERATION = {
    # UEFA
    "Germany": "UEFA", "West Germany": "UEFA", "Germany DR": "UEFA",
    "Italy": "UEFA", "France": "UEFA", "England": "UEFA", "Spain": "UEFA",
    "Netherlands": "UEFA", "Portugal": "UEFA", "Belgium": "UEFA",
    "Croatia": "UEFA", "Switzerland": "UEFA", "Sweden": "UEFA",
    "Poland": "UEFA", "Austria": "UEFA", "Hungary": "UEFA",
    "Czechoslovakia": "UEFA", "Czechia": "UEFA", "Slovakia": "UEFA",
    "Denmark": "UEFA", "Norway": "UEFA", "Republic of Ireland": "UEFA",
    "Northern Ireland": "UEFA", "Scotland": "UEFA", "Wales": "UEFA",
    "Romania": "UEFA", "Bulgaria": "UEFA", "Yugoslavia": "UEFA",
    "Serbia": "UEFA", "Slovenia": "UEFA", "Bosnia and Herzegovina": "UEFA", 
    "Ukraine": "UEFA", "Russia": "UEFA", "Soviet Union": "UEFA", 
    "Greece": "UEFA", "Turkiye": "UEFA", "Iceland": "UEFA",
    "Israel": "UEFA", 
    # CONMEBOL
    "Brazil": "CONMEBOL", "Argentina": "CONMEBOL", "Uruguay": "CONMEBOL",
    "Chile": "CONMEBOL", "Paraguay": "CONMEBOL", "Peru": "CONMEBOL",
    "Colombia": "CONMEBOL", "Ecuador": "CONMEBOL", "Bolivia": "CONMEBOL",
    # CONCACAF
    "Mexico": "CONCACAF", "United States": "CONCACAF", "Costa Rica": "CONCACAF", 
    "Honduras": "CONCACAF", "Jamaica": "CONCACAF", "Canada": "CONCACAF", 
    "Cuba": "CONCACAF", "El Salvador": "CONCACAF", "Haiti": "CONCACAF", 
    "Trinidad and Tobago": "CONCACAF", "Panama": "CONCACAF",
    # CAF
    "Egypt": "CAF", "Morocco": "CAF", "Tunisia": "CAF", "Algeria": "CAF",
    "Nigeria": "CAF", "Cameroon": "CAF", "Senegal": "CAF", "Ghana": "CAF",
    "Cote d'Ivoire": "CAF", "South Africa": "CAF", "DR. Congo": "CAF", 
    "Togo": "CAF", "Angola": "CAF",
    # AFC
    "Korea Republic": "AFC", "Korea DPR": "AFC", "Japan": "AFC",
    "Saudi Arabia": "AFC", "IR Iran": "AFC", "Iraq": "AFC", "China PR": "AFC",
    "Kuwait": "AFC", "United Arab Emirates": "AFC", "Qatar": "AFC", "Indonesia": "AFC",
    "Australia": "AFC", #from 2006 it's affiliated to AFC. Before, it was OFC.
    # OFC
    "New Zealand": "OFC",
}
DEFAULT_FEDERATION = "UNKNOWN"

def get_federation(nation_name: str) -> str:
    fed = NATION_FEDERATION.get(nation_name)
    if fed is None:
        log.warning("No federation found for nation %r -> assigned %r", nation_name, DEFAULT_FEDERATION)
        return DEFAULT_FEDERATION
    return fed

def decade_of(year: int) -> int:
    return (year // 10) * 10

def century_of(year: int) -> int:
    return (year - 1) // 100 + 1

def extract(src_conn):
    with src_conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT nation_id, nation_name FROM nations")
        nations = cur.fetchall()

        cur.execute("SELECT manager_id, manager_name FROM managers")
        managers = cur.fetchall()

        cur.execute("""
            SELECT match_id, match_date, round, attendance,
                   home_nation_id, away_nation_id,
                   home_manager_id, away_manager_id,
                   home_score, away_score, home_xg, away_xg,
                   home_penalty, away_penalty
            FROM matches
        """)
        matches = cur.fetchall()

        cur.execute("SELECT event_id, match_id, nation_id, event_type FROM match_events")
        events = cur.fetchall()

    log.info("Extracted: %d nations, %d managers, %d matches, %d events",
              len(nations), len(managers), len(matches), len(events))
    return nations, managers, matches, events

def transform_nations(nations):
    return [
        {
            "nation_id": n["nation_id"],
            "nation_name": n["nation_name"],
            "federation": get_federation(n["nation_name"]),
        }
        for n in nations
    ]

def transform_dates(matches):
    dates = {}
    for m in matches:
        d = m["match_date"]
        if d is None:
            continue
        if d not in dates:
            year = d.year
            dates[d] = {
                "date": d,
                "year": year,
                "decade": decade_of(year),
                "century": century_of(year),
            }
    log.info("Built %d dates inside Date DT.", len(dates))
    return dates

def compute_event_measures(events):
    counts = defaultdict(lambda: defaultdict(int))
    ignored_categories = set()

    for e in events:
        category = e["event_type"]
        column = CATEGORY_TO_MEASURE_COLUMN.get(category)
        if column is None:
            ignored_categories.add(category)
            continue
        counts[e["match_id"]][column] += 1

    if ignored_categories:
        log.info("The following events should not be counted for measures: %s", sorted(ignored_categories))

    return counts


def transform_matches(matches, event_counts):
    rows = []
    skipped = defaultdict(int)

    for m in matches:
        if m["match_date"] is None:
            skipped["match_date NULL"] += 1
            continue
        if m["round"] is None:
            skipped["round NULL"] += 1
            continue
        if m["home_manager_id"] is None or m["away_manager_id"] is None:
            skipped["manager NULL"] += 1
            continue
        if m["home_score"] is None or m["away_score"] is None:
            skipped["score NULL"] += 1
            continue

        counts = event_counts.get(m["match_id"], {})
        row = {
            "match_id": m["match_id"], 
            "match_date": m["match_date"],
            "round": m["round"],
            "attendance": m["attendance"] if m["attendance"] is not None else 0,
            "home_nation_id": m["home_nation_id"],
            "away_nation_id": m["away_nation_id"],
            "home_manager_id": m["home_manager_id"],
            "away_manager_id": m["away_manager_id"],
            "home_score": m["home_score"],
            "away_score": m["away_score"],
            "home_xg": m["home_xg"],
            "away_xg": m["away_xg"],
            "home_penalty": m["home_penalty"],
            "away_penalty": m["away_penalty"],
        }
        for col in MEASURE_COLUMNS:
            row[col] = counts.get(col, 0)

        rows.append(row)

    if skipped:
        log.warning("The following matches cannot be loaded due to some NULL in dimensions: %s (total %d)",
                     dict(skipped), sum(skipped.values()))
    log.info("Number of matches ready for the Load: %d", len(rows))
    return rows

def load_nations(dst_conn, nations):
    id_map = {}
    with dst_conn.cursor() as cur:
        for n in nations:
            cur.execute(
                "INSERT INTO nation (nation_name, federation) VALUES (%s, %s) RETURNING nation_id",
                (n["nation_name"], n["federation"]),
            )
            id_map[n["nation_id"]] = cur.fetchone()[0]
    log.info("Loaded %d nations in the DW", len(id_map))
    return id_map


def load_managers(dst_conn, managers):
    id_map = {}
    with dst_conn.cursor() as cur:
        for m in managers:
            cur.execute(
                "INSERT INTO manager (manager_name) VALUES (%s) RETURNING manager_id",
                (m["manager_name"],),
            )
            id_map[m["manager_id"]] = cur.fetchone()[0]
    log.info("Loaded %d manager in the DW", len(id_map))
    return id_map


def load_dates(dst_conn, dates):
    id_map = {}
    with dst_conn.cursor() as cur:
        for d, rec in dates.items():
            cur.execute(
                "INSERT INTO date (date, year, decade, century) VALUES (%s, %s, %s, %s) RETURNING date_id",
                (rec["date"], rec["year"], rec["decade"], rec["century"]),
            )
            id_map[d] = cur.fetchone()[0]
    log.info("Loaded %d match_dates in the DW", len(id_map))
    return id_map

def load_fact_match(dst_conn, match_rows, nation_id_map, manager_id_map, date_id_map):
    insert_sql = """
        INSERT INTO fact_match (
            home_manager_id, away_manager_id, date_id, home_nation_id, away_nation_id, round,
            attendance, home_score, away_score, home_xg, away_xg, home_penalty, away_penalty,
            n_home_yellow_card, n_home_red_card, n_away_yellow_card, n_away_red_card,
            n_home_penalty_miss, n_away_penalty_miss, n_home_penalty_goal, n_away_penalty_goal
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (home_manager_id, away_manager_id, date_id, home_nation_id, away_nation_id, round)
        DO NOTHING
    """
    inserted = 0
    collided = 0
    with dst_conn.cursor() as cur:
        for r in match_rows:
            params = (
                manager_id_map[r["home_manager_id"]],
                manager_id_map[r["away_manager_id"]],
                date_id_map[r["match_date"]],
                nation_id_map[r["home_nation_id"]],
                nation_id_map[r["away_nation_id"]],
                r["round"],
                r["attendance"],
                r["home_score"],
                r["away_score"],
                r["home_xg"],
                r["away_xg"],
                r["home_penalty"],
                r["away_penalty"],
                r["n_home_yellow_card"],
                r["n_home_red_card"],
                r["n_away_yellow_card"],
                r["n_away_red_card"],
                r["n_home_penalty_miss"],
                r["n_away_penalty_miss"],
                r["n_home_penalty_goal"],
                r["n_away_penalty_goal"],
            )
            cur.execute(insert_sql, params)
            if cur.rowcount == 0:
                collided += 1
                log.warning("fact_match: primary key collision for match_id=%s (ON CONFLICT discarded the row)",
                             r["match_id"])
            else:
                inserted += 1

    log.info("fact_match: %d new rows, %d collisions detected", inserted, collided)

def run():
    with psycopg.connect(SRC_DSN) as src_conn, psycopg.connect(DST_DSN) as dst_conn:
        # Extraction
        nations, managers, matches, events = extract(src_conn)
        # Transformation
        t_nations = transform_nations(nations)
        t_dates = transform_dates(matches)
        event_counts = compute_event_measures(events)
        t_matches = transform_matches(matches, event_counts)
        # Load
        nation_id_map = load_nations(dst_conn, t_nations)
        manager_id_map = load_managers(dst_conn, managers)
        date_id_map = load_dates(dst_conn, t_dates)
        load_fact_match(dst_conn, t_matches, nation_id_map, manager_id_map, date_id_map)

        dst_conn.commit()
        log.info("ETL pipeline ended")


if __name__ == "__main__":
    run()