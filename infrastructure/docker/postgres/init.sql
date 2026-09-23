-- Multi-tenant ecommerce schemas
-- Each microservice owns its schema (bounded context separation)

CREATE SCHEMA IF NOT EXISTS auth;
CREATE SCHEMA IF NOT EXISTS users;
CREATE SCHEMA IF NOT EXISTS campaigns;
CREATE SCHEMA IF NOT EXISTS products;
CREATE SCHEMA IF NOT EXISTS orders;
CREATE SCHEMA IF NOT EXISTS deliveries;

-- Tenant registry (shared schema)
CREATE TABLE IF NOT EXISTS public.tenants (
    id          VARCHAR PRIMARY KEY,
    name        VARCHAR NOT NULL,
    slug        VARCHAR NOT NULL UNIQUE,
    plan        VARCHAR NOT NULL DEFAULT 'basic',
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    settings    JSONB DEFAULT '{}',
    created_at  TIMESTAMP DEFAULT NOW(),
    updated_at  TIMESTAMP DEFAULT NOW()
);

-- Seed demo tenant
INSERT INTO public.tenants (id, name, slug, plan)
VALUES ('tenant-demo-001', 'Demo Pharma', 'demo-pharma', 'pro')
ON CONFLICT DO NOTHING;

GRANT ALL ON SCHEMA auth       TO admin;
GRANT ALL ON SCHEMA users      TO admin;
GRANT ALL ON SCHEMA campaigns  TO admin;
GRANT ALL ON SCHEMA products   TO admin;
GRANT ALL ON SCHEMA orders     TO admin;
GRANT ALL ON SCHEMA deliveries TO admin;
