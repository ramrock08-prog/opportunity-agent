from opportunity import Opportunity
from storage import DATA_FILE, load_opportunities, save_opportunities

# Preserve any existing opportunity data during this test.
original_data = DATA_FILE.read_bytes() if DATA_FILE.exists() else None

try:
    sample = Opportunity(
        title="Storage Test Internship",
        type="internship",
        organization="Example Organization",
        source_url="https://example.com/internship",
        application_url="https://example.com/apply",
        confidence=0.9,
        required_skills=["Python", "Machine Learning"],
    )

    save_opportunities([sample])
    loaded = load_opportunities()

    assert len(loaded) == 1
    assert loaded[0].title == "Storage Test Internship"
    assert loaded[0].required_skills == ["Python", "Machine Learning"]

    print("Storage test passed!")
    print("Saved and loaded:", loaded[0].title)
    print("Skills preserved:", loaded[0].required_skills)

finally:
    if original_data is None:
        DATA_FILE.unlink(missing_ok=True)
    else:
        DATA_FILE.write_bytes(original_data)
