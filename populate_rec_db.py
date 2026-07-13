"""
Run with: python populate_rec_db.py --csv matches_clean.csv --dbname world_cups_recdb 
        --user postgres --password *** --host localhost --port 5432
Do this AFTER reconciled_database_schema.sql
"""
import argparse
import ast
import re
import sys
import unicodedata
import pandas as pd
import psycopg

def clean_text(x):
   #converts NaN strings into None and removes ambiguous characters
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return None
    s = str(x).replace("\xa0", " ").strip()
    if not s: return None
    #Doing this ensures that event with different accents the strings
    #are treated with the same name, if needed.
    s = unicodedata.normalize('NFD',s)
    s = "".join(c for c in s if unicodedata.category(c) != 'Mn')
    return s

def to_none(x):
    # converts all NaN to None
    if x is None:
        return None
    if isinstance(x, float) and pd.isna(x):
        return None
    return x

def to_int(x):
    x = to_none(x)
    return int(x) if x is not None else None

def parse_minute(raw):
    #Parse strings like "90+3" in their minute integer correspondancy
    if raw is None:
        return None
    raw = str(raw).replace("&rsquor;", "").strip()
    m = re.match(r"(\d+)(?:\+(\d+))?", raw)
    if not m:
        return None
    base = int(m.group(1))
    extra = int(m.group(2)) if m.group(2) else 0
    return base + extra

_MARKER_RE = re.compile(r"\s*\([A-Z]+\)\s*$")

def parse_simple_events(raw):
    #Parse more events into several events
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return []
    events = []
    for chunk in str(raw).split("|"):
        if "·" not in chunk:
            continue
        name_part, minute_part = chunk.rsplit("·", 1)
        name = clean_text(_MARKER_RE.sub("", name_part))
        minute = parse_minute(minute_part)
        if name:
            events.append((name, minute))
    return events

def parse_long_events(raw, name_index=2):
    #Like the previous method but with long fields
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return []
    try:
        items = ast.literal_eval(raw)
    except (ValueError, SyntaxError):
        return []
    events = []
    for item in items:
        parts = item.split("|")
        if len(parts) <= name_index:
            continue
        name = clean_text(parts[name_index])
        minute = parse_minute(parts[0])
        if name:
            events.append((name, minute))
    return events

SIMPLE_EVENT_COLUMNS = {
    "home_goal": "HomeGoal",
    "away_goal": "AwayGoal",
    "home_own_goal": "HomeOwnGoal",
    "away_own_goal": "AwayOwnGoal",
    "home_penalty_goal": "HomePenaltyGoal",
    "away_penalty_goal": "AwayPenaltyGoal",
    "home_red_card": "HomeRedCard",
    "away_red_card": "AwayRedCard",
    "home_yellow_red_card": "HomeRedCard",
    "away_yellow_red_card": "AwayRedCard",
}

LONG_EVENT_COLUMNS = {
    "home_penalty_miss_long": "HomePenaltyMiss",
    "away_penalty_miss_long": "AwayPenaltyMiss",
    "home_penalty_shootout_goal_long": "HomePenaltyShootoutGoal",
    "away_penalty_shootout_goal_long": "AwayPenaltyShootoutGoal",
    "home_penalty_shootout_miss_long": "HomePenaltyShootoutMiss",
    "away_penalty_shootout_miss_long": "AwayPenaltyShootoutMiss",
    "home_yellow_card_long": "HomeYellowCard",
    "away_yellow_card_long": "AwayYellowCard",
    "home_substitute_in_long": "HomeSubstitutes",
    "away_substitute_in_long": "AwaySubstitues",
}

def side_of(column_name):
    return "home" if column_name.startswith("home_") else "away"

def populate_nations(cur, df):
    names = sorted({clean_text(n) for n in pd.concat([df["home_team"], df["away_team"]]) if clean_text(n)})
    nation_id = {}
    for name in names:
        cur.execute(
            """
            INSERT INTO nations (nation_name) VALUES (%s)
            ON CONFLICT (nation_name) DO UPDATE SET nation_name = EXCLUDED.nation_name
            RETURNING nation_id
            """,
            (name,),
        )
        nation_id[name] = cur.fetchone()[0]
    return nation_id

def populate_managers(cur, df):
    names = sorted({clean_text(n) for n in pd.concat([df["home_manager"], df["away_manager"]]) if clean_text(n)})
    manager_id = {}
    for name in names:
        cur.execute(
            "INSERT INTO managers (manager_name) VALUES (%s) RETURNING manager_id",
            (name,),
        )
        manager_id[name] = cur.fetchone()[0]
    return manager_id

def populate_editions(cur, df):
    years = sorted({int(y) for y in df["Year"].unique()})
    edition_id = {}
    for year in years:
        cur.execute(
            "INSERT INTO editions (year) VALUES (%s) RETURNING edition_id",
            (year,),
        )
        edition_id[year] = cur.fetchone()[0]
    print(f"[editions] inserite {len(edition_id)} righe")
    return edition_id

