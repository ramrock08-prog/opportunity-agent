"""Browser test for verification, reset, profile persistence, and logout.

Requires an auth-enabled backend on port 8001 with:
    AUTH_REQUIRED=1
    AUTH_REQUIRE_VERIFIED=1
    AUTH_DEV_SHOW_TOKENS=1
    AUTH_SECRET=<local test secret>
    SENDER_EMAIL/SENDER_PASSWORD unset (dev token mode)

and a Vite server on port 5174 with
VITE_API_BASE=http://127.0.0.1:8001.
"""

import json
import time
import urllib.request

from playwright.sync_api import expect, sync_playwright

APP_URL = "http://127.0.0.1:5174/"
HEALTH_URL = "http://127.0.0.1:8001/api/health"


def main() -> int:
    with urllib.request.urlopen(HEALTH_URL) as response:
        health = json.loads(response.read().decode("utf-8"))

    assert health["auth"] == "required", health

    email = f"e2e-{int(time.time())}@example.com"
    password = "strong-password-123"
    console_errors: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            channel="msedge", headless=True
        )
        page = browser.new_page()

        page.on(
            "console",
            lambda message: console_errors.append(message.text)
            if message.type == "error"
            else None,
        )

        # Mock resume extraction so the browser test does not spend Gemini
        # credits; the real extractor is tested separately.
        page.route(
            "**/api/profile/import-resume",
            lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({
                    "status": "parsed",
                    "filename": "resume.txt",
                    "characters": 120,
                    "profile": {
                        "name": "E2E Student",
                        "degree": "B.Tech",
                        "branch": "ECE",
                        "year_of_study": 3,
                        "skills": ["Python", "React"],
                        "interests": ["AI", "Software Engineering"],
                        "preferred_locations": ["India"],
                        "remote_preferred": True,
                        "opportunity_types": [
                            "internship",
                            "job",
                        ],
                    },
                }),
            ),
        )

        # Avoid spending Tavily/Gemini credits while testing onboarding.
        page.route(
            "**/api/discover",
            lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({
                    "status": "completed",
                    "count": 7,
                    "opportunities": [],
                }),
            ),
        )

        page.goto(APP_URL, wait_until="networkidle")
        expect(page.locator(".auth-card")).to_be_visible(timeout=15_000)
        print("Auth screen is shown when sign-in is required.")

        page.get_by_role("tab", name="Create account").click()
        page.get_by_label("Name").fill("E2E Student")
        page.get_by_label("Email").fill(email)
        page.get_by_label("Password").fill(password)
        page.locator(".auth-submit").click()

        expect(
            page.get_by_role("heading", name="Verify your email")
        ).to_be_visible(timeout=15_000)
        page.get_by_role(
            "button", name="Verify now (development)"
        ).click()

        account = page.locator(".account-box", has_text=email)
        expect(account).to_be_visible(timeout=15_000)
        expect(page.get_by_role("heading", name="Explore opportunities")).to_be_visible()
        print("Registration and email verification sign the user in.")

        # New accounts should be prompted to complete their profile.
        expect(
            page.get_by_role("heading", name="Set up your profile")
        ).to_be_visible(timeout=10_000)

        page.locator("input[type=file]").set_input_files({
            "name": "resume.txt",
            "mimeType": "text/plain",
            "buffer": (
                b"E2E Student. B.Tech ECE. Skills: Python, React."
            ),
        })
        expect(page.get_by_label("Degree")).to_have_value("B.Tech")
        expect(
            page.locator(".resume-message")
        ).to_contain_text("Imported resume.txt")

        page.get_by_role("button", name="Save profile").click()

        # The editor closes and the profile is now populated.
        expect(
            page.get_by_role("button", name="Edit profile")
        ).to_be_visible(timeout=10_000)
        expect(
            page.locator(".auto-discovery-banner")
        ).to_contain_text("Search complete", timeout=15_000)
        print(
            "New-account profile onboarding saves and starts discovery."
        )

        page.locator(".account-box button", has_text="Sign out").click()
        expect(page.locator(".auth-card")).to_be_visible(timeout=10_000)
        print("Sign out returns to the auth screen.")

        # Password reset with the development token.
        page.get_by_role("button", name="Forgot password?").click()
        expect(
            page.get_by_role("heading", name="Reset your password")
        ).to_be_visible()
        page.get_by_label("Email").fill(email)
        page.get_by_role(
            "button", name="Send reset link"
        ).click()
        expect(
            page.get_by_role(
                "heading", name="Choose a new password"
            )
        ).to_be_visible(timeout=10_000)

        new_password = "another-strong-password-456"
        page.get_by_label("New password").fill(new_password)
        page.get_by_role(
            "button", name="Update password"
        ).click()
        expect(
            page.get_by_role("heading", name="Welcome back")
        ).to_be_visible(timeout=10_000)

        page.get_by_label("Email").fill(email)
        page.get_by_label("Password").fill(new_password)
        page.locator(".auth-submit").click()
        expect(
            page.locator(".account-box", has_text=email)
        ).to_be_visible(timeout=15_000)
        print("Password reset and login work.")

        page.get_by_role("button", name="Edit profile").click()
        expect(page.get_by_label("Degree")).to_have_value(
            "B.Tech", timeout=10_000
        )
        print("Profile data survived logout, reset, and login.")

        browser.close()

    if console_errors:
        print("Browser console errors:")
        for error in console_errors:
            print(f" - {error}")
        return 1

    print("All authentication browser tests passed!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())