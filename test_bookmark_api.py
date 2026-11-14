from fastapi.testclient import TestClient
from pathlib import Path

from api import app
from bookmarks import BOOKMARKS_FILE

# Preserve any existing bookmarks during this test.
original_data = (
    BOOKMARKS_FILE.read_bytes()
    if BOOKMARKS_FILE.exists()
    else None
)

test_url = "https://example.com/opportunity-agent-bookmark-test"
client = TestClient(app)

try:
    # Save a test bookmark.
    response = client.post(
        "/api/bookmarks",
        json={"url": test_url},
    )
    assert response.status_code == 200, response.text
    assert test_url in response.json()["bookmarks"]
    print("POST bookmark: OK")

    # Verify it can be retrieved.
    response = client.get("/api/bookmarks")
    assert response.status_code == 200, response.text
    assert test_url in response.json()["bookmarks"]
    print("GET bookmarks: OK")

    # Remove the test bookmark.
    response = client.delete(
        "/api/bookmarks",
        params={"url": test_url},
    )
    assert response.status_code == 200, response.text
    assert test_url not in response.json()["bookmarks"]
    print("DELETE bookmark: OK")

    print("All bookmark API tests passed!")

finally:
    # Restore the original bookmark file exactly.
    if original_data is None:
        BOOKMARKS_FILE.unlink(missing_ok=True)
    else:
        BOOKMARKS_FILE.write_bytes(original_data)
