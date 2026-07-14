CREATE TABLE editions (
    edition_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    year INT NOT NULL
);
CREATE TABLE nations (
    nation_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nation_name VARCHAR(100) NOT NULL UNIQUE
);
-- We model this as a many-to-many relations due to multihost years like 2002
CREATE TABLE edition_hosts (
    edition_id INT REFERENCES editions(edition_id) ON DELETE CASCADE,
    country_id INT REFERENCES nations(nation_id) ON DELETE RESTRICT,
    PRIMARY KEY (edition_id, country_id)
);
CREATE TABLE managers (
    manager_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    manager_name VARCHAR(150) NOT NULL 
);
CREATE TABLE matches (
    match_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    edition_id INT REFERENCES editions (edition_id) ON DELETE SET NULL,
    match_date DATE,
    round VARCHAR(100),
    venue VARCHAR(255),
    attendance INT,
    referee VARCHAR(150),
    officials_details TEXT, 
    home_nation_id INT REFERENCES nations(nation_id) ON DELETE RESTRICT,
    away_nation_id INT REFERENCES nations(nation_id) ON DELETE RESTRICT,
    home_manager_id INT REFERENCES managers(manager_id) ON DELETE SET NULL,
    away_manager_id INT REFERENCES managers(manager_id) ON DELETE SET NULL,
    home_captain VARCHAR(150),
    away_captain VARCHAR(150),
    home_score INT,
    away_score INT,
    home_xg NUMERIC(3,1), 
    away_xg NUMERIC(3,1),
    home_penalty INT,
    away_penalty INT,
    score_text VARCHAR(50),
    notes TEXT
);
CREATE TABLE match_events (
    event_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    match_id INT REFERENCES matches(match_id) ON DELETE CASCADE,
    nation_id INT REFERENCES nations(nation_id) ON DELETE RESTRICT,
    player_name VARCHAR(150) NOT NULL,
    minute INT,
    event_type VARCHAR(50) NOT NULL 
);