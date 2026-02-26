import asyncio
from app.db.session import engine
from sqlalchemy import text

async def check():
    async with engine.connect() as conn:
        # 检查当前数据库时间
        result = await conn.execute(text('SELECT CURRENT_TIMESTAMP, datetime("now", "localtime")'))
        row = result.fetchone()
        print(f'UTC时间: {row[0]}')
        print(f'本地时间: {row[1]}')
        
        # 检查报告数据
        result = await conn.execute(text('SELECT id, title, created_at, updated_at FROM reports'))
        print('\n报告数据:')
        for row in result:
            print(f'ID: {row[0]}, 标题: {row[1]}, 创建时间: {row[2]}, 更新时间: {row[3]}')

if __name__ == '__main__':
    asyncio.run(check())