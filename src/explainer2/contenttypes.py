"""Canonical content-type registry (operator decision 2026-07-06).

One production system, four content types. The media plane (narrate → align →
render → mux) is type-agnostic; a content type changes only generation-plane
behavior: which playbooks are read, what the package must contain, and how the
video is branded. Keep this a data table, not a class hierarchy — anything
type-specific in code looks the answer up here.

Branding rule (operator decision 2026-07-05, ISO 14971 series): the word
"Masterclass" is reserved for PAID content. The same multi-part production
published free on YouTube is branded "The Operator's Guide to X". Internally
both are content_type "masterclass"; `distribution` decides the public brand.
"""

# Package deliverables per type: the files validate.py enforces under package/
# (SKILL §8d), plus whether the A/B thumbnail pair is required.
CONTENT_TYPES = {
    "deepdive": {
        "label": "Deep dive",
        "default_aspect": "16:9",
        "playbooks": ["blueprint-playbook", "script-playbook", "spoken-humanizer",
                      "motion-playbook", "shorts-playbook", "thumbnail-playbook",
                      "article-playbook"],
        "package_files": ["meta.json", "article.md", "linkedin.md"],
        "package_thumbnails": True,
        "blurb": "standalone retention-engineered teaching video (~8–25 min); the channel default",
    },
    "short": {
        "label": "Short",
        "default_aspect": "9:16",
        "playbooks": ["shorts-playbook", "spoken-humanizer", "motion-playbook"],
        # Standalone shorts-only runs; derived cuts under <parent>/shorts/ are
        # packaged by their parent and never run validate themselves.
        "package_files": ["meta.json"],
        "package_thumbnails": False,
        "blurb": "9:16 vertical; usually a derived cut of a parent video, sometimes standalone",
    },
    "masterclass": {
        "label": "Masterclass / Operator's Guide episode",
        "default_aspect": "16:9",
        "playbooks": ["masterclass-playbook", "blueprint-playbook", "script-playbook",
                      "spoken-humanizer", "motion-playbook", "shorts-playbook",
                      "thumbnail-playbook", "article-playbook"],
        "package_files": ["meta.json", "article.md", "linkedin.md"],
        "package_thumbnails": True,
        "blurb": "one episode of a multi-part series that teaches a large concept in order; "
                 "episodes build on each other (vs. deep dives, which stand alone)",
    },
    "promo": {
        "label": "Promotional video",
        "default_aspect": "16:9",
        "playbooks": ["promo-playbook", "spoken-humanizer", "motion-playbook",
                      "thumbnail-playbook"],
        # A commercial has no companion essay; the offer's landing page is the
        # written piece. linkedin.md still ships (the operator shares the promo).
        "package_files": ["meta.json", "linkedin.md"],
        "package_thumbnails": True,
        "blurb": "a direct-response piece for ONE specific offer/event/book — copywriting "
                 "best practices, multiple CTAs; a little commercial, not a lesson",
    },
}

DISTRIBUTIONS = ("youtube", "paywalled")


def brand_label(distribution):
    """Public series brand for a masterclass-type project (2026-07-05 rule)."""
    return "Masterclass" if distribution == "paywalled" else "The Operator's Guide"


def infer_from_aspect(aspect):
    """Legacy projects (no content_type in project.json) — every 16:9 project to
    date is a deep dive and every 9:16 one a short, so infer from the aspect."""
    return "deepdive" if aspect == "16:9" else "short"


def package_requirements(content_type):
    """(files, thumbnails_required) validate.py enforces; unknown types get the
    deep-dive (strictest) set so a typo never relaxes the gate."""
    ct = CONTENT_TYPES.get(content_type, CONTENT_TYPES["deepdive"])
    return ct["package_files"], ct["package_thumbnails"]
