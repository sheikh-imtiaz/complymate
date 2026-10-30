import pytest

from complymate.domain.screening.matcher import best_match, normalize, score_names
from complymate.domain.screening.watchlist_parser import parse_dfat_csv, parse_simple_csv


def test_normalize_strips_accents_honorifics_and_suffixes():
    assert normalize("Dr. José  Álvarez-Núñez") == "jose alvarez nunez"
    assert normalize("Northern Star Shipping LLC", entity=True) == "northern star shipping"


@pytest.mark.parametrize(
    ("query", "candidate", "minimum"),
    [
        ("Viktor Ivanov", "Viktor Petrovich Ivanov", 85),
        ("Ivanov Viktor", "Viktor Ivanov", 95),
        ("Abdulrahman Al Fulani", "Abdul Rahman Al-Fulani", 85),
        ("Sergey Volkov", "Sergei Volkov", 88),
    ],
)
def test_likely_matches_score_high(query, candidate, minimum):
    assert score_names(query, candidate).score >= minimum


@pytest.mark.parametrize(("query", "candidate"), [("Jane Citizen", "Viktor Ivanov"), ("John", "John Smith")])
def test_unrelated_or_partial_names_score_low(query, candidate):
    assert score_names(query, candidate).score < 85


def test_exact_match_is_100():
    assert score_names("Kim Chol Su", "kim chol su").score == 100


def test_dob_mismatch_reduces_score():
    same = best_match("Viktor Ivanov", ["Viktor Ivanov"], query_dob="1961-03-14", entry_dob="1961-03-14")
    diff = best_match("Viktor Ivanov", ["Viktor Ivanov"], query_dob="1990-01-01", entry_dob="1961-03-14")
    assert same.score > diff.score
    assert diff.score < 90


def test_year_only_dob_compatible():
    m = best_match("Kim Chol Su", ["Kim Chol Su"], query_dob="1970-05-01", entry_dob="1970")
    assert m.method.endswith("+dob")


def test_parse_dfat_groups_aliases():
    csv_text = (
        "Reference,Name of Individual or Entity,Type,Name Type,Date of Birth,Citizenship,Committees\n"
        "123,John Doe,Individual,Primary Name,1970,AU,Test\n"
        "123a,Johnny Doe,Individual,Alias,,,\n"
        "124,Bad Corp,Entity,Primary Name,,,\n"
    )
    entries = parse_dfat_csv(csv_text)
    assert len(entries) == 2
    john = next(e for e in entries if e.reference == "123")
    assert john.aliases == ["Johnny Doe"]
    assert john.entity_type == "individual"


def test_parse_simple_csv():
    entries = parse_simple_csv("Source,Reference,Name,Type,Aliases\nNZ,1,Some Person,Individual,A;B\n")
    assert entries[0].aliases == ["A", "B"]
