#!/usr/bin/env python3
"""
Sistema de migracao SQL simples para asyncpg.

Uso:
    poetry run python migrate.py up     # Aplica migracoes pendentes
    poetry run python migrate.py status  # Mostra status das migracoes
    poetry run python migrate.py down    # Remove ultima migracao
"""
import asyncio
import glob
import os
import sys
from pathlib import Path

import asyncpg

from api.settings import settings


async def ensure_migrations_table(conn: asyncpg.Connection):
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version VARCHAR(50) PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')


async def get_applied(conn: asyncpg.Connection) -> set[str]:
    rows = await conn.fetch('SELECT version FROM schema_migrations ORDER BY version')
    return {row['version'] for row in rows}


def get_migration_files() -> list[Path]:
    migrations_dir = Path(__file__).parent / 'migrations'
    files = sorted(glob.glob(str(migrations_dir / '*.sql')))
    return [Path(f) for f in files]


def file_version(path: Path) -> str:
    return path.stem  # ex: 001_initial_schema


async def migrate_up():
    conn = await asyncpg.connect(settings.DATABASE_URL)
    try:
        await ensure_migrations_table(conn)
        applied = await get_applied(conn)
        migration_files = get_migration_files()

        pending = [f for f in migration_files if file_version(f) not in applied]

        if not pending:
            print('Nenhuma migracao pendente.')
            return

        for migration_file in pending:
            version = file_version(migration_file)
            sql = migration_file.read_text()

            print(f'Aplicando {version}...')
            await conn.execute(sql)
            await conn.execute(
                'INSERT INTO schema_migrations (version) VALUES ($1)',
                version,
            )
            print(f'  {version} aplicada com sucesso.')

        print(f'\n{len(pending)} migracao(oes) aplicada(s).')
    finally:
        await conn.close()


async def migrate_status():
    conn = await asyncpg.connect(settings.DATABASE_URL)
    try:
        await ensure_migrations_table(conn)
        applied = await get_applied(conn)
        migration_files = get_migration_files()

        print('Status das migracoes:')
        print('-' * 50)
        for mf in migration_files:
            version = file_version(mf)
            status = 'APLICADA' if version in applied else 'PENDENTE'
            print(f'  {version}: {status}')

        total = len(migration_files)
        done = len(applied & {file_version(f) for f in migration_files})
        print(f'\n{done}/{total} migracoes aplicadas.')
    finally:
        await conn.close()


async def migrate_down():
    conn = await asyncpg.connect(settings.DATABASE_URL)
    try:
        await ensure_migrations_table(conn)
        applied = await get_applied(conn)
        migration_files = get_migration_files()

        applied_files = [f for f in migration_files if file_version(f) in applied]
        if not applied_files:
            print('Nenhuma migracao para remover.')
            return

        last = applied_files[-1]
        version = file_version(last)

        print(f'Removendo {version}...')
        await conn.execute(
            'DELETE FROM schema_migrations WHERE version = $1',
            version,
        )
        print(f'  {version} marcada como removida.')
        print('  NOTA: As tabelas NAO foram dropadas. Use DROP manual se necessario.')
    finally:
        await conn.close()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]

    if command == 'up':
        asyncio.run(migrate_up())
    elif command == 'status':
        asyncio.run(migrate_status())
    elif command == 'down':
        asyncio.run(migrate_down())
    else:
        print(f'Comando desconhecido: {command}')
        print(__doc__)
        sys.exit(1)


if __name__ == '__main__':
    main()
