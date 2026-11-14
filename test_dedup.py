from opportunity import Opportunity
from dedup import deduplicate_opportunities

items = [
    Opportunity(
        title="AI Internship",
        type="internship",
        source_url="https://www.example.com/internship?utm_source=a",
        confidence=0.6,
    ),
    Opportunity(
        title="AI Internship",
        type="internship",
        source_url="https://example.com/internship/?utm_source=b",
        confidence=0.9,
    ),
    Opportunity(
        title="Data Science Hackathon",
        type="hackathon",
        source_url="https://example.org/event",
        confidence=0.8,
    ),
]

unique = deduplicate_opportunities(items)

print("Original records:", len(items))
print("Unique records:", len(unique))
print("Kept AI Internship confidence:", unique[0].confidence)

assert len(unique) == 2
assert unique[0].confidence == 0.9

print("Deduplication test passed!")
