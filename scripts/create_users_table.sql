CREATE TABLE IF NOT EXISTS utilisateurs (
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    mot_de_passe_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('client', 'admin', 'super_admin')),
    date_creation TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);
