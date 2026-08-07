"""全站截图：生产模式启动前后端，Playwright 绕过系统代理截取五个页面。"""
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

PAGES = ["", "signals", "trades", "portfolio", "settings"]


def wait_for(url, timeout=60):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for _ in range(timeout * 2):
        try:
            opener.open(url, timeout=1)
            return True
        except Exception:
            time.sleep(0.5)
    return False


def main():
    root = Path("C:/Work/note/CursorWorkSpace/Professional-Investment")
    shots = root / "docs/design/screenshots"
    shots.mkdir(parents=True, exist_ok=True)
    backend_port = "8011"
    web_port = "3015"

    base_env = os.environ.copy()
    base_env["no_proxy"] = "127.0.0.1,localhost"
    base_env["NO_PROXY"] = "127.0.0.1,localhost"
    node_dir = r"C:\Work\application\NodeJs"
    base_env["PATH"] = node_dir + os.pathsep + base_env.get("PATH", "")
    pnpm = r"C:\Users\jarvan_iv\AppData\Roaming\npm\pnpm.cmd"

    print("Starting backend...")
    backend = subprocess.Popen(
        ["uv", "run", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", backend_port],
        cwd=root / "services/quant-api",
        stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT, env=base_env,
    )
    if not wait_for(f"http://127.0.0.1:{backend_port}/api/settings"):
        backend.kill()
        sys.exit("backend did not start")

    print("Starting frontend (production)...")
    web_env = base_env.copy()
    web_env["QUANT_API_URL"] = f"http://127.0.0.1:{backend_port}"
    frontend = subprocess.Popen(
        [pnpm, "start", "-p", web_port],
        cwd=root / "apps/web",
        stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT, env=web_env,
    )
    if not wait_for(f"http://127.0.0.1:{web_port}/settings"):
        backend.kill(); frontend.kill()
        sys.exit("frontend did not start")

    print("Taking screenshots...")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-proxy-server", "--disable-extensions"])
        for vp_name, vp in [("desktop", {"width": 1440, "height": 900}),
                            ("mobile", {"width": 390, "height": 844})]:
            ctx = browser.new_context(viewport=vp)
            page = ctx.new_page()
            for path in PAGES:
                name = path or "dashboard"
                page.goto(f"http://127.0.0.1:{web_port}/{path}", wait_until="networkidle")
                page.wait_for_timeout(800)
                page.screenshot(path=str(shots / f"{name}-{vp_name}.png"), full_page=False)
                print(f"  {name}-{vp_name}.png")
            ctx.close()
        browser.close()

    print("Done.")
    backend.kill()
    frontend.kill()


if __name__ == "__main__":
    main()
