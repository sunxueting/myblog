#!/usr/bin/env python3
"""Build a self-contained index.html with all dependencies inlined.
   Run: python3 build_standalone.py
   Output: index_standalone.html (zero external requests)
"""
import subprocess
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))

# CDN URLs (bootcdn = China-friendly, jsdelivr = fallback)
CDN_OPTIONS = {
    "React": [
        "https://cdn.bootcdn.net/ajax/libs/react/18.2.0/umd/react.production.min.js",
        "https://cdn.jsdelivr.net/npm/react@18/umd/react.production.min.js",
    ],
    "ReactDOM": [
        "https://cdn.bootcdn.net/ajax/libs/react-dom/18.2.0/umd/react-dom.production.min.js",
        "https://cdn.jsdelivr.net/npm/react-dom@18/umd/react-dom.production.min.js",
    ],
}

def download(url, label):
    """Download via curl (better SSL handling on macOS)"""
    print(f"  Downloading {label} from {url[:60]}...")
    try:
        result = subprocess.run(
            ["curl", "-sS", "--connect-timeout", "10", "--max-time", "20", "-L", url],
            capture_output=True, text=True, timeout=25
        )
        if result.returncode != 0:
            print(f"    curl error: {result.stderr.strip()[:200]}")
            return None
        if len(result.stdout) < 100:
            print(f"    Response too short ({len(result.stdout)} bytes)")
            return None
        return result.stdout
    except Exception as e:
        print(f"    Exception: {e}")
        return None

def main():
    print("=== Building standalone index.html ===\n")

    # 1. Download React
    react_js = None
    for url in CDN_OPTIONS["React"]:
        react_js = download(url, "React 18")
        if react_js:
            break
    if not react_js:
        print("FATAL: Cannot download React. Check network and try again.")
        sys.exit(1)

    # 2. Download ReactDOM
    react_dom_js = None
    for url in CDN_OPTIONS["ReactDOM"]:
        react_dom_js = download(url, "ReactDOM 18")
        if react_dom_js:
            break
    if not react_dom_js:
        print("FATAL: Cannot download ReactDOM. Check network and try again.")
        sys.exit(1)

    # 3. Read data.js
    data_js_path = os.path.join(BASE, "data.js")
    if not os.path.exists(data_js_path):
        print("FATAL: data.js not found")
        sys.exit(1)
    with open(data_js_path, "r") as f:
        data_js = f.read()

    # 4. Read index.html
    index_path = os.path.join(BASE, "index.html")
    with open(index_path, "r") as f:
        html = f.read()

    # 5. Build inline scripts
    inline_react = f"<script>\n{react_js}\n</script>"
    inline_react_dom = f"<script>\n{react_dom_js}\n</script>"
    inline_data = f"<script>\n{data_js}\n</script>"

    # 6. Replace external script tags with inline versions
    html = html.replace(
        '<script src="https://unpkg.com/react@18/umd/react.production.min.js"></script>',
        inline_react
    )
    html = html.replace(
        '<script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>',
        inline_react_dom
    )
    html = html.replace(
        '<script src="data.js"></script>',
        inline_data
    )

    # 7. Save
    out_path = os.path.join(BASE, "index_standalone.html")
    with open(out_path, "w") as f:
        f.write(html)

    size_kb = os.path.getsize(out_path) / 1024
    sc_open = html.count("<script")
    sc_close = html.count("</script>")

    print(f"\n{'='*50}")
    print(f"Done! Output: index_standalone.html ({size_kb:.0f} KB)")
    print(f"Script tags: {sc_open} open / {sc_close} close")
    print(f"External requests remaining: 1 (Tailwind CDN only)")
    print(f"\nTo deploy:")
    print(f"  cp index_standalone.html index.html")
    print(f"  git add index.html build_standalone.py")
    print(f"  git commit -m 'Inline React/ReactDOM/data.js'")
    print(f"  git push origin main")

if __name__ == "__main__":
    main()
