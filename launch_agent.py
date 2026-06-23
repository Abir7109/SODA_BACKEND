"""
SODA Local Agent Launcher — runs the agent and writes ALL output to a log file.
This is called by the batch file / Task Scheduler instead of directly running local_agent.py.
"""
import sys, os, subprocess, time

script_dir = os.path.dirname(os.path.abspath(__file__))
agent_path = os.path.join(script_dir, "backend", "local_agent.py")
log_path = os.path.join(script_dir, "agent_launcher.log")

with open(log_path, "a") as log:
    log.write(f"\n--- Launcher started at {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
    log.write(f"Python: {sys.executable}\n")
    log.write(f"Agent: {agent_path}\n")
    log.flush()

    # Try pythonw first (no console), fallback to python
    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    if os.path.exists(pythonw):
        python_exe = pythonw
    else:
        python_exe = sys.executable

    log.write(f"Using: {python_exe}\n")
    log.flush()

    proc = subprocess.Popen(
        [python_exe, "-u", agent_path],
        stdout=log,
        stderr=log,
        cwd=script_dir,
    )

    log.write(f"Launched PID: {proc.pid}\n")
    log.write(f"Agent log: {os.path.join(script_dir, 'agent.log')}\n")
    log.flush()
