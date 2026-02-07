-- Create the Tables
CREATE TABLE USERS (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE PROJECTS (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES USERS(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Added
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE LOGS (
    id SERIAL PRIMARY KEY,
    project_id INT REFERENCES PROJECTS(id) ON DELETE CASCADE,
    user_prompt TEXT,
    llm_response JSONB,
    execution_time FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP -- Added (Fixes the crash)
);

CREATE TABLE SAVED_SCHEMAS (
    id SERIAL PRIMARY KEY,
    project_id INT REFERENCES PROJECTS(id) ON DELETE CASCADE,
    sql_script TEXT,
    er_diagram_code TEXT,
    version INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP -- Added
);

-- Seed Data
INSERT INTO USERS (email, password_hash) VALUES ('admin@example.com', 'hash_123');
INSERT INTO PROJECTS (user_id, name, description) VALUES (1, 'My First ERD Project', 'Default workspace');