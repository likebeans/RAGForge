"""检查数据库中的报告数据"""
import sqlite3

def check_database():
    conn = sqlite3.connect('backend/yaoyan.db')
    cursor = conn.cursor()
    
    # 检查所有表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print("数据库中的表:", [t[0] for t in tables])
    
    # 检查报告表是否存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reports'")
    reports_table = cursor.fetchone()
    
    if reports_table:
        # 检查报告数量
        cursor.execute("SELECT COUNT(*) FROM reports")
        count = cursor.fetchone()[0]
        print(f"报告数量: {count}")
        
        # 检查报告数据
        cursor.execute("SELECT id, title, user_id, status FROM reports LIMIT 5")
        reports = cursor.fetchall()
        print("示例报告:", reports)
        
        # 检查用户表
        cursor.execute("SELECT id, username FROM users LIMIT 5")
        users = cursor.fetchall()
        print("示例用户:", users)
    else:
        print("reports 表不存在")
    
    conn.close()

if __name__ == "__main__":
    check_database()