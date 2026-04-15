import requests

BASE_URL = "http://localhost:8000/api/v1"

# 测试历史记录
print("测试历史记录API...")
r = requests.get(f"{BASE_URL}/interview/history",
                 params={"user_id": "test_user", "limit": 5})
print(f"状态码: {r.status_code}")

if r.status_code == 200:
    data = r.json()
    print(f"记录数: {data['total']}")

    if data['records']:
        record_id = data['records'][0]['id']
        print(f"\n获取详情: {record_id}")

        r2 = requests.get(f"{BASE_URL}/interview/history/{record_id}")
        print(f"详情状态码: {r2.status_code}")

        if r2.status_code == 200:
            detail = r2.json()
            conv = detail.get('conversation_history', [])
            print(f"对话历史条数: {len(conv)}")

            if conv:
                print("✅ 历史记录功能正常！")
                print(f"第一条: [{conv[0]['role']}] {conv[0]['content'][:50]}...")
            else:
                print("❌ 对话历史为空")
    else:
        print("没有找到记录")
else:
    print(f"错误: {r.text}")