def populate_edition_hosts(cur, df, edition_id, nation_id):
    year_to_host = df.drop_duplicates("Year").set_index("Year")["Host"]
    rows = []
    for year, host_field in year_to_host.items():
        for host_name in str(host_field).split(","):
            host_name = clean_text(host_name)
            if not host_name:
                continue
            rows.append((edition_id[int(year)], nation_id[host_name]))
    cur.executemany(
        "INSERT INTO edition_hosts (edition_id, country_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
        rows)

INSERT_MATCH_SQL = """
INSERT INTO matches (
    edition_id, match_date, round, venue, attendance, referee, officials_details,
    home_nation_id, away_nation_id, home_manager_id, away_manager_id,
    home_captain, away_captain, home_score, away_score, home_xg, away_xg,
    home_penalty, away_penalty, score_text, notes
) VALUES (
    %(edition_id)s, %(match_date)s, %(round)s, %(venue)s, %(attendance)s, %(referee)s, %(officials_details)s,
    %(home_nation_id)s, %(away_nation_id)s, %(home_manager_id)s, %(away_manager_id)s,
    %(home_captain)s, %(away_captain)s, %(home_score)s, %(away_score)s, %(home_xg)s, %(away_xg)s,
    %(home_penalty)s, %(away_penalty)s, %(score_text)s, %(notes)s
)
RETURNING match_id
"""

INSERT_EVENTS_SQL = """
INSERT INTO match_events (match_id, nation_id, player_name, minute, event_type)
VALUES (%s, %s, %s, %s, %s)
"""

def build_match_row(row, edition_id, nation_id, manager_id):
    return {
        "edition_id": edition_id[int(row["Year"])],
        "match_date": row["Date"],
        "round": clean_text(row["Round"]),
        "venue": clean_text(row["Venue"]),
        "attendance": to_int(row["Attendance"]),
        "referee": clean_text(row["Referee"]),
        "officials_details": clean_text(row["Officials"]),
        "home_nation_id": nation_id[clean_text(row["home_team"])],
        "away_nation_id": nation_id[clean_text(row["away_team"])],
        "home_manager_id": manager_id.get(clean_text(row["home_manager"])),
        "away_manager_id": manager_id.get(clean_text(row["away_manager"])),
        "home_captain": clean_text(row["home_captain"]),
        "away_captain": clean_text(row["away_captain"]),
        "home_score": to_int(row["home_score"]),
        "away_score": to_int(row["away_score"]),
        "home_xg": to_none(row["home_xg"]),
        "away_xg": to_none(row["away_xg"]),
        "home_penalty": to_int(row["home_penalty"]),
        "away_penalty": to_int(row["away_penalty"]),
        "score_text": clean_text(row["Score"]),
        "notes": clean_text(row["Notes"]),
    }


def extract_match_events(row, match_id, nation_id):
    #Extracts the correct MatchEvents
    events = []

    for col, event_type in SIMPLE_EVENT_COLUMNS.items():
        side = side_of(col)
        team_name = clean_text(row["home_team"] if side == "home" else row["away_team"])
        nid = nation_id[team_name]
        for player_name, minute in parse_simple_events(row[col]):
            events.append((match_id, nid, player_name, minute, event_type))

    for col, event_type in LONG_EVENT_COLUMNS.items():
        side = side_of(col)
        team_name = clean_text(row["home_team"] if side == "home" else row["away_team"])
        nid = nation_id[team_name]
        for player_name, minute in parse_long_events(row[col]):
            events.append((match_id, nid, player_name, minute, event_type))

    return events

def populate_matches_and_events(cur, df, edition_id, nation_id, manager_id):
    for _, row in df.iterrows():
        match_row = build_match_row(row, edition_id, nation_id, manager_id)
        cur.execute(INSERT_MATCH_SQL, match_row)
        match_id = cur.fetchone()[0]
    
        events = extract_match_events(row, match_id, nation_id)
        if events:
            cur.executemany(INSERT_EVENTS_SQL, events)

def main():
    parser = argparse.ArgumentParser(description="Populate the reconciled database schema")
    parser.add_argument("--csv", default="matches_clean.csv")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", default="5432")
    parser.add_argument("--dbname", required=True)
    parser.add_argument("--user", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()

    df = pd.read_csv(args.csv)

    conn = psycopg.connect(
        host=args.host, port=args.port, dbname=args.dbname,
        user=args.user, password=args.password,
    )
    try:
        with conn:
            with conn.cursor() as cur:
                nation_id = populate_nations(cur, df)
                manager_id = populate_managers(cur, df)
                edition_id = populate_editions(cur, df)
                populate_edition_hosts(cur, df, edition_id, nation_id)
                populate_matches_and_events(cur, df, edition_id, nation_id, manager_id)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()