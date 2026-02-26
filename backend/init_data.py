import asyncio
import os
import sys

# 将当前目录添加到 sys.path，确保可以导入 app 模块
sys.path.append(os.getcwd())

from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.user import User
from app.models.role import Role
from app.models.group import Group
from app.auth.password import hash_password

async def init_data():
    print("Starting data initialization...")
    async with SessionLocal() as session:
        try:
            # 1. Create Role
            stmt = select(Role).where(Role.name == "admin")
            result = await session.execute(stmt)
            admin_role = result.scalar_one_or_none()
            
            if not admin_role:
                print("Creating 'admin' role...")
                admin_role = Role(
                    name="admin",
                    display_name="Administrator",
                    description="System Administrator with full access",
                    permissions=["*"]
                )
                session.add(admin_role)
            else:
                print("'admin' role already exists.")

            # 2. Create Group
            stmt = select(Group).where(Group.name == "IT")
            result = await session.execute(stmt)
            it_group = result.scalar_one_or_none()
            
            if not it_group:
                print("Creating 'IT' group...")
                it_group = Group(
                    name="IT",
                    display_name="Information Technology",
                    description="IT Department"
                )
                session.add(it_group)
            else:
                print("'IT' group already exists.")

            # 3. Create User
            stmt = select(User).where(User.username == "admin")
            result = await session.execute(stmt)
            admin_user = result.scalar_one_or_none()
            
            if not admin_user:
                print("Creating 'admin' user...")
                admin_user = User(
                    username="admin",
                    password_hash=hash_password("admin123"),
                    email="admin@yaoyan.ai",
                    display_name="System Admin",
                    is_admin=True,
                    is_active=True,
                    clearance="top_secret"
                )
                # Associate role and group
                # 注意：如果是新创建的对象，需要在 flush 后才能关联，或者直接通过 relationship 赋值
                # 这里因为 admin_role 和 it_group 已经在 session 中（无论是查询出来的还是新add的），SQLAlchemy 会处理
                admin_user.roles.append(admin_role)
                admin_user.groups.append(it_group)
                
                session.add(admin_user)
                await session.commit()
                print("User 'admin' created successfully with password 'admin123'.")
            else:
                print("User 'admin' already exists. Resetting password...")
                admin_user.password_hash = hash_password("admin123")
                # Ensure roles/groups are linked if missing
                if admin_role not in admin_user.roles:
                    admin_user.roles.append(admin_role)
                if it_group not in admin_user.groups:
                    admin_user.groups.append(it_group)
                    
                session.add(admin_user)
                await session.commit()
                print("User 'admin' password reset to 'admin123'.")
        except Exception as e:
            print(f"An error occurred: {e}")
            await session.rollback()
            raise

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(init_data())
