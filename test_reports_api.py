"""测试报告API"""
import requests

def test_reports_api():
    base_url = "http://localhost:3002"
    
    # 首先登录获取token
    login_response = requests.post(f"{base_url}/api/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    
    if login_response.status_code == 200:
        token = login_response.json()["access_token"]
        print("登录成功")
        
        # 测试获取报告列表
        headers = {"Authorization": f"Bearer {token}"}
        reports_response = requests.get(f"{base_url}/api/reports", headers=headers)
        
        if reports_response.status_code == 200:
            data = reports_response.json()
            print(f"报告列表响应: {data}")
            print(f"报告数量: {data.get('total', 0)}")
            print(f"报告项目: {data.get('items', [])}")
        else:
            print(f"获取报告列表失败: {reports_response.status_code}")
            print(f"错误信息: {reports_response.text}")
    else:
        print(f"登录失败: {login_response.status_code}")
        print(f"错误信息: {login_response.text}")

if __name__ == "__main__":
    test_reports_api()