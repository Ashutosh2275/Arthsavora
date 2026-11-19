import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def main():
    for db in ['arthsavora', 'arthsavora_test']:
        engine = create_async_engine(f'postgresql+asyncpg://postgres:postgres@localhost:5433/{db}')
        async with engine.begin() as conn:
            # Check if role exists
            res = await conn.execute(text("SELECT 1 FROM pg_roles WHERE rolname = 'arthsavora_app'"))
            if not res.fetchone():
                await conn.execute(text("CREATE ROLE arthsavora_app WITH LOGIN PASSWORD 'arthsavora_app' NOSUPERUSER NOBYPASSRLS;"))
            await conn.execute(text("GRANT USAGE ON SCHEMA public TO arthsavora_app;"))
            await conn.execute(text("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO arthsavora_app;"))
            await conn.execute(text("GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO arthsavora_app;"))
            await conn.execute(text("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO arthsavora_app;"))
            await conn.execute(text("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO arthsavora_app;"))
            print(f"Role arthsavora_app configured for {db}")

asyncio.run(main())
