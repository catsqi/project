import requests

# 测试获取所有记录
r = requests.get(
    'http://localhost:8000/api/v1/interview/history', params={'limit': 10})
print(f'状态码: {r.status_code}')
print(f'响应: {r.text}')
