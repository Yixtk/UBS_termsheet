TEST_CASES = [
    {
        "name": "BNP Phoenix S&P500 Single",
        "pdf_path": "data/BNP-PhoenixSnowball-SP500-XS1083630027-TS.pdf",
        "expected": {
            "structure_type": "single",
            "min_underlyings": 1,
            "must_have_dates": [
                "observation_dates",
                "valuation_date"
            ]
        }
    },
    {
        "name": "IT0006764473 Term Sheet",
        "pdf_path": "data/IT0006764473-TS.pdf",
        "expected": {
            "structure_type": "worst_of",
            "min_underlyings": 1,
            "must_have_dates": [
                "observation_dates",
                "valuation_date",
                "maturity_date"
            ]
        }
    }
]

