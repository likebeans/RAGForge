"""删除数据库文件"""
import os
import glob

# 查找并删除所有.db文件
db_files = glob.glob("backend/*.db")
for db_file in db_files:
    try:
        os.remove(db_file)
        print(f"已删除: {db_file}")
    except Exception as e:
        print(f"删除失败 {db_file}: {e}")

print("数据库文件清理完成")