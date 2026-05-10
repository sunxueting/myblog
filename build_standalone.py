#!/usr/bin/env python3
"""Build standalone index.html — inline React/ReactDOM only, keep data.js external.
   Run: python3 build_standalone.py
"""
import subprocess, os, sys

BASE = os.path.dirname(os.path.abspath(__file__))
CDNS = {
    "react": [
        "https://cdn.bootcdn.net/ajax/libs/react/18.2.0/umd/react.production.min.js",
        "https://cdn.jsdelivr.net/npm/react@18/umd/react.production.min.js",
    ],
    "react-dom": [
        "https://cdn.bootcdn.net/ajax/libs/react-dom/18.2.0/umd/react-dom.production.min.js",
        "https://cdn.jsdelivr.net/npm/react-dom@18/umd/react-dom.production.min.js",
    ],
}

def download(url, label):
    print(f"  Downloading {label}...")
    r = subprocess.run(["curl", "-sSL", "--connect-timeout", "10", "--max-time", "20", url],
                       capture_output=True, text=True, timeout=25)
    if r.returncode != 0 or len(r.stdout) < 100:
        return None
    return r.stdout

def main():
    print("=== Building standalone index.html ===\n")

    react_js = None
    for u in CDNS["react"]:
        react_js = download(u, "React 18")
        if react_js: break
    if not react_js: print("FATAL: React download failed"); sys.exit(1)

    dom_js = None
    for u in CDNS["react-dom"]:
        dom_js = download(u, "ReactDOM 18")
        if dom_js: break
    if not dom_js: print("FATAL: ReactDOM download failed"); sys.exit(1)

    with open(os.path.join(BASE, "index.html"), "r") as f:
        html = f.read()

    # Replace unpkg.com CDN with inline React/ReactDOM
    html = html.replace(
        '<script src="https://unpkg.com/react@18/umd/react.production.min.js"></script>',
        f"<script>\n{react_js}\n</script>"
    )
    html = html.replace(
        '<script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>',
        f"<script>\n{dom_js}\n</script>"
    )

    # Move Tailwind CDN from <head> to end of <body> to not block rendering
    html = html.replace(
        '<script src="https://cdn.tailwindcss.com"></script>',
        ''
    )
    html = html.replace(
        '</body>',
        '<script>tailwind={config:{theme:{extend:{fontFamily:{serif:[\'"Noto Serif SC"\',\'"Source Han Serif SC"\',\'"Songti SC"\',\'STSong\',\'Georgia\',\'serif\']}}}}}</script>\n<script async src="https://cdn.tailwindcss.com"></script>\n</body>'
    )

    # Also remove the standalone tailwind config that was in <head> (now at bottom)
    html = html.replace(
        '<script>tailwind.config={theme:{extend:{fontFamily:{serif:[\'"Noto Serif SC"\',\'"Source Han Serif SC"\',\'"Songti SC"\',\'STSong\',\'Georgia\',\'serif\']}}}}</script>',
        ''
    )

    out = os.path.join(BASE, "index_standalone.html")
    with open(out, "w") as f:
        f.write(html)

    kb = os.path.getsize(out) / 1024
    print(f"\nDone! index_standalone.html ({kb:.0f} KB)")
    print("  External requests: data.js + Tailwind CDN (async)")
    print("  data.js stays external (4.5MB, same-origin = fast in WeChat)")
    print("\n  cp index_standalone.html index.html && git add . && git commit -m 'fix' && git push")

if __name__ == "__main__":
    main()
