create table manager (
	manager_id smallint generated always as identity primary key,
	manager_name varchar (100) not NULL 
);
create table nation (
	nation_id smallint generated always as identity primary key,
	nation_name varchar (100) not NULL,
	federation varchar (100) not NULL
);
create table date (
	date_id smallint generated always as identity primary key,
	date date not NULL,
	year smallint not NULL,
	decade smallint not NULL,
	century smallint not NULL
);
create table fact_match (
	home_manager_id smallint references manager(manager_id) on delete restrict,
	away_manager_id smallint references manager(manager_id) on delete restrict,
	date_id smallint references date(date_id) on delete restrict,
	home_nation_id smallint references nation(nation_id) on delete restrict,
	away_nation_id smallint references nation(nation_id) on delete restrict,
	round varchar(100) not NULL,
	primary key (home_manager_id, away_manager_id, date_id, home_nation_id, away_nation_id, round),
	attendance int not NULL,
    home_score smallint not NULL,
    away_score smallint not NULL,
    home_xg NUMERIC(4,2), 
    away_xg NUMERIC(4,2),
    home_penalty smallint,
    away_penalty smallint, --these 2 parameters refer to the final penalty shootout, if any
    n_home_yellow_card smallint,
    n_home_red_card smallint,
    n_away_yellow_card smallint,
    n_away_red_card smallint,
    n_home_penalty_miss smallint,
    n_away_penalty_miss smallint,
    n_home_penalty_goal smallint,
    n_away_penalty_goal smallint --these 4 parameters refer to penalties given during the match, if any
);