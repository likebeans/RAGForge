import asyncio
from app.db.session import engine
from sqlalchemy import text

async def check_db():
    async with engine.connect() as conn:
        result = await conn.execute(text('SELECT * FROM reports'))
        print('报告数据:')
        for row in result:
            print(row)

asyncio.run(check_db())
