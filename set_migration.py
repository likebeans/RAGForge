"""手动设置迁移版本并升级"""
import sqlite3

def set_migration_version():
    conn = sqlite3.connect('backend/yaoyan.db')
    cursor = conn.cursor()
    
    # 设置迁移版本为项目筛选表版本
    cursor.execute("UPDATE alembic_version SET version_num = '2c9c6c7b1c0f'")
    conn.commit()
    print(f"已设置迁移版本为: 2c9c6c7b1c0f")
    
    conn.close()

if __name__ == "__main__":
    set_migration_version()