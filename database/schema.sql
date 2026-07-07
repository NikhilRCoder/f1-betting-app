-- ═══════════════════════════════════════════
-- PitWall — F1 Betting Analytics Platform
-- Full schema (DDL). SQLite dialect.
--   INTEGER PRIMARY KEY  -> auto-increment rowid
--   TEXT dates           -> ISO 8601 strings
--   REAL                 -> decimals
-- ═══════════════════════════════════════════

-- ═══════════════════════════════════════════
-- CORE ENTITIES
-- ═══════════════════════════════════════════

CREATE TABLE IF NOT EXISTS drivers (
    id INTEGER PRIMARY KEY,
    code TEXT NOT NULL,               -- e.g. 'VER', 'NOR'
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    full_name TEXT NOT NULL,
    nationality TEXT,
    date_of_birth TEXT,
    active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(code)
);

CREATE TABLE IF NOT EXISTS constructors (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    nationality TEXT,
    active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(name)
);

CREATE TABLE IF NOT EXISTS circuits (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    country TEXT NOT NULL,
    city TEXT,
    length_km REAL,
    corners INTEGER,
    drs_zones INTEGER,
    circuit_type TEXT,                -- 'permanent', 'street', 'hybrid'
    altitude_m REAL,
    latitude REAL,
    longitude REAL,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(name)
);

-- ═══════════════════════════════════════════
-- SEASON & RACE DATA
-- ═══════════════════════════════════════════

CREATE TABLE IF NOT EXISTS seasons (
    year INTEGER PRIMARY KEY,
    rounds INTEGER
);

CREATE TABLE IF NOT EXISTS races (
    id INTEGER PRIMARY KEY,
    season INTEGER NOT NULL,
    round INTEGER NOT NULL,
    circuit_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    date TEXT NOT NULL,
    time TEXT,
    laps INTEGER,
    weather TEXT,                      -- 'dry', 'wet', 'mixed', 'damp'
    safety_cars INTEGER DEFAULT 0,
    virtual_safety_cars INTEGER DEFAULT 0,
    red_flags INTEGER DEFAULT 0,
    avg_temp_c REAL,
    track_temp_c REAL,
    humidity_pct REAL,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (season) REFERENCES seasons(year),
    FOREIGN KEY (circuit_id) REFERENCES circuits(id),
    UNIQUE(season, round)
);

-- ═══════════════════════════════════════════
-- RESULTS & PERFORMANCE
-- ═══════════════════════════════════════════

CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY,
    race_id INTEGER NOT NULL,
    driver_id INTEGER NOT NULL,
    constructor_id INTEGER NOT NULL,
    grid INTEGER,
    position INTEGER,                 -- NULL = DNF/DNS/DSQ
    position_text TEXT,               -- 'Ret', 'DNS', 'DSQ', or position string
    points REAL DEFAULT 0,
    laps_completed INTEGER,
    status TEXT,                      -- 'Finished', 'Mechanical', 'Collision', etc.
    time_ms INTEGER,                  -- Race time in ms (winner)
    gap_to_leader_ms INTEGER,
    fastest_lap_rank INTEGER,
    fastest_lap_time_ms INTEGER,
    fastest_lap_speed REAL,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (race_id) REFERENCES races(id),
    FOREIGN KEY (driver_id) REFERENCES drivers(id),
    FOREIGN KEY (constructor_id) REFERENCES constructors(id)
);

CREATE TABLE IF NOT EXISTS qualifying (
    id INTEGER PRIMARY KEY,
    race_id INTEGER NOT NULL,
    driver_id INTEGER NOT NULL,
    constructor_id INTEGER NOT NULL,
    position INTEGER,
    q1_time_ms INTEGER,
    q2_time_ms INTEGER,
    q3_time_ms INTEGER,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (race_id) REFERENCES races(id),
    FOREIGN KEY (driver_id) REFERENCES drivers(id),
    FOREIGN KEY (constructor_id) REFERENCES constructors(id)
);

CREATE TABLE IF NOT EXISTS pit_stops (
    id INTEGER PRIMARY KEY,
    race_id INTEGER NOT NULL,
    driver_id INTEGER NOT NULL,
    stop_number INTEGER NOT NULL,
    lap INTEGER NOT NULL,
    duration_ms REAL,
    total_time_ms REAL,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (race_id) REFERENCES races(id),
    FOREIGN KEY (driver_id) REFERENCES drivers(id)
);

-- ═══════════════════════════════════════════
-- WEATHER (granular, per-race)
-- ═══════════════════════════════════════════

CREATE TABLE IF NOT EXISTS weather (
    id INTEGER PRIMARY KEY,
    race_id INTEGER NOT NULL,
    session TEXT NOT NULL,             -- 'FP1','FP2','FP3','Q','R','Sprint'
    condition TEXT,                    -- 'dry','wet','mixed'
    air_temp_c REAL,
    track_temp_c REAL,
    humidity_pct REAL,
    wind_speed_kph REAL,
    wind_direction TEXT,
    rain_probability REAL,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (race_id) REFERENCES races(id)
);

