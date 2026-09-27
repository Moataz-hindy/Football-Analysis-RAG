-- Multi-Tenant Profile, Persona & Persistent Memory Migration for PostgreSQL 16
-- Logical isolation using profile_id foreign keys and cascade rules.

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    display_name TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS profiles (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    display_name TEXT NOT NULL,
    profile_type TEXT NOT NULL DEFAULT 'scout',
    football_focus TEXT DEFAULT 'Player Recruitment & Positional Profiling',
    experience_level TEXT DEFAULT 'Professional',
    preferred_analysis_style TEXT DEFAULT 'Statistical & Quantitative',
    preferred_report_type TEXT DEFAULT 'Scout Report',
    favorite_competitions TEXT DEFAULT '["UEFA Champions League", "FIFA World Cup", "Premier League"]',
    favorite_teams TEXT DEFAULT '["Argentina", "Manchester City", "Arsenal"]',
    favorite_analysis_areas TEXT DEFAULT '["Tactical Structures", "Pressing Metrics", "xG Differential"]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id)
);

CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    profile_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE TABLE IF NOT EXISTS profile_memory (
    id TEXT PRIMARY KEY,
    profile_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    memory_type TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'explicit',
    confidence REAL DEFAULT 1.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS profile_personas (
    id TEXT PRIMARY KEY,
    profile_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    field TEXT NOT NULL,
    background TEXT NOT NULL,
    stance TEXT NOT NULL,
    communication_style TEXT NOT NULL,
    expertise TEXT NOT NULL, -- JSON array of strings
    priorities TEXT NOT NULL, -- JSON array of strings
    source TEXT NOT NULL DEFAULT 'user', -- 'user' or 'generated'
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS profile_reports (
    id TEXT PRIMARY KEY,
    profile_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    discussion_id TEXT,
    report_type TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    sections TEXT NOT NULL, -- JSON formatted sections
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_discussions (
    id TEXT PRIMARY KEY,
    profile_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    discussion_id TEXT NOT NULL,
    topic TEXT NOT NULL,
    num_rounds INT DEFAULT 3,
    num_agents INT DEFAULT 6,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for tenant isolation and query performance
CREATE INDEX IF NOT EXISTS idx_profiles_user_id ON profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token);
CREATE INDEX IF NOT EXISTS idx_profile_memory_profile_id ON profile_memory(profile_id);
CREATE INDEX IF NOT EXISTS idx_profile_personas_profile_id ON profile_personas(profile_id);
CREATE INDEX IF NOT EXISTS idx_profile_reports_profile_id ON profile_reports(profile_id);
CREATE INDEX IF NOT EXISTS idx_user_discussions_profile_id ON user_discussions(profile_id);
