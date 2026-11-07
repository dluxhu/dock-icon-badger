#!/usr/bin/env python3
"""
server.py - local web UI for dock_icon_badger.py.

Serves a single-page UI on 127.0.0.1 only. Upload (or point at local paths of) app icons and
badges, pick styles and knobs, preview every app x badge x style, and download PNG / .icns / zip.

Run it with `python3 run.py` (creates .venv and installs requirements first), or directly:
    python3 server.py [--port 8765] [--open]
Only Python's standard library is used here; rendering comes from dock_icon_badger.py.
"""
import argparse, base64, copy, hashlib, io, json, os, platform, re, shutil, signal, sys
import tempfile, threading, time, uuid, webbrowser, zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dock_icon_badger as dib  # noqa: E402

WEB = os.path.join(HERE, "web")
MAX_UPLOAD = 25 * 1024 * 1024          # per file
MAX_JSON = 1 * 1024 * 1024
MAX_RESULTS = 1500                     # oldest rendered results are deleted beyond this
UPLOAD_EXT = (".icns", ".png", ".svg", ".jpg", ".jpeg", ".webp")
PATH_EXT = UPLOAD_EXT + (".app", ".iconset")
STATIC = {"/": ("index.html", "text/html; charset=utf-8")}
IS_MAC = platform.system() == "Darwin"
SAMPLE_APPS = os.path.join(HERE, "samples", "apps")
SAMPLE_BADGES = os.path.join(HERE, "samples", "badges")   # <name>.svg and <name>.png; PNG is used without SVG support
# Samples shown in the pickers: (file key, label, recommended). Files not listed here are appended.
SAMPLE_META = {"app": [("Mail", "Mail", True), ("Calendar", "Calendar", True), ("Notes", "Notes", True), ("Swirl", "Swirl", True),
                       ("Weather", "Weather", False), ("Terminal", "Terminal", False), ("Music", "Music", False), ("Chat", "Chat", False)],
               "logo": [("todo-dodo", "Todo-Dodo", True), ("beta", "Beta", True), ("dev", "Dev", False)]}


class Superseded(Exception):
    pass


