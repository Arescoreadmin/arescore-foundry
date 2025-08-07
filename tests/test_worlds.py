import requests

TOKEN = {'Authorization': 'Bearer changeme'}


def test_world_creation_and_log_export():
    base = 'http://localhost:8000'
    r = requests.post(f'{base}/worlds', json={'name': 'test'}, headers=TOKEN)
    assert r.status_code == 200
    r = requests.get(f'{base}/worlds', headers=TOKEN)
    assert 'test' in r.json()['worlds']
    r = requests.get('http://localhost:8004/export', headers=TOKEN)
    assert r.status_code == 200
