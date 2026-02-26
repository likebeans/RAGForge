"""检查reports表结构"""
import sqlite3

def check_reports_structure():
    conn = sqlite3.connect('backend/yaoyan.db')
    cursor = conn.cursor()
    
    # 检查reports表结构
    cursor.execute("PRAGMA table_info(reports)")
    columns = cursor.fetchall()
    print("reports表结构:")
    for col in columns:
        print(f"  {col[1]} ({col[2]})")
    
    # 检查报告数量
    cursor.execute("SELECT COUNT(*) FROM reports")
    count = cursor.fetchone()[0]
    print(f"\n报告数量: {count}")
    
    conn.close()

if __name__ == "__main__":
    check_reports_structure()