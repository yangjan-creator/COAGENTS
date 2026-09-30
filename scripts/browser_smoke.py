"""Opt-in local UI smoke test; creates only explicitly synthetic demo records."""

import json
from pathlib import Path
from uuid import uuid4

import httpx
from dotenv import dotenv_values
from playwright.sync_api import expect, sync_playwright

from apc.demo import seed


def main():
    root = Path(__file__).resolve().parents[1]
    token = dotenv_values(root / ".env").get("COAGENTS_ADMIN_TOKEN", "")
    url = "http://127.0.0.1:8310"
    headers = {"Authorization": "Bearer " + token} if token else {}
    with httpx.Client(base_url=url, headers=headers) as client:
        seed(client)
        projects = client.get("/projects").json()
        project = next(p for p in projects if p["key"] == "DEMO")
        data = client.get("/workspace").json()
        layout = data["default_layout"]

    errors = []
    suffix = uuid4().hex[:8]
    screenshots = root / "docs" / "screenshots"
    screenshots.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1080})
        context.add_init_script(
            "sessionStorage.setItem('coagents-token', " + json.dumps(token) + ");"
        )
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(url + "/dashboard")
        page.locator(".metric").first.wait_for()
        page.locator("#project").select_option(project["id"])
        assert page.locator("#error").is_hidden()
        page.screenshot(path=str(screenshots / "workspace.png"))

        page.locator("#new-item").click()
        form = page.locator("#editor-form")
        form.locator('[name="key"]').fill("UI-" + suffix)
        form.locator('[name="title"]').fill("瀏覽器合成檢查 " + suffix)
        form.locator('[name="description"]').fill("純合成；驗證 UI 與 SQL 寫入，不操作產品資料。")
        form.locator('[type="submit"]').click()
        page.locator("#editor").wait_for(state="hidden")
        page.get_by_role("button", name="瀏覽器合成檢查 " + suffix, exact=True).click()
        page.locator("#drawer").wait_for(state="visible")
        page.locator("[data-claim]").click()
        page.locator("#drawer-content").get_by_text("負責人", exact=True).wait_for()
        page.locator("[data-progress]").click()
        form.locator('[name="status"]').select_option("WORKING")
        form.locator('[name="progress_percent"]').fill("35")
        form.locator('[name="message"]').fill("UI smoke: progress round trip")
        form.locator('[type="submit"]').click()
        page.locator("#editor").wait_for(state="hidden")
        expect(page.locator("#drawer-content .detailrow").filter(has_text="進度")).to_contain_text("35%")
        page.locator("[data-edit]").click()
        form.locator('[name="description"]').fill("合成內容更新已讀回 " + suffix)
        form.locator('[type="submit"]').click()
        page.locator("#editor").wait_for(state="hidden")
        expect(page.locator("#drawer-content .description")).to_have_text("合成內容更新已讀回 " + suffix)
        page.locator("#close-drawer").click()

        page.locator('[data-action="summary"]').click()
        form.locator('[name="body_markdown"]').fill("瀏覽器 PM Summary 合成讀寫 " + suffix)
        form.locator('[type="submit"]').click()
        page.locator("#editor").wait_for(state="hidden")
        page.locator(".summary-entry").get_by_text("瀏覽器 PM Summary 合成讀寫 " + suffix, exact=True).wait_for()

        page.locator('[data-view="templates"]').click()
        page.locator('[data-action="template"]').click()
        form.locator('[name="name"]').fill("UI template " + suffix)
        layout["widgets"] = [{"type": "table", "query": "items", "title": "客製管制表 " + suffix,
                              "columns": ["title", "version", "validation"]}]
        form.locator('[name="layout"]').fill(json.dumps(layout))
        form.locator('[type="submit"]').click()
        page.locator("#editor").wait_for(state="hidden")
        page.get_by_role("heading", name="UI template " + suffix, exact=True).wait_for()
        page.locator('[data-view="overview"]').click()
        page.locator("#active-template").select_option(label="UI template " + suffix)
        page.get_by_role("heading", name="客製管制表 " + suffix, exact=True).wait_for()
        assert page.locator("#content th").all_text_contents() == ["工作項目", "交付版本", "驗證"]
        page.locator("#active-template").select_option("")

        for view in ["board", "versions", "assets", "timeline", "templates", "members"]:
            page.locator('[data-view="' + view + '"]').click()
            assert page.locator("#error").is_hidden(), view
            assert page.locator("#content").inner_text().strip(), view
        page.locator('[data-view="overview"]').click()
        page.set_viewport_size({"width": 390, "height": 844})
        page.locator("#toast").wait_for(state="hidden")
        page.screenshot(path=str(screenshots / "mobile.png"))
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), "mobile overflow"
        browser.close()
    assert not errors, errors
    print("PASS: PostgreSQL-backed UI create/claim/progress/summary/template; 7 views; mobile; zero JS errors")


if __name__ == "__main__":
    main()
