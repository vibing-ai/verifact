""" pytest fixtures:
 pytest_generate_tests is a list of questions for testing with expect_success [True,False] and a min_score

Other potential queries
        queries = [
            "The sky is green during a storm.",
            "Grass is usually yellow.",
            "Water normally boils at 90°C.",
            "The Great Wall of China is visible from space with the naked eye."
        ]
Can potentially add testing with "strict" in  [False, True]
"""

def pytest_generate_tests(metafunc):
    if {"query", "expect_success", "min_score"}.issubset(metafunc.fixturenames):
        test_data = [
            ("Grass is usually yellow.", False, 0.3),
            ("The sun rises in the west.", False, 0.0),
            ("Mount Everest is the tallest mountain in the world.", True, 0.7),
        ]
        metafunc.parametrize(
            argnames=("query", "expect_success", "min_score"),
            argvalues=test_data
        )
