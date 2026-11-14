from opportunity import Opportunity
from text_utils import clean_list, clean_text


def test_clean_text_repairs_lost_possessive():
    assert clean_text("Bachelor\ufffds degree") == "Bachelor's degree"
    assert clean_text("  AI   Research  ") == "AI Research"


def test_clean_text_removes_replacement_artifacts():
    assert clean_text("Intern \ufffd\ufffd 2027") == "Intern \u2014 2027"
    assert clean_text("Bad \ufffd text") == "Bad text"


def test_clean_list_deduplicates_and_drops_empty():
    assert clean_list(["Python", " Python ", "", None, "AI"]) == [
        "Python",
        "AI",
    ]


def test_opportunity_cleans_extracted_fields():
    opportunity = Opportunity(
        title="  Intern\ufffds Role ",
        type="internship",
        description="Build  models.\nShip them.",
        location="  ",
        eligibility=["  CGPA 8  ", "CGPA 8", ""],
        source_url=" https://example.com/job ",
        application_url="https://example.com/apply ",
        confidence=0.9,
    )

    assert opportunity.title == "Intern's Role"
    assert opportunity.description == "Build models. Ship them."
    assert opportunity.location == "Not specified"
    assert opportunity.eligibility == ["CGPA 8"]
    assert opportunity.source_url == "https://example.com/job"