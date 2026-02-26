"""检查alembic迁移状态"""
import sqlite3

def check_migration_status():
    conn = sqlite3.connect('backend/yaoyan.db')
    cursor = conn.cursor()
    
    # 检查alembic_version表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'")
    version_table = cursor.fetchone()
    
    if version_table:
        # 检查当前迁移版本
        cursor.execute("SELECT version_num FROM alembic_version")
        current_version = cursor.fetchone()
        print(f"当前迁移版本: {current_version}")
        
        # 检查所有表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"数据库中的表: {[t[0] for t in tables]}")
    else:
        print("alembic_version表不存在，数据库未初始化")
    
    conn.close()

if __name__ == "__main__":
    check_migration_status()