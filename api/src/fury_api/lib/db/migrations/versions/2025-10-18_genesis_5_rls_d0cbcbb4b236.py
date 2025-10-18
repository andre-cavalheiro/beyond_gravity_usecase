"""RLS with tenant_user and tenant_user_ro roles.

Revision ID: d0cbcbb4b236
Revises: 4efdb957fe21
Create Date: 2025-01-28 16:02:24.320335+00:00

"""

from __future__ import annotations

import warnings

from alembic import op


__all__ = ["downgrade", "upgrade", "schema_upgrades", "schema_downgrades"]

# revision identifiers, used by Alembic.
revision = "d0cbcbb4b236"
down_revision = "4efdb957fe21"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning)

        schema_upgrades()


def downgrade() -> None:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning)

        schema_downgrades()


def schema_upgrades() -> None:
    """Schema upgrade migrations."""
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning)

        # Create tenant_user role if it doesn't exist
        op.execute(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'tenant_user') THEN
                    CREATE ROLE tenant_user;
                END IF;

                -- Grant schema and table permissions to tenant_user
                EXECUTE 'GRANT USAGE ON SCHEMA ' || current_schema || ' TO tenant_user';
                EXECUTE 'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA ' || current_schema || ' TO tenant_user';
                EXECUTE 'ALTER DEFAULT PRIVILEGES IN SCHEMA ' || current_schema || ' GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO tenant_user';
                EXECUTE 'GRANT USAGE ON ALL SEQUENCES IN SCHEMA ' || current_schema || ' TO tenant_user';
                EXECUTE 'ALTER DEFAULT PRIVILEGES IN SCHEMA ' || current_schema || ' GRANT USAGE ON SEQUENCES TO tenant_user';
            END;
            $$ LANGUAGE plpgsql;
            """
        )

        # Create tenant_user_ro role if it doesn't exist
        op.execute(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'tenant_user_ro') THEN
                    CREATE ROLE tenant_user_ro;
                END IF;

                -- Grant schema and table permissions to tenant_user_ro (read-only)
                EXECUTE 'GRANT USAGE ON SCHEMA ' || current_schema || ' TO tenant_user_ro';
                EXECUTE 'GRANT SELECT ON ALL TABLES IN SCHEMA ' || current_schema || ' TO tenant_user_ro';
                EXECUTE 'ALTER DEFAULT PRIVILEGES IN SCHEMA ' || current_schema || ' GRANT SELECT ON TABLES TO tenant_user_ro';
                EXECUTE 'GRANT USAGE ON ALL SEQUENCES IN SCHEMA ' || current_schema || ' TO tenant_user_ro';
                EXECUTE 'ALTER DEFAULT PRIVILEGES IN SCHEMA ' || current_schema || ' GRANT USAGE ON SEQUENCES TO tenant_user_ro';
            END;
            $$ LANGUAGE plpgsql;
            """
        )

        # Enable Row-Level Security on tables and add policies
        op.execute(
            """
            DO $$
            BEGIN
                -- Enable RLS on 'organization' table
                ALTER TABLE organization ENABLE ROW LEVEL SECURITY;

                -- Drop existing policies to avoid duplicates
                DROP POLICY IF EXISTS tenant_policy ON organization;
                CREATE POLICY tenant_policy ON organization
                TO tenant_user
                USING (id = current_setting('app.current_organization_id')::bigint);

                DROP POLICY IF EXISTS tenant_policy_ro ON organization;
                CREATE POLICY tenant_policy_ro ON organization
                TO tenant_user_ro
                USING (id = current_setting('app.current_organization_id')::bigint);

                -- Enable RLS on 'user' table
                ALTER TABLE "user" ENABLE ROW LEVEL SECURITY;

                DROP POLICY IF EXISTS tenant_policy ON "user";
                CREATE POLICY tenant_policy ON "user"
                TO tenant_user
                USING (organization_id = current_setting('app.current_organization_id')::bigint);

                DROP POLICY IF EXISTS tenant_policy_ro ON "user";
                CREATE POLICY tenant_policy_ro ON "user"
                TO tenant_user_ro
                USING (organization_id = current_setting('app.current_organization_id')::bigint);
            END;
            $$ LANGUAGE plpgsql;
            """
        )


