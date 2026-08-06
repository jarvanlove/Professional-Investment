import subprocess
import sys
from pathlib import Path

def main():
    root = Path("C:/Work/note/CursorWorkSpace/Professional-Investment")
    shots = root / "docs/design/screenshots"
    shots.mkdir(parents=True, exist_ok=True)
    html = root / "scripts/settings-visual-qa.html"

    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"file:///{html.as_posix()}")
        page.screenshot(path=str(shots / "settings-desktop-1440x900.png"), full_page=True)

        page2 = browser.new_page(viewport={"width": 390, "height": 844})
        page2.goto(f"file:///{html.as_posix()}")
        page2.screenshot(path=str(shots / "settings-mobile-390x844.png"), full_page=True)
        browser.close()
    print("Done.")

if __name__ == "__main__":
    main()
