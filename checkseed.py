import asyncio
import asyncpg

async def main():
    conn = await asyncpg.connect('postgresql://sepaham:sepaham@localhost:5432/sepaham')
    rows = await conn.fetch("SELECT email, role FROM users ORDER BY email")
    print('users:', len(rows))
    for r in rows:
        print('-', r['email'], r['role'])
    roles = await conn.fetch("SELECT id, title FROM roles ORDER BY id")
    print('roles:', len(roles))
    for r in roles[:12]:
        print('-', r['id'], r['title'])
    rms = await conn.fetch("SELECT id, title FROM roadmaps ORDER BY id")
    print('roadmaps:', len(rms))
    for r in rms[:12]:
        print('-', r['id'], r['title'])
    await conn.close()

asyncio.run(main())