class Store:
    """Everything lives in one temp dir that is deleted when the server stops."""
    def __init__(self):
        self.dir = tempfile.mkdtemp(prefix="dock-icon-badger-")
        for d in ("uploads", "results"): os.makedirs(os.path.join(self.dir, d))
        self.items, self.results, self.cache, self.latest = {}, {}, {}, {}
        self.lock = threading.Lock()
        self.render_slots = threading.Semaphore(max(1, min(4, (os.cpu_count() or 2) // 2)))

    def cleanup(self): shutil.rmtree(self.dir, ignore_errors=True)

    def add_item(self, kind, path, name=None, src=None):
        """Load an app icon or badge from a file path; raises ValueError with a friendly message."""
        return self.register(kind, load_obj(kind, path, name), src or source_id(path))

    def register(self, kind, obj, src):
        iid = uuid.uuid4().hex[:12]
        thumb_src = obj.icon if kind == "app" else obj.im
        th = thumb_src.copy(); th.thumbnail((128, 128)); buf = io.BytesIO(); th.save(buf, "PNG")
        item = dict(id=iid, kind=kind, src=src, name=obj.name, thumb="data:image/png;base64," + base64.b64encode(buf.getvalue()).decode())
        if kind == "app": item.update(detail=f"{obj.kind}, {obj.source_size}px")
        else: item.update(detail=f"{obj.im.width}x{obj.im.height}, accent #%02x%02x%02x" % obj.accent, accent="#%02x%02x%02x" % obj.accent)
        with self.lock: self.items[iid] = dict(item, obj=obj)
        return item

    def sample(self, kind, key):
        """A sample app/badge as a new item. Samples are decoded once (preloaded at startup) and shared."""
        s = SAMPLES.get(kind, {}).get(key)
        if not s: raise ValueError(f"unknown sample {key!r}")
        with s["lock"]:
            if s["obj"] is None: s["obj"] = load_obj(kind, s["path"], s["name"])
        return self.register(kind, s["obj"], s["src"])   # content hash: uploading the same file again is a duplicate

    def render(self, req):
        with self.lock:
            app, logo = self.items.get(req.get("app")), self.items.get(req.get("logo"))
        if not app or app["kind"] != "app" or not logo or logo["kind"] != "logo": raise ValueError("unknown app or badge id")
        style = dib.ALIASES.get(req.get("style", ""), req.get("style", ""))
        if style not in dib.STYLES: raise ValueError(f"unknown style {req.get('style')!r}")
        size = str(req.get("size") or "ref")
        if size not in dib.CURL_PRESETS:
            try: size = str(max(0.3, min(1.6, float(size))))
            except ValueError: raise ValueError("size must be ref, bigger or a number")
        defaults = dib.STYLES[style][2]
        overrides = []
        for k, v in (req.get("params") or {}).items():
            if k not in defaults: raise ValueError(f"style {style} has no knob {k!r}")
            if isinstance(v, (list, tuple)): v = ",".join(str(x) for x in v)
            v = str(v).strip()
            if k in dib.KNOB_CHOICES and v not in dib.KNOB_CHOICES[k]: raise ValueError(f"{k} must be one of {dib.KNOB_CHOICES[k]}")
            try: dib.parse_value(v, defaults[k])
            except ValueError: raise ValueError(f"bad value for {k}: {v!r}")
            overrides.append((k, v))
        accent = (req.get("accent") or "").strip()
        if accent and not re.fullmatch(r"#?[0-9a-fA-F]{6}", accent): raise ValueError("accent must be #rrggbb")
        draft = bool(req.get("draft"))
        key = hashlib.sha1(json.dumps([app["id"], logo["id"], style, size, accent, sorted(overrides), draft]).encode()).hexdigest()[:16]
        with self.lock:
            if key in self.results: return self.public(key)
        group, seq = str(req.get("group") or "")[:80], req.get("seq")
        if group and isinstance(seq, int):
            with self.lock: self.latest[group] = max(seq, self.latest.get(group, seq))
        lg = logo["obj"]
        if accent: lg = copy.copy(lg); lg.accent = dib.color(accent, None)
        with self.render_slots:
            if group and isinstance(seq, int) and seq < self.latest.get(group, seq):
                raise Superseded("superseded by a newer request")   # live preview moved on; skip the work
            try:
                img, info = dib.render(app["obj"], lg, style, size, overrides, draft=draft)
            except SystemExit as e: raise ValueError(str(e))
            except RuntimeError as e: raise ValueError(str(e))
        png = os.path.join(self.dir, "results", key + ".png"); img.save(png, compress_level=1 if draft else 6)
        with self.lock:
            self.results[key] = dict(id=key, png=png, icns=None, app=app["obj"].name, logo=lg.name, style=style, info=info, t=time.time())
            if len(self.results) > MAX_RESULTS:
                for old in sorted(self.results.values(), key=lambda r: r["t"])[: len(self.results) - MAX_RESULTS]:
                    for f in (old["png"], old["icns"]):
                        if f and os.path.exists(f): os.remove(f)
                    self.results.pop(old["id"], None)
        return self.public(key)

    def public(self, key):
        r = self.results[key]
        return dict(id=key, app=r["app"], logo=r["logo"], style=r["style"], info=r["info"],
                    png=f"/api/result/{key}.png", icns=f"/api/result/{key}.icns", filename=f"{r['app']} - {r['logo']}")

    def icns(self, key):
        r = self.results[key]
        if not r["icns"]:
            from PIL import Image
            path = os.path.join(self.dir, "results", key + ".icns")
            dib.write_icns(Image.open(r["png"]).convert("RGBA"), path); r["icns"] = path
        return r["icns"]


STORE = None
STYLE_META = None
SVG = None
SAMPLES = {}   # kind -> key -> dict(name, path, recommended, thumb (PNG bytes), obj (loaded lazily), lock)


def source_id(path):
    """Identity used by the UI to refuse duplicates: content hash for files, real path for bundles/folders."""
    if os.path.isfile(path):
        with open(path, "rb") as f: return "file:" + hashlib.sha256(f.read()).hexdigest()
    return "path:" + os.path.realpath(path).rstrip("/")


def load_obj(kind, path, name=None):
    try:
        obj = dib.App(path) if kind == "app" else dib.Logo(path)
    except SystemExit as e:           # the CLI helpers exit with a message
        raise ValueError(str(e))
    except Exception as e:
        raise ValueError(f"could not read {os.path.basename(path)}: {e}")
    if name: obj.name = name
    return obj


def scan_samples():
    """Index the bundled samples and make small thumbnails, so the picker opens instantly."""
    from PIL import Image
    out = {}
    for kind, folder in (("app", SAMPLE_APPS), ("logo", SAMPLE_BADGES)):
        if not os.path.isdir(folder): continue
        keys = sorted({os.path.splitext(n)[0] for n in os.listdir(folder) if n.endswith(".png")})
        meta = {k: (lbl, rec) for k, lbl, rec in SAMPLE_META[kind]}
        order = [k for k, _, _ in SAMPLE_META[kind] if k in keys] + [k for k in keys if k not in meta]
        out[kind] = {}
        for k in order:
            png, svg = os.path.join(folder, k + ".png"), os.path.join(folder, k + ".svg")
            th = Image.open(png).convert("RGBA"); th.thumbnail((160, 160), Image.LANCZOS)
            buf = io.BytesIO(); th.save(buf, "PNG")
            lbl, rec = meta.get(k, (dib.nice_name(k), False))
            path = svg if kind == "logo" and SVG and os.path.exists(svg) else png
            out[kind][k] = dict(src=source_id(path), name=lbl, recommended=rec, thumb=buf.getvalue(), obj=None, lock=threading.Lock(), path=path)
    return out


def preload_samples():
    """Decode every sample in the background (badges first: SVG rasterizing is the slow part)."""
    for kind in ("logo", "app"):
        for s in SAMPLES.get(kind, {}).values():
            with s["lock"]:
                if s["obj"] is None:
                    try: s["obj"] = load_obj(kind, s["path"], s["name"])
                    except ValueError: pass


def safe_name(s):
    s = re.sub(r"[^\w .,()+-]", "_", os.path.basename(str(s)))[:80].strip(" .")
    return s or "file"


def local_path(raw):
    """Validate a local path typed by the user: read-only use, must exist, must be an icon-like file."""
    p = os.path.realpath(os.path.expanduser(str(raw).strip().strip('"').strip("'")))
    if "\x00" in p: raise ValueError("bad path")
    if not os.path.exists(p): raise ValueError(f"not found: {raw}")
    low = p.lower().rstrip("/")
    if not low.endswith(PATH_EXT): raise ValueError("path must be an .icns, .png, .svg, .jpg, .webp file, an .iconset folder or an .app bundle")
    if os.path.isfile(p) and os.path.getsize(p) > MAX_UPLOAD: raise ValueError("file too large (25 MB max)")
    return p


def installed_apps():
    if not IS_MAC: return []
    out = []
    for root in ("/Applications", "/Applications/Utilities", "/System/Applications", os.path.expanduser("~/Applications")):
        try:
            for n in sorted(os.listdir(root)):
                if n.endswith(".app"): out.append(dict(name=n[:-4], path=os.path.join(root, n)))
        except OSError:
            pass
    return out


class Handler(BaseHTTPRequestHandler):
    server_version = "DockIconBadger/1.0"

    def log_message(self, fmt, *args):
        if os.environ.get("DIB_VERBOSE"): sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    # ---- helpers
    def host_ok(self):
        """Refuse other Host headers (DNS-rebinding protection) - the UI is only for this machine."""
        port = self.server.server_address[1]
        return self.headers.get("Host", "") in (f"127.0.0.1:{port}", f"localhost:{port}", f"[::1]:{port}")

    def send(self, code, body, ctype="application/json", headers=None):
        if isinstance(body, (dict, list)): body = json.dumps(body).encode()
        elif isinstance(body, str): body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store"); self.send_header("X-Content-Type-Options", "nosniff")
        for k, v in (headers or {}).items(): self.send_header(k, v)
        self.end_headers(); self.wfile.write(body)

    def error(self, code, msg): self.send(code, {"error": msg})

    def read_body(self, limit):
        n = int(self.headers.get("Content-Length") or 0)
        if n > limit: raise ValueError(f"upload too large ({limit // (1024 * 1024)} MB max)")
        return self.rfile.read(n) if n else b""

    def json_body(self):
        try: return json.loads(self.read_body(MAX_JSON) or b"{}")
        except json.JSONDecodeError: raise ValueError("bad JSON")

    def send_file(self, path, ctype, download=None):
        with open(path, "rb") as f: data = f.read()
        h = {}
        if download: h["Content-Disposition"] = f'attachment; filename="{safe_name(download)}"'
        self.send(200, data, ctype, h)

    # ---- routes
    def do_GET(self):
        if not self.host_ok(): return self.error(403, "forbidden host")
        u = urlparse(self.path); path = u.path
        try:
            if path in STATIC:
                f, ct = STATIC[path]; return self.send_file(os.path.join(WEB, f), ct)
            if path == "/favicon.ico": return self.send_file(os.path.join(WEB, "thumbs", "ref-match.png"), "image/png")
            m = re.fullmatch(r"/thumbs/([a-z0-9-]+)\.png", path)
            if m and os.path.exists(os.path.join(WEB, "thumbs", m.group(1) + ".png")):
                return self.send_file(os.path.join(WEB, "thumbs", m.group(1) + ".png"), "image/png")
            if path == "/api/info":
                return self.send(200, dict(styles=STYLE_META, svg=SVG, mac=IS_MAC, platform=platform.system(),
                                           icns="iconutil" if dib.which("iconutil") else "builtin",
                                           samples=bool(SAMPLES.get("app")), sizes=list(dib.CURL_PRESETS)))
            if path == "/api/apps": return self.send(200, installed_apps())
            if path == "/api/samples":
                return self.send(200, {kind: [dict(key=k, name=s["name"], recommended=s["recommended"], thumb=f"/samples/{kind}/{k}.png")
                                              for k, s in d.items()] for kind, d in SAMPLES.items()})
            m = re.fullmatch(r"/samples/(app|logo)/([\w.-]+)\.png", path)
            if m and m.group(2) in SAMPLES.get(m.group(1), {}):
                return self.send(200, SAMPLES[m.group(1)][m.group(2)]["thumb"], "image/png")
            m = re.fullmatch(r"/api/result/([0-9a-f]{16})\.(png|icns)", path)
            if m:
                key, ext = m.groups()
                with STORE.lock: r = STORE.results.get(key)
                if not r: return self.error(404, "result expired; render again")
                name = f"{r['style']} - {r['app']} - {r['logo']}.{ext}"
                dl = name if parse_qs(u.query).get("download") else None
                if ext == "png": return self.send_file(r["png"], "image/png", dl)
                return self.send_file(STORE.icns(key), "image/icns", name)
            return self.error(404, "not found")
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            self.error(500, str(e))

    def do_POST(self):
        if not self.host_ok(): return self.error(403, "forbidden host")
        u = urlparse(self.path); q = parse_qs(u.query)
        try:
            if u.path == "/api/upload":
                kind = (q.get("kind") or [""])[0]
                if kind not in ("app", "logo"): raise ValueError("kind must be app or logo")
                fname = safe_name((q.get("name") or ["upload.png"])[0])
                ext = os.path.splitext(fname)[1].lower()
                if ext not in UPLOAD_EXT: raise ValueError("upload .icns, .png, .svg, .jpg or .webp files")
                if ext == ".svg" and not SVG: raise ValueError("this computer can't render SVG (install cairo or librsvg); use a PNG instead")
                data = self.read_body(MAX_UPLOAD)
                if not data: raise ValueError("empty upload")
                p = os.path.join(STORE.dir, "uploads", uuid.uuid4().hex + ext)
                with open(p, "wb") as f: f.write(data)
                return self.send(200, STORE.add_item(kind, p, dib.nice_name(fname), "file:" + hashlib.sha256(data).hexdigest()))
            if u.path == "/api/path":
                b = self.json_body(); kind = b.get("kind")
                if kind not in ("app", "logo"): raise ValueError("kind must be app or logo")
                p = local_path(b.get("path", ""))
                if p.lower().endswith(".svg") and not SVG: raise ValueError("this computer can't render SVG (install cairo or librsvg)")
                return self.send(200, STORE.add_item(kind, p))
            if u.path == "/api/sample":
                b = self.json_body(); kind = b.get("kind")
                if kind not in ("app", "logo"): raise ValueError("kind must be app or logo")
                return self.send(200, STORE.sample(kind, str(b.get("key", ""))))
            if u.path == "/api/render":
                return self.send(200, STORE.render(self.json_body()))
            if u.path == "/api/zip":
                ids = self.json_body().get("ids") or []
                buf = io.BytesIO(); seen = set()
                with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
                    for key in ids:
                        with STORE.lock: r = STORE.results.get(str(key))
                        if not r: continue
                        base = f"{safe_name(r['style'])}/{safe_name(r['app'] + ' - ' + r['logo'])}"; n, i = base, 2
                        while n in seen: n = f"{base} ({i})"; i += 1
                        seen.add(n); z.write(r["png"], n + ".png"); z.write(STORE.icns(r["id"]), n + ".icns")
                if not seen: raise ValueError("nothing to download; render first")
                return self.send(200, buf.getvalue(), "application/zip", {"Content-Disposition": 'attachment; filename="dock-icons.zip"'})
            return self.error(404, "not found")
        except Superseded as e:
            self.error(409, str(e))
        except ValueError as e:
            self.error(400, str(e))
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            self.error(500, f"{type(e).__name__}: {e}")


def bind(preferred, host="127.0.0.1", tries=30):
    """HTTP server on the preferred port, or the next free one (then any free port)."""
    for p in list(range(preferred, preferred + tries)) + [0]:
        try:
            return ThreadingHTTPServer((host, p), Handler)
        except OSError:
            continue
    raise SystemExit("no free port found")


def main(argv=None):
    global STORE, STYLE_META, SVG, SAMPLES
    ap = argparse.ArgumentParser(description="Local web UI for Dock Icon Badger (binds to 127.0.0.1 only).")
    ap.add_argument("--port", type=int, default=int(os.environ.get("DIB_PORT", 8765)), help="preferred port (next free one is used if busy)")
    ap.add_argument("--open", action="store_true", help="open the UI in the default browser")
    a = ap.parse_args(argv)
    STYLE_META = dib.styles_metadata(); SVG = dib.svg_backend()
    httpd = bind(a.port); httpd.daemon_threads = True; port = httpd.server_address[1]
    STORE = Store()
    SAMPLES = scan_samples(); threading.Thread(target=preload_samples, daemon=True).start()
    url = f"http://127.0.0.1:{port}"
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    print(f"Dock Icon Badger running at {url}", flush=True)
    if not SVG: print("Note: SVG inputs are disabled (no cairo/librsvg found); PNG and .icns work.", flush=True)
    print("Press Ctrl+C to stop.", flush=True)
    if a.open: threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close(); STORE.cleanup(); print("Stopped; temporary files removed.", flush=True)


if __name__ == "__main__":
    main()
