import requests
import time

print("Start rescoring components...")

resp = requests.post('http://localhost:8000/admin/api/v1/admin/components/score-all', json={'battery_model': 'Audi_A3'}, timeout=300)
print(f"Status: {resp.status_code}")