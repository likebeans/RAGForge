import asyncio
from app.db.session import engine
from sqlalchemy import text

async def check():
    async with engine.connect() as conn:
        result = await conn.execute(text('SELECT id, title, created_at, updated_at FROM reports'))
        print('报告数据:')
        for row in result:
            print(f'ID: {row[0]}, 标题: {row[1]}, 创建时间: {row[2]}, 更新时间: {row[3]}')

if __name__ == '__main__':
    asyncio.run(check())