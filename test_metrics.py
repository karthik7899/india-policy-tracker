import pytest
from metrics import detect_emerging_players


@pytest.fixture
def empty_watchlist():
    return {}


@pytest.fixture
def mock_watchlist():
    return {
        "technology": [
            {"ticker": "TCS", "name": "Tata Consultancy Services"},
            {"ticker": "INFY", "name": "Infosys Ltd"},
        ],
        "finance": [{"ticker": "HDFC", "name": "HDFC Bank"}],
    }


def test_detect_emerging_players_happy_path(empty_watchlist):
    brief_data = {
        "technology": [{"title": "New Tech Corp announces major breakthrough."}]
    }

    result = detect_emerging_players(brief_data, empty_watchlist)
    assert "technology" in result
    assert "New Tech Corp" in result["technology"]
    assert len(result["technology"]) == 1


def test_detect_emerging_players_existing_player(mock_watchlist):
    brief_data = {"technology": [{"title": "Infosys Ltd reports Q3 earnings."}]}

    result = detect_emerging_players(brief_data, mock_watchlist)
    assert "technology" not in result


def test_detect_emerging_players_ignored_words(empty_watchlist):
    brief_data = {
        "infrastructure": [
            {"title": "India Infrastructure announces new projects."},
            {"title": "Delhi Limited to build new roads."},
            {"title": "Government Corp takes new initiatives."},
        ]
    }

    result = detect_emerging_players(brief_data, empty_watchlist)
    assert "infrastructure" not in result


def test_detect_emerging_players_skip_emerging_players_sector(empty_watchlist):
    brief_data = {
        "emerging_players": [{"title": "Future Technologies is rising fast."}]
    }

    result = detect_emerging_players(brief_data, empty_watchlist)
    assert "emerging_players" not in result


def test_detect_emerging_players_regex_patterns(empty_watchlist):
    brief_data = {
        "various": [
            {"title": "Alpha Ltd is good."},
            {"title": "Beta Limited is good."},
            {"title": "Gamma Corp is good."},
            {"title": "Delta Corporation is good."},
            {"title": "Epsilon Technologies is good."},
            {"title": "Zeta Enterprises is good."},
            {"title": "Eta Solutions is good."},
            {"title": "Theta Infrastructure is good."},
        ]
    }

    result = detect_emerging_players(brief_data, empty_watchlist)
    assert "various" in result
    expected = [
        "Alpha Ltd",
        "Beta Limited",
        "Gamma Corp",
        "Delta Corporation",
        "Epsilon Technologies",
        "Zeta Enterprises",
        "Eta Solutions",
        "Theta Infrastructure",
    ]
    for exp in expected:
        assert exp in result["various"]
    assert len(result["various"]) == 8


def test_detect_emerging_players_short_name_filtering(empty_watchlist):
    brief_data = {
        "technology": [
            {"title": "A Ltd announces a new product."},
            {"title": "Ab Corp is doing well."},
        ]
    }

    result = detect_emerging_players(brief_data, empty_watchlist)
    assert "technology" not in result


def test_detect_emerging_players_multiple_occurrences(empty_watchlist):
    brief_data = {
        "technology": [
            {"title": "Alpha Tech Corp is good. Alpha Tech Corp wins award."}
        ]
    }

    result = detect_emerging_players(brief_data, empty_watchlist)
    assert "technology" in result
    assert result["technology"] == ["Alpha Tech Corp"]  # should be unique
