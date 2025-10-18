from __future__ import annotations

import asyncio
import importlib
import pkgutil
from typing import TYPE_CHECKING, Any

from alembic import context
from alembic.autogenerate import rewriter
from alembic.operations import ops
from sqlalchemy import Column, pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from fury_api.lib.db.base import metadata
from fury_api.lib.settings import config as db_config

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection

__all__ = ["do_run_migrations", "run_migrations_offline", "run_migrations_online"]


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config


def _load_domain_models() -> None:
    """Ensure all domain SQLModel tables are imported before autogenerate runs."""
    package_name = f"{db_config.app.SLUG}.domain"
    try:
        package = importlib.import_module(package_name)
    except ImportError:
        return

    package_path = getattr(package, "__path__", None)
    if package_path is None:
        return

    for module_info in pkgutil.walk_packages(package_path, package.__name__ + "."):
        if module_info.name.endswith(".models"):
            importlib.import_module(module_info.name)


_load_domain_models()

# Interpret the config file for Python logging.
# This line sets up loggers basically.
# if config.config_file_name is not None:
#     from logging.config import fileConfig

#     fileConfig(config.config_file_name)


# Apply Custom Sorting to Columns
writer = rewriter.Rewriter()


@writer.rewrites(ops.MigrationScript)
def rewrite_op_container(context, revision, op) -> ops.MigrationScript:
    rls_upgprade_ops = []
    for sub_upgrade_op in op.upgrade_ops.ops:
        if isinstance(sub_upgrade_op, ops.CreateTableOp):
            column_names = {col.key for col in sub_upgrade_op.columns if isinstance(col, Column)}
            new_op = build_rls_upgrade_op(sub_upgrade_op.table_name, sub_upgrade_op.schema, column_names)
            if new_op is not None:
                rls_upgprade_ops.append(new_op)

    op.upgrade_ops.ops.extend(rls_upgprade_ops)
    return op


# Order columns on create table
@writer.rewrites(ops.CreateTableOp)
def order_columns(context, revision, op) -> ops.CreateTableOp:
    special_names = {
        "id": -100,
        "organization_id": -99,
        "created_at": 1001,
        "created_by": 1002,
        "updated_at": 1003,
        "updated_by": 1004,
    }

    cols_by_key = [
        (special_names.get(col.key, index) if isinstance(col, Column) else 2000, col.copy())
        for index, col in enumerate(op.columns)
    ]

    columns = [col for _, col in sorted(cols_by_key, key=lambda entry: entry[0])]
    return ops.CreateTableOp(
        op.table_name, columns, schema=op.schema, _namespace_metadata=op._namespace_metadata, **op.kw
    )


# Enable RLS when adding a new table
def build_rls_upgrade_op(table_name: str, schema: str | None, columns: set[str]) -> ops.ExecuteSQLOp | None:
    schema_prefix = f'"{schema}".' if schema else ""

    if "organization_id" not in columns:
        return None

    policy_definitions = (("tenant_user", "tenant_policy"), ("tenant_user_ro", "tenant_policy_ro"))
    policy_statements = "".join(
        f"""
            create policy {policy_name} on {schema_prefix}"{table_name}" to {role_name}
                using (organization_id = current_setting('app.current_organization_id')::bigint);
        """
        for role_name, policy_name in policy_definitions
    )

    return ops.ExecuteSQLOp(
        f"""
        do $$
        begin
            alter table {schema_prefix}"{table_name}" enable row level security;
            {policy_statements}
        end;
        $$ language plpgsql;
        """
    )


# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = metadata
target_metadata.schema = db_config.database.SCHEMA

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.
config.set_main_option("sqlalchemy.url", db_config.database.URL)
config.compare_type = True
config.compare_server_default = True
# We don't want to include schemas in the migration scripts as we are using a single schema and setting the search path
config.include_schemas = False
config.version_table_schema = target_metadata.schema
config.version_table = "alembic_version"
config.version_table_pk = "version_num"
config.render_as_batch = True
config.process_revision_directives = writer


def include_object(obj: Any, name: str, type_: str, reflected: bool, compare_to: Any) -> bool:
    """Determines if an object should be included in the migration.

    Args:
        obj: Object to include or exclude.
        name: The name of the object.
        type_: The type of the object. (e.g. table, index, etc.)
        reflected: Whether the object was reflected from the database.
        compare_to: The object to compare to.

    Returns:
        True if the object should be included in the migration, otherwise False.
    """
    if type_ == "table" and name == config.version_table:
        return False

    return True


def context_pre_begin_transaction() -> None:
    context.execute(f"create schema if not exists {target_metadata.schema};")
    context.execute(f"set search_path to {target_metadata.schema}")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.
    Calls to context.execute() here emit the given string to the
    script output.
    """
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=config.compare_type,
        include_schemas=config.include_schemas,
        version_table=config.version_table,
        version_table_pk=config.version_table_pk,
        version_table_schema=config.version_table_schema,
        render_as_batch=config.render_as_batch,
        process_revision_directives=config.process_revision_directives,
    )

    with context.begin_transaction():
        context_pre_begin_transaction()
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=config.compare_type,
        include_schemas=config.include_schemas,
        version_table=config.version_table,
        version_table_pk=config.version_table_pk,
        version_table_schema=config.version_table_schema,
        render_as_batch=config.render_as_batch,
        include_object=include_object,
        process_revision_directives=config.process_revision_directives,
    )

    with context.begin_transaction():
        context_pre_begin_transaction()
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    configuration = config.get_section(config.config_ini_section) or {}

    connectable = async_engine_from_config(configuration, prefix="sqlalchemy.", poolclass=pool.NullPool, future=True)
    if connectable is None:
        msg = (
            "Could not get engine from config. "
            "Please ensure your `alembic.ini` according to the official Alembic documentation."
        )
        raise RuntimeError(msg)

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
