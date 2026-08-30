from trading_research.scripts.enrich_contextual_research import enrich_document


def test_enrich_document_adds_optional_contextual_research():
    document = {
        "generatedAt": "2026-08-28",
        "stocks": [
            {
                "code": "TEST.US",
                "name": "TEST",
                "market": "US",
                "timezone": "America/New_York",
                "lastTradeDay": "2026-08-28",
                "indicators": {
                    "lastClose": 100.0,
                    "atr20": 2.0,
                    "support": 98.0,
                    "resistance": 102.0,
                    "nearestKeyLevel": 100.0,
                    "yesterdayLow": 99.0,
                    "yesterdayHigh": 101.0,
                    "vwap": None,
                    "vwapDev": None,
                    "vwapDevThreshold": 1.0,
                    "orbHigh": None,
                    "orbLow": None,
                },
                "levels": [],
                "daily": [],
                "intraday": None,
            }
        ],
    }
    enriched = enrich_document(document)
    assert enriched["stocks"] == document["stocks"]
    assert enriched["contextualResearch"]["coverage"]["evaluated"] == 1
    assert enriched["contextualResearch"]["contexts"][0]["instrument"]["code"] == "TEST.US"
