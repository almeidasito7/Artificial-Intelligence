OFFICE_SCHEMA_SQL = """
CREATE SCHEMA IF NOT EXISTS office;

CREATE TABLE IF NOT EXISTS office.office_sections (
    id BIGSERIAL PRIMARY KEY,

    table_number TEXT NOT NULL,
    area TEXT NOT NULL,

    status TEXT DEFAULT 'available'
        CHECK (status IN ('available', 'occupied', 'maintenance')),

    business_area TEXT,
    office_region TEXT,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS office.office_resources (
    id BIGSERIAL PRIMARY KEY,

    resource_name TEXT NOT NULL,
    type TEXT,

    status TEXT DEFAULT 'available'
        CHECK (status IN ('available', 'in_use', 'maintenance')),

    quantity INTEGER DEFAULT 0 CHECK (quantity >= 0),

    office_region TEXT,

    section_id BIGINT REFERENCES office.office_sections(id),

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

ALTER TABLE office.office_sections ENABLE ROW LEVEL SECURITY;
ALTER TABLE office.office_resources ENABLE ROW LEVEL SECURITY;

CREATE POLICY IF NOT EXISTS "Allow all sections"
ON office.office_sections
FOR ALL
USING (true);

CREATE POLICY IF NOT EXISTS "Allow all resources"
ON office.office_resources
FOR ALL
USING (true);
""".strip()
