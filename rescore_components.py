import requests
import time

# 重新评估所有组件
print("开始重新评估组件...")

resp = requests.post('http://localhost:8000/admin/api/v1/admin/components/score-all',
    json={'battery_model': 'Audi_A3'}, timeout=300)
print(f"评分完成: {resp.status_code}")