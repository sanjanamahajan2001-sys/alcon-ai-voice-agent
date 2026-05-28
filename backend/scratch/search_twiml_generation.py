with open('/home/sanjana/Alcon/poc/backend/flow_manager.py', 'r', encoding='utf-8') as f:
    content = f.read()

import re
matches = [m.start() for m in re.finditer('VoiceResponse', content)]
for m in matches[:5]:
    print(f"Match at {m}:\n{content[m-200:m+200]}\n" + "-"*50)
