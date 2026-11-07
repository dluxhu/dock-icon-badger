#!/usr/bin/env python3
"""
run.py - one-command start for the Dock Icon Badger web UI.

    python3 run.py [--port 8765] [--open] [--no-venv]

Creates .venv next to this file if needed, installs requirements.txt into it (only when the
file changed), then starts server.py on 127.0.0.1 and prints:

    Dock Icon Badger running at http://127.0.0.1:<port>

Needs only python3 (3.8+). Stop with Ctrl+C.
"""
import hashlib, os, signal, subprocess, sys, venv

HERE = os.path.dirname(os.path.abspath(__file__))
VENV = os.path.join(HERE, ".venv")
REQ = os.path.join(HERE, "requirements.txt")


def venv_python():
    return os.path.join(VENV, "Scripts", "python.exe") if os.name == "nt" else os.path.join(VENV, "bin", "python")


def deps_ok(py):
    return subprocess.run([py, "-c", "import PIL, numpy"], capture_output=True).returncode == 0


def ensure_venv():
    py = venv_python()
    if not os.path.exists(py):
        print("Setting up a Python environment in .venv (first run only)...", flush=True)
        try:
            venv.create(VENV, with_pip=True)
        except Exception as e:
            sys.exit(f"Could not create .venv ({e}). On Debian/Ubuntu: sudo apt install python3-venv. "
                     f"Or install the requirements yourself and run: python3 run.py --no-venv")
    stamp = os.path.join(VENV, ".requirements.sha1")
    want = hashlib.sha1(open(REQ, "rb").read()).hexdigest()
    have = open(stamp).read().strip() if os.path.exists(stamp) else ""
    if want != have or not deps_ok(py):
        print("Installing requirements (pillow, numpy, cairosvg)...", flush=True)
        r = subprocess.run([py, "-m", "pip", "install", "--disable-pip-version-check", "-q", "-r", REQ])
        if r.returncode != 0 or not deps_ok(py):
            sys.exit("pip install failed; check your network connection and try again.")
        with open(stamp, "w") as f: f.write(want)
    return py


def main():
    args = sys.argv[1:]
    if "--no-venv" in args:
        args.remove("--no-venv"); py = sys.executable
        if not deps_ok(py): sys.exit("Pillow and numpy are missing: pip install -r requirements.txt")
    else:
        py = ensure_venv()
    child = subprocess.Popen([py, os.path.join(HERE, "server.py")] + args)
    signal.signal(signal.SIGTERM, lambda *_: child.terminate())   # pass "stop" on to the server
    while True:
        try:
            sys.exit(child.wait())
        except KeyboardInterrupt:   # Ctrl+C reaches the server too; wait for it to clean up
            continue


if __name__ == "__main__":
    main()
