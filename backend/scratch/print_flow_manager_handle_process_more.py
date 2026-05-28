with open('/home/sanjana/Alcon/poc/backend/flow_manager.py', 'r', encoding='utf-8') as f:
    content = f.read()

pos = content.find("def handle_process")
if pos != -1:
    print(content[pos+1000:pos+3000])
