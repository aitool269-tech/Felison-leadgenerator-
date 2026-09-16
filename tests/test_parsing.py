from app import clean_plaats, norm_naam, norm_naam_relatie, parse_adres


def test_parse_adres_standaardformaat():
    straat, postcode, plaats = parse_adres("De Weidenweg 9 7961LN Ruinerwold NL")
    assert straat == "De Weidenweg 9"
    assert postcode == "7961LN"
    assert plaats == "Ruinerwold"


def test_parse_adres_zonder_nl_suffix():
    straat, postcode, plaats = parse_adres("Kerkstraat 1 1234AB Amsterdam")
    assert straat == "Kerkstraat 1"
    assert postcode == "1234AB"
    assert plaats == "Amsterdam"


def test_parse_adres_zonder_postcode_geeft_hele_string_als_straat():
    straat, postcode, plaats = parse_adres("Onbekend adres zonder postcode")
    assert straat == "Onbekend adres zonder postcode"
    assert postcode is None
    assert plaats is None


def test_parse_adres_lege_string_geeft_alles_none():
    assert parse_adres("") == (None, None, None)
    assert parse_adres(None) == (None, None, None)


def test_norm_naam_verwijdert_diakrieten_en_leestekens():
    assert norm_naam("Müller & Zörgiebel B.V.") == "mullerzorgiebelbv"


def test_norm_naam_lege_input():
    assert norm_naam("") == ""
    assert norm_naam(None) == ""


def test_norm_naam_relatie_negeert_rechtsvorm_en_generieke_woorden():
    assert norm_naam_relatie("Kantoor B.V.") == norm_naam_relatie("Kantoor Adviesgroep B.V.")
    assert norm_naam_relatie("Kantoor B.V.") == "kantoor"


def test_norm_naam_relatie_verschillende_kantoren_blijven_verschillend():
    assert norm_naam_relatie("Kantoor Jansen B.V.") != norm_naam_relatie("Kantoor Pietersen B.V.")


def test_norm_naam_relatie_lege_input():
    assert norm_naam_relatie("") == ""
    assert norm_naam_relatie(None) == ""


def test_clean_plaats_strip_gemeente_prefix():
    assert clean_plaats("Gemeente Rotterdam") == "Rotterdam"


def test_clean_plaats_strip_gemeente_suffix_met_komma():
    assert clean_plaats("Oosterblokker, Gemeente Drechterland") == "Oosterblokker"


def test_clean_plaats_geen_wijziging_nodig():
    assert clean_plaats("Amsterdam") == "Amsterdam"


def test_clean_plaats_none_blijft_none():
    assert clean_plaats(None) is None
