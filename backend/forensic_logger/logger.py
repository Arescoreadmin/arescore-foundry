import hashlib, json, time, os

LOG_PATH = os.getenv('FORENSIC_LOG', '/data/forensic.log')
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

_last_hash = '0'*64

def write_event(event: dict):
    global _last_hash
    event['ts'] = time.time()
    payload = json.dumps(event, sort_keys=True)
    h = hashlib.sha256((_last_hash + payload).encode()).hexdigest()
    _last_hash = h
    with open(LOG_PATH, 'a') as f:
        f.write(json.dumps({'hash': h, 'event': event}) + "\n")
    return h