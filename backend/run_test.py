import subprocess
import os

print("Running test_simulate.py via WSL...")
cmd = 'wsl -d Ubuntu-24.04 bash -c "cd /home/sanjana/Alcon/poc/backend && source venv/bin/activate && python test_simulate.py > test_out.txt 2>&1"'
subprocess.run(cmd, shell=True)
print("Done. Output saved to test_out.txt in WSL")
