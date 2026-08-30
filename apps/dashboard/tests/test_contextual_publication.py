import pytest

from trading_research.scripts.enrich_contextual_research import enrich_document


def document(data_date):
    return {
        "generatedAt": data_date,
        "stocks": [
            {
                "code": "TEST.US",
                "name": "TEST",
                "market": "US",
                "timezone": "America/New_York",
                "lastTradeDay": data_date,
                "indicators": {"lastClose": 100.0, "atr20": 2.0},
                "levels": [],
                "daily": [],
                "intraday": None,
            }
        ],
    }


def test_enrichment_adds_conditional_research_from_history_documents():
    current = enrich_document(document("2026-08-30"))
    history = {"contextualResearch": current["contextualResearch"]}
    history["contextualResearch"] = {
        **history["contextualResearch"],
        "dataDate": "2026-08-29",
        "contexts": [
            {
                **history["contextualResearch"]["contexts"][0],
                "dataDate": "2026-08-29",
            }
        ],
    }

    enriched = enrich_document(document("2026-08-30"), history_documents=[history])

    conditional = enriched["conditionalResearch"]
    assert conditional["sourceSnapshots"] == 2
    assert conditional["dateRange"] == {"start": "2026-08-29", "end": "2026-08-30"}


def test_enrichment_rejects_malformed_history_context():
    current = enrich_document(document("2026-08-30"))
    malformed = {"contextualResearch": current["contextualResearch"]}
    del malformed["contextualResearch"]["contexts"][0]["instrument"]

    with pytest.raises(ValueError, match="instrument"):
        enrich_document(document("2026-08-30"), history_documents=[malformed])