def schema_downgrades() -> None:
    """Schema downgrade migrations."""
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning)

        op.execute(
            """
            DO $$
            DECLARE
                dependent_count int;
                role_oid oid;
            BEGIN
                -- Disable and drop RLS on 'organization'
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'organization') THEN
                    DROP POLICY IF EXISTS tenant_policy ON organization;
                    DROP POLICY IF EXISTS tenant_policy_ro ON organization;
                    ALTER TABLE organization DISABLE ROW LEVEL SECURITY;
                END IF;

                -- Disable and drop RLS on 'user'
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'user') THEN
                    DROP POLICY IF EXISTS tenant_policy ON "user";
                    DROP POLICY IF EXISTS tenant_policy_ro ON "user";
                    ALTER TABLE "user" DISABLE ROW LEVEL SECURITY;
                END IF;

                -- Clean up the tenant_user role
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'tenant_user') THEN
                    -- Revoke schema privileges
                    EXECUTE 'REVOKE USAGE ON SCHEMA ' || current_schema || ' FROM tenant_user';
                    EXECUTE 'REVOKE SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA ' || current_schema || ' FROM tenant_user';
                    EXECUTE 'REVOKE USAGE ON ALL SEQUENCES IN SCHEMA ' || current_schema || ' FROM tenant_user';

                    -- Revoke default privileges
                    EXECUTE 'ALTER DEFAULT PRIVILEGES FOR ROLE tenant_user IN SCHEMA ' || current_schema || ' REVOKE ALL ON TABLES FROM tenant_user';
                    EXECUTE 'ALTER DEFAULT PRIVILEGES FOR ROLE tenant_user IN SCHEMA ' || current_schema || ' REVOKE ALL ON SEQUENCES FROM tenant_user';

                    -- Explicitly clean up remaining grants on default privileges
                    DELETE FROM pg_default_acl
                    WHERE defaclrole = (SELECT oid FROM pg_roles WHERE rolname = 'tenant_user');

                    -- Check for dependencies
                    SELECT COUNT(*) INTO dependent_count
                    FROM pg_shdepend
                    WHERE refobjid = (SELECT oid FROM pg_roles WHERE rolname = 'tenant_user');

                    IF dependent_count = 0 THEN
                        EXECUTE 'DROP ROLE tenant_user';
                    ELSE
                        RAISE NOTICE 'Role tenant_user still has dependencies and cannot be dropped.';
                    END IF;
                END IF;

                -- Clean up the tenant_user_ro role
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'tenant_user_ro') THEN
                    -- Revoke schema privileges
                    EXECUTE 'REVOKE USAGE ON SCHEMA ' || current_schema || ' FROM tenant_user_ro';
                    EXECUTE 'REVOKE SELECT ON ALL TABLES IN SCHEMA ' || current_schema || ' FROM tenant_user_ro';
                    EXECUTE 'REVOKE USAGE ON ALL SEQUENCES IN SCHEMA ' || current_schema || ' FROM tenant_user_ro';

                    -- Revoke default privileges
                    EXECUTE 'ALTER DEFAULT PRIVILEGES FOR ROLE tenant_user_ro IN SCHEMA ' || current_schema || ' REVOKE ALL ON TABLES FROM tenant_user_ro';
                    EXECUTE 'ALTER DEFAULT PRIVILEGES FOR ROLE tenant_user_ro IN SCHEMA ' || current_schema || ' REVOKE ALL ON SEQUENCES FROM tenant_user_ro';

                    -- Explicitly clean up remaining grants on default privileges
                    DELETE FROM pg_default_acl
                    WHERE defaclrole = (SELECT oid FROM pg_roles WHERE rolname = 'tenant_user_ro');

                    -- Check for dependencies
                    SELECT COUNT(*) INTO dependent_count
                    FROM pg_shdepend
                    WHERE refobjid = (SELECT oid FROM pg_roles WHERE rolname = 'tenant_user_ro');

                    IF dependent_count = 0 THEN
                        EXECUTE 'DROP ROLE tenant_user_ro';
                    ELSE
                        RAISE NOTICE 'Role tenant_user_ro still has dependencies and cannot be dropped.';
                    END IF;
                END IF;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
