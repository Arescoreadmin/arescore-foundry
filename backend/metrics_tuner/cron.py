import os, httpx, time, yaml
PROM = os.getenv("PROM_URL", "http://prometheus:9090")
OUT = os.getenv("OUTPUT_RULES", "/rules/_generated.yml")

QUERY = 'rate(http_requests_total[5m])'

while True:
    try:
        r = httpx.get(f"{PROM}/api/v1/query", params={"query": QUERY}, timeout=5)
        val = 0.0
        if r.status_code == 200:
            data = r.json().get("data", {}).get("result", [])
            if data and 'value' in data[0]:
                val = float(data[0]['value'][1])
        rules = {
            'groups': [{
                'name': 'autotune',
                'rules': [{
                    'alert': 'HighHTTPRate',
                    'expr': f"{QUERY} > {max(10, val*3):.2f}",
                    'for': '2m',
                    'labels': {'severity': 'warning'},
                    'annotations': {'summary': 'Auto-tuned high HTTP rate'}
                }]
            }]
        }
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with open(OUT, 'w') as f:
            yaml.safe_dump(rules, f)
    except Exception as e:
        print("tuner error", e)
    time.sleep(60)