import json
from pathlib import Path

SOUND_LOG_FILE = Path('../lunalu-bot/data/json/sound_log.json')

with SOUND_LOG_FILE.open() as f:
    logs = json.loads(f.read())

for k, v in logs['user_data'].items():
    temp = v
    temp.pop(0)
    temp.append(0)
    logs[k] = temp

with SOUND_LOG_FILE.open('w') as f:
    f.write(json.dumps(logs))
