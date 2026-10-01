-- =========================================================================
-- 1. SECURITE RLS (Row-Level Security) - Isolation Multi-Tenant
-- =========================================================================

-- Table des Élèves
ALTER TABLE eleves ENABLE ROW LEVEL SECURITY;
ALTER TABLE eleves FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS isolation_tenant_eleves ON eleves;
CREATE POLICY isolation_tenant_eleves ON eleves
    FOR ALL
    USING (school_id = NULLIF(current_setting('app.current_school_id', true), '')::integer);

-- Table des Classes
ALTER TABLE classes ENABLE ROW LEVEL SECURITY;
ALTER TABLE classes FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS isolation_tenant_classes ON classes;
CREATE POLICY isolation_tenant_classes ON classes
    FOR ALL
    USING (school_id = NULLIF(current_setting('app.current_school_id', true), '')::integer);

-- Table des Notes
ALTER TABLE notes ENABLE ROW LEVEL SECURITY;
ALTER TABLE notes FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS isolation_tenant_notes ON notes;
CREATE POLICY isolation_tenant_notes ON notes
    FOR ALL
    USING (school_id = NULLIF(current_setting('app.current_school_id', true), '')::integer);

-- Table des Paiements / Finances
ALTER TABLE paiements ENABLE ROW LEVEL SECURITY;
ALTER TABLE paiements FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS isolation_tenant_paiements ON paiements;
CREATE POLICY isolation_tenant_paiements ON paiements
    FOR ALL
    USING (school_id = NULLIF(current_setting('app.current_school_id', true), '')::integer);


-- =========================================================================
-- 2. PERFORMANCE & INDEXATION (Optimisation des requêtes multi-tenant)
-- =========================================================================

CREATE INDEX IF NOT EXISTS idx_eleves_school_class ON eleves(school_id, classe_id);
CREATE INDEX IF NOT EXISTS idx_notes_school_eleve ON notes(school_id, eleve_id);
CREATE INDEX IF NOT EXISTS idx_paiements_school_date ON paiements(school_id, date_paiement);
CREATE INDEX IF NOT EXISTS idx_users_school_role ON users(school_id, role);