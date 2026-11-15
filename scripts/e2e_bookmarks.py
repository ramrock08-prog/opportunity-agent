"""End-to-end browser test for bookmark save / refresh / remove.

Requires the FastAPI backend on port 8000 and the Vite dev server on
port 5173. Uses the locally installed Microsoft Edge, so no Chromium
download is required.
"""

import json
import urllib.parse
import urllib.request

from playwright.sync_api import expect, sync_playwright

APP_URL = "http://127.0.0.1:5173/"
API_URL = "http://127.0.0.1:8000"


def api_bookmarks() -> list[str]:
    with urllib.request.urlopen(f"{API_URL}/api/bookmarks") as response:
        return json.loads(response.read().decode("utf-8"))["bookmarks"]


def api_application_urls() -> list[str]:
    with urllib.request.urlopen(
        f"{API_URL}/api/applications"
    ) as response:
        data = json.loads(response.read().decode("utf-8"))

    return [item["source_url"] for item in data["applications"]]


def remove_api_application(url: str) -> None:
    request = urllib.request.Request(
        f"{API_URL}/api/applications?url="
        f"{urllib.parse.quote(url, safe='')}",
        method="DELETE",
    )
    urllib.request.urlopen(request).read()


def set_api_bookmarks(urls: list[str]) -> None:
    """Restore a known bookmark list through the public API."""
    current = api_bookmarks()

    for url in current:
        if url not in urls:
            request = urllib.request.Request(
                f"{API_URL}/api/bookmarks?url={urllib.parse.quote(url, safe='')}",
                method="DELETE",
            )
            urllib.request.urlopen(request).read()

    for url in urls:
        if url not in api_bookmarks():
            request = urllib.request.Request(
                f"{API_URL}/api/bookmarks",
                data=json.dumps({"url": url}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(request).read()


def _run_browser_test(original_bookmarks: list[str]) -> int:
    target_url = None
    console_errors: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page()

        page.on(
            "console",
            lambda message: console_errors.append(message.text)
            if message.type == "error"
            else None,
        )

        page.goto(APP_URL, wait_until="networkidle")

        cards = page.locator(".opportunity-card")
        expect(cards.first).to_be_visible(timeout=15_000)
        card_count = cards.count()
        assert card_count >= 1, "No opportunity cards rendered."
        print(f"Rendered {card_count} opportunity card(s).")

        # Pick a card that is not already bookmarked.
        target = None
        for index in range(card_count):
            card = cards.nth(index)
            button = card.locator(".bookmark-button")
            if "Saved" not in button.inner_text():
                target = card
                break

        assert target is not None, "Every rendered card was already saved."
        title = target.locator("h3").inner_text()
        target_url = target.get_attribute("data-source-url") or None

        if not target_url:
            # Fall back to matching the card title against the API data.
            with urllib.request.urlopen(
                f"{API_URL}/api/opportunities"
            ) as response:
                opportunities = json.loads(response.read().decode("utf-8"))[
                    "opportunities"
                ]
            target_url = next(
                item["source_url"]
                for item in opportunities
                if item["title"] == title
            )

        print(f"Testing bookmark flow for: {title}")

        # 1. Save.
        target.locator(".bookmark-button").click()
        expect(target.locator(".bookmark-button")).to_contain_text(
            "Saved", timeout=10_000
        )
        assert target_url in api_bookmarks(), "POST did not persist bookmark."
        print("Save button persists the bookmark through the API.")

        # 2. Reload and confirm the saved state survives.
        page.reload(wait_until="networkidle")
        reloaded = page.locator(".opportunity-card", has_text=title)
        expect(reloaded.locator(".bookmark-button")).to_contain_text(
            "Saved", timeout=10_000
        )
        print("Saved state survives a page refresh.")

        # 3. Details drawer opens, shows the record, and closes with Escape.
        page.route(
            "**/api/opportunities/verify",
            lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({
                    "status": "checked",
                    "verification": {
                        "application": {
                            "status": "reachable",
                            "status_code": 200,
                            "message": "The page returned HTTP 200.",
                        },
                        "source": {
                            "status": "reachable",
                            "status_code": 200,
                            "message": "The page returned HTTP 200.",
                        },
                        "deadline": {
                            "message": "No deadline was published."
                        },
                        "disclaimer": (
                            "A reachable link does not confirm that "
                            "applications are open."
                        ),
                    },
                }),
            ),
        )

        reloaded.locator(".details-button").click()
        dialog = page.get_by_role("dialog")
        expect(dialog).to_be_visible(timeout=10_000)
        expect(dialog.locator("#detail-title")).to_have_text(title)
        expect(dialog).to_contain_text("extracted automatically")

        dialog.get_by_role(
            "button", name="Check links now"
        ).click()
        expect(dialog).to_contain_text("Reachable", timeout=10_000)
        expect(dialog).to_contain_text(
            "does not confirm that applications are open"
        )

        page.keyboard.press("Escape")
        expect(dialog).to_have_count(0, timeout=10_000)
        print("Details drawer and link check work correctly.")

        # 4. Saved view shows the bookmark.
        page.locator(
            ".side-link", has_text="Saved opportunities"
        ).click()
        expect(page.locator(".opportunity-card", has_text=title)).to_be_visible(
            timeout=10_000
        )
        saved_count = page.locator(".opportunity-card").count()
        assert saved_count >= 1, "Saved view did not render any cards."
        print(f"Saved view shows {saved_count} bookmarked card(s).")

        # 5. Remove from the saved view and confirm it disappears.
        saved_card = page.locator(".opportunity-card", has_text=title)
        saved_card.locator(".bookmark-button").click()
        expect(
            page.locator(".opportunity-card", has_text=title)
        ).to_have_count(0, timeout=10_000)
        assert target_url not in api_bookmarks(), "DELETE did not remove bookmark."
        print("Removing a bookmark updates storage and the Saved view.")

        # 6. Apply flow opens with saved-details fields.
        page.locator(".side-link", has_text="Discover").click()
        apply_card = page.locator(
            ".opportunity-card", has_text=title
        )
        apply_card.locator(".apply-button").click()
        apply_dialog = page.get_by_role("dialog")
        expect(apply_dialog).to_be_visible(timeout=10_000)
        expect(apply_dialog.get_by_label("Phone")).to_be_visible()
        expect(
            apply_dialog.get_by_label("College")
        ).to_be_visible()
        apply_dialog.get_by_role(
            "button", name="Close apply panel"
        ).click()
        print("Apply panel opens with saved-detail fields.")

        # 7. Application tracker from the detail drawer.
        page.locator(".side-link", has_text="Discover").click()
        discover_card = page.locator(
            ".opportunity-card", has_text=title
        )
        discover_card.locator(".details-button").click()
        dialog = page.get_by_role("dialog")
        expect(dialog).to_be_visible(timeout=10_000)
        dialog.get_by_label("Application status").select_option(
            "applied"
        )
        dialog.get_by_role(
            "button", name="Save status"
        ).click()
        expect(
            page.locator(
                ".opportunity-card", has_text=title
            ).locator(".status-pill", has_text="applied")
        ).to_be_visible(timeout=10_000)
        page.keyboard.press("Escape")

        page.locator(
            ".side-link", has_text="Applications"
        ).click()
        expect(
            page.locator(".opportunity-card", has_text=title)
        ).to_be_visible(timeout=10_000)
        print("Application tracker and Applications view work.")

        browser.close()

    if console_errors:
        print("Browser console errors:")
        for error in console_errors:
            print(f" - {error}")
        return 1

    print("All bookmark browser tests passed!")
    return 0


def main() -> int:
    original_bookmarks = api_bookmarks()
    original_applications = api_application_urls()

    try:
        return _run_browser_test(original_bookmarks)
    finally:
        set_api_bookmarks(original_bookmarks)

        for url in api_application_urls():
            if url not in original_applications:
                remove_api_application(url)

        assert api_bookmarks() == original_bookmarks, "Bookmark restore failed."
        assert api_application_urls() == original_applications, (
            "Application restore failed."
        )
        print("Original bookmarks and applications restored.")


if __name__ == "__main__":
    raise SystemExit(main())