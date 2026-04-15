import requests

# 测试获取所有记录
r = requests.get(
    'http://localhost:8000/api/v1/interview/history', params={'limit': 10})
print(f'状态码: {r.status_code}')
data = r.json()
print(f'总记录数: {data["total"]}')
print('\n最近的记录:')
for rec in data['records']:
    print(
        f'  - {rec["user_id"]} | {rec["job_title"]} | {rec["status"]} | 对话数: {rec.get("question_count", 0)}')
