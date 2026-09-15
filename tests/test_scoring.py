from datetime import date, timedelta

from app import bereken_score


def dagen_geleden(n):
    return (date.today() - timedelta(days=n)).isoformat()


def basislead(**overrides):
    lead = {
        "begindatum_dienst": None,
        "dienst": "Adviseren / Bemiddelen",
        "beperkingen": None,
        "rechtsvorm": "Eenmanszaak",
        "naam": "Voorbeeld Assurantiën",
        "postcode": None,
        "plaats": None,
    }
    lead.update(overrides)
    return lead


def test_verse_vergunning_binnen_45_dagen_geeft_bonus():
    score, klasse, uitleg = bereken_score(basislead(begindatum_dienst=dagen_geleden(10)))
    assert "verse vergunning (+25)" in uitleg
    assert score == 40 + 25 + 10  # basis + vers + dienst (postcode/plaats onbekend geeft niets)


def test_recente_vergunning_tussen_45_en_120_dagen_geeft_kleinere_bonus():
    score, klasse, uitleg = bereken_score(basislead(begindatum_dienst=dagen_geleden(90)))
    assert "recente vergunning (+15)" in uitleg


def test_oude_vergunning_boven_120_dagen_geeft_geen_bonus():
    score, klasse, uitleg = bereken_score(basislead(begindatum_dienst=dagen_geleden(200)))
    assert "oudere vergunning (+0)" in uitleg


def test_geen_begindatum_dienst_slaat_de_regel_over():
    score, klasse, uitleg = bereken_score(basislead(begindatum_dienst=None))
    assert not any("vergunning (+" in u for u in uitleg.split("; "))


def test_afwijkende_dienst_geeft_min_10():
    score, klasse, uitleg = bereken_score(basislead(dienst="Bemiddelen in schadeverzekeringen"))
    assert "afwijkende dienst" in uitleg
    assert score == 40 - 10


def test_beperkingen_geeft_min_30():
    score, klasse, uitleg = bereken_score(basislead(beperkingen="Alleen betalingsbeschermers"))
    assert "beperkte vergunning" in uitleg
    assert score == 40 + 10 - 30


def test_bv_in_rechtsvorm_geeft_plus_10():
    score, klasse, uitleg = bereken_score(basislead(rechtsvorm="Besloten vennootschap"))
    assert "B.V./N.V. (+10)" in uitleg


def test_bv_in_naam_geeft_ook_plus_10_ook_zonder_rechtsvorm():
    score, klasse, uitleg = bereken_score(basislead(rechtsvorm="Onbekend", naam="Jansen Advies B.V."))
    assert "B.V./N.V. (+10)" in uitleg


def test_postcode_bekend_geeft_plus_10():
    score, klasse, uitleg = bereken_score(basislead(postcode="1234AB"))
    assert "volledig adres bekend (+10)" in uitleg


def test_alleen_plaats_bekend_geeft_plus_5():
    score, klasse, uitleg = bereken_score(basislead(plaats="Rotterdam"))
    assert "vestigingsplaats bekend (+5)" in uitleg


def test_geen_postcode_en_geen_plaats_geeft_niets():
    score, klasse, uitleg = bereken_score(basislead())
    assert "adres bekend" not in uitleg


def test_maximale_haalbare_score_is_95_en_klasse_a():
    # Beste combinatie van alle bonussen (via naam, want de B.V.-bonus kijkt naar
    # naam, niet naar rechtsvorm — zie app.py:167-169): 40 + 25 + 10 + 10 + 10 = 95.
    # Nooit hoger dan 95 haalbaar, dus de clamp op 100 (app.py:174) wordt door
    # deze combinatie niet geraakt — dat is bestaand, vastgelegd gedrag.
    lead = basislead(begindatum_dienst=dagen_geleden(1), naam="Test Kantoor B.V.", postcode="1234AB")
    score, klasse, uitleg = bereken_score(lead)
    assert score == 95
    assert klasse == "A"


def test_minimale_haalbare_score_is_0():
    # Slechtste combinatie: 40 - 10 (afwijkende dienst) - 30 (beperkingen) = 0.
    lead = basislead(dienst="Iets anders", beperkingen="Ja", begindatum_dienst=dagen_geleden(200))
    score, klasse, uitleg = bereken_score(lead)
    assert score == 0
    assert klasse == "C"


def test_klasse_a_vanaf_70():
    score, klasse, uitleg = bereken_score(basislead(begindatum_dienst=dagen_geleden(10), rechtsvorm="Besloten vennootschap", postcode="1234AB"))
    assert score >= 70
    assert klasse == "A"


def test_klasse_c_onder_50():
    score, klasse, uitleg = bereken_score(basislead(dienst="Iets anders"))
    assert score < 50
    assert klasse == "C"
