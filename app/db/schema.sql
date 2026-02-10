-- ============================================================================
-- JMA Knowledge Base - Database Schema (FastAPI + Psycopg2)
-- ============================================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
-- Note: 'vector' extension requires pgvector installed on the server.
-- CREATE EXTENSION IF NOT EXISTS vector; 

-- Helper Functions
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 1. Core Identity & Access
-- ============================================================================

CREATE TABLE IF NOT EXISTS clients (
    client_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    industry VARCHAR(100),
    relationship_start_date DATE,
    metadata JSONB DEFAULT '{}'::jsonb,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    salt VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    client_access INTEGER[] DEFAULT '{}',
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    is_superuser BOOLEAN DEFAULT false,
    last_login TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_sessions (
    session_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_log (
    log_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100),
    resource_id INTEGER,
    client_id INTEGER REFERENCES clients(client_id),
    details JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- 2. Business Logic (Core)
-- ============================================================================

CREATE TABLE IF NOT EXISTS stakeholders (
    stakeholder_id SERIAL PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES clients(client_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(100),
    email VARCHAR(255),
    tone VARCHAR(50) NOT NULL DEFAULT 'neutral',
    tone_analysis JSONB DEFAULT '{}',
    last_interaction TIMESTAMP,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT unique_stakeholder UNIQUE(client_id, name, email)
);

CREATE TABLE IF NOT EXISTS knowledge_entries (
    entry_id SERIAL PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES clients(client_id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    entry_type VARCHAR(50) NOT NULL,
    source VARCHAR(255),
    -- Using float8[] as fallback for vector(384) if pgvector is missing
    embedding float8[], 
    metadata JSONB DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    daaeg_phase VARCHAR(50),
    stakeholder_ids INTEGER[] DEFAULT '{}',
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS templates (
    template_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    current_version_id INTEGER,
    is_active BOOLEAN DEFAULT true,
    metadata JSONB DEFAULT '{}',
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS template_versions (
    version_id SERIAL PRIMARY KEY,
    template_id INTEGER NOT NULL REFERENCES templates(template_id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    dynamic_fields JSONB DEFAULT '{}',
    changelog TEXT,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT unique_template_version UNIQUE(template_id, version_number)
);

CREATE TABLE IF NOT EXISTS deliverable_workflows (
    workflow_id SERIAL PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES clients(client_id) ON DELETE CASCADE,
    deliverable_type VARCHAR(100) NOT NULL,
    template_id INTEGER REFERENCES templates(template_id),
    file_path VARCHAR(500),
    status VARCHAR(50) NOT NULL DEFAULT 'draft',
    generation_metadata JSONB DEFAULT '{}',
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS deliverable_reviews (
    review_id SERIAL PRIMARY KEY,
    workflow_id INTEGER NOT NULL REFERENCES deliverable_workflows(workflow_id) ON DELETE CASCADE,
    reviewer_id INTEGER NOT NULL REFERENCES users(id),
    review_status VARCHAR(50) NOT NULL,
    feedback TEXT,
    reviewed_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS workflow_reviewers (
    assignment_id SERIAL PRIMARY KEY,
    workflow_id INTEGER NOT NULL REFERENCES deliverable_workflows(workflow_id) ON DELETE CASCADE,
    reviewer_id INTEGER NOT NULL REFERENCES users(id),
    assigned_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT unique_workflow_reviewer UNIQUE(workflow_id, reviewer_id)
);

CREATE TABLE IF NOT EXISTS enrichment_queue (
    queue_id SERIAL PRIMARY KEY,
    workflow_id INTEGER NOT NULL REFERENCES deliverable_workflows(workflow_id) ON DELETE CASCADE,
    status VARCHAR(50) DEFAULT 'pending',
    processed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS notifications (
    notification_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    notification_type VARCHAR(50),
    is_read BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- 3. Triggers
-- ============================================================================

CREATE TRIGGER update_clients_updated_at BEFORE UPDATE ON clients FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_stakeholders_updated_at BEFORE UPDATE ON stakeholders FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_knowledge_entries_updated_at BEFORE UPDATE ON knowledge_entries FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_templates_updated_at BEFORE UPDATE ON templates FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_deliverable_workflows_updated_at BEFORE UPDATE ON deliverable_workflows FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 4. Indexes
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_knowledge_entries_client_id ON knowledge_entries(client_id);
CREATE INDEX IF NOT EXISTS idx_stakeholders_client_id ON stakeholders(client_id);
CREATE INDEX IF NOT EXISTS idx_deliverable_workflows_client_id ON deliverable_workflows(client_id);
CREATE INDEX IF NOT EXISTS idx_workflow_status ON deliverable_workflows(status);
CREATE INDEX IF NOT EXISTS idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_knowledge_entries_daaeg ON knowledge_entries(daaeg_phase);
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
