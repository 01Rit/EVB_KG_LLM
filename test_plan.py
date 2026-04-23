import requests

r = requests.post(
    'http://localhost:8000/api/v1/disassembly/plan',
    json={'battery_model': 'Audi_A3', 'context': [], 'debug': False},
    timeout=120
)
print('Status:', r.status_code)
print('Response:', r.text[:3000] if r.text else 'empty')