-- ═══════════════════════════════════════════
-- BETTING & PREDICTIONS
-- ═══════════════════════════════════════════

CREATE TABLE IF NOT EXISTS odds_history (
    id INTEGER PRIMARY KEY,
    race_id INTEGER NOT NULL,
    driver_id INTEGER NOT NULL,
    market TEXT NOT NULL,              -- 'race_winner','podium','top5','top10','pole','fastest_lap','h2h'
    bookmaker TEXT NOT NULL,
    odds_decimal REAL NOT NULL,
    odds_fractional TEXT,
    odds_american TEXT,
    implied_probability REAL,
    overround REAL,
    scraped_at TEXT DEFAULT (datetime('now')),
    source_url TEXT,
    FOREIGN KEY (race_id) REFERENCES races(id),
    FOREIGN KEY (driver_id) REFERENCES drivers(id)
);

CREATE TABLE IF NOT EXISTS model_predictions (
    id INTEGER PRIMARY KEY,
    race_id INTEGER NOT NULL,
    driver_id INTEGER NOT NULL,
    model_name TEXT NOT NULL,          -- 'elo','xgboost','logistic','ensemble'
    market TEXT NOT NULL,
    probability REAL NOT NULL,
    confidence REAL,                  -- 0-100
    features_used TEXT,               -- JSON blob of feature values
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (race_id) REFERENCES races(id),
    FOREIGN KEY (driver_id) REFERENCES drivers(id)
);

CREATE TABLE IF NOT EXISTS recommendations (
    id INTEGER PRIMARY KEY,
    race_id INTEGER NOT NULL,
    driver_id INTEGER NOT NULL,
    market TEXT NOT NULL,
    model_probability REAL NOT NULL,
    implied_probability REAL NOT NULL,
    expected_value REAL,
    edge_pct REAL,
    kelly_fraction REAL,
    confidence REAL,                  -- 0-100
    verdict TEXT NOT NULL,            -- 'STRONG_BET','SMALL_EDGE','NO_BET','AVOID'
    explanation TEXT,                 -- Human-readable reasoning
    actual_result TEXT,               -- Filled post-race for tracking
    profit_loss REAL,                 -- Filled post-race for tracking
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (race_id) REFERENCES races(id),
    FOREIGN KEY (driver_id) REFERENCES drivers(id)
);

CREATE TABLE IF NOT EXISTS manual_notes (
    id INTEGER PRIMARY KEY,
    race_id INTEGER,
    driver_id INTEGER,
    constructor_id INTEGER,
    circuit_id INTEGER,
    note TEXT NOT NULL,
    category TEXT,                    -- 'insight','risk','strategy','general'
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (race_id) REFERENCES races(id),
    FOREIGN KEY (driver_id) REFERENCES drivers(id),
    FOREIGN KEY (constructor_id) REFERENCES constructors(id),
    FOREIGN KEY (circuit_id) REFERENCES circuits(id)
);

-- ═══════════════════════════════════════════
-- TRACKING & P&L
-- ═══════════════════════════════════════════

CREATE TABLE IF NOT EXISTS bet_tracker (
    id INTEGER PRIMARY KEY,
    race_id INTEGER NOT NULL,
    driver_id INTEGER NOT NULL,
    market TEXT NOT NULL,
    bookmaker TEXT,
    odds_taken REAL NOT NULL,
    stake REAL NOT NULL,
    recommendation_id INTEGER,
    result TEXT,                       -- 'win','loss','void','pending'
    payout REAL,
    profit_loss REAL,
    notes TEXT,
    placed_at TEXT DEFAULT (datetime('now')),
    settled_at TEXT,
    FOREIGN KEY (race_id) REFERENCES races(id),
    FOREIGN KEY (driver_id) REFERENCES drivers(id),
    FOREIGN KEY (recommendation_id) REFERENCES recommendations(id)
);

-- ═══════════════════════════════════════════
-- INDEXES
-- ═══════════════════════════════════════════

CREATE INDEX IF NOT EXISTS idx_results_race ON results(race_id);
CREATE INDEX IF NOT EXISTS idx_results_driver ON results(driver_id);
CREATE INDEX IF NOT EXISTS idx_results_constructor ON results(constructor_id);
CREATE INDEX IF NOT EXISTS idx_qualifying_race ON qualifying(race_id);
CREATE INDEX IF NOT EXISTS idx_qualifying_driver ON qualifying(driver_id);
CREATE INDEX IF NOT EXISTS idx_odds_race ON odds_history(race_id);
CREATE INDEX IF NOT EXISTS idx_odds_driver ON odds_history(driver_id);
CREATE INDEX IF NOT EXISTS idx_odds_market ON odds_history(market);
CREATE INDEX IF NOT EXISTS idx_predictions_race ON model_predictions(race_id);
CREATE INDEX IF NOT EXISTS idx_recommendations_race ON recommendations(race_id);
CREATE INDEX IF NOT EXISTS idx_bet_tracker_race ON bet_tracker(race_id);
CREATE INDEX IF NOT EXISTS idx_pit_stops_race ON pit_stops(race_id);
