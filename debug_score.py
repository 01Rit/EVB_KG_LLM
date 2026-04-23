import requests

resp = requests.get('http://localhost:8000/api/v1/battery-models?search=Audi')
print("Battery models:", resp.json())

# Try calling score-all with correct path
import json
resp2 = requests.post('http://localhost:8000/admin/api/v1/admin/components/score-all',
    json={'battery_model': 'Audi_A3'}, timeout=120)
print("\nScore-all response:", resp2.status_code, resp2.json())