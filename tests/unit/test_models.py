from letterforge.models import (
    ALL_CHARS,
    GRID_COLS,
    SHEET1_CHARS,
    SHEET1_SPEC,
    SHEET2_CHARS,
    SHEET2_SPEC,
    CharCategory,
)


def test_sheet1_char_count():
    # 26 upper + 10 digits + 6 punct
    assert len(SHEET1_CHARS) == 42


def test_sheet2_char_count():
    assert len(SHEET2_CHARS) == 26


def test_all_chars_count():
    assert len(ALL_CHARS) == 68


def test_char_filenames_unique():
    names = [c.filename for c in ALL_CHARS]
    assert len(names) == len(set(names)), "Duplicate filenames detected"


def test_upper_char_filename():
    char = next(c for c in ALL_CHARS if c.char == "A")
    assert char.filename == "upper_A.png"
    assert char.category == CharCategory.UPPER


def test_lower_char_filename():
    char = next(c for c in ALL_CHARS if c.char == "a")
    assert char.filename == "lower_a.png"
    assert char.category == CharCategory.LOWER


def test_digit_char_filename():
    char = next(c for c in ALL_CHARS if c.char == "0")
    assert char.filename == "digit_0.png"
    assert char.category == CharCategory.DIGIT


def test_punct_filenames():
    punct_chars = [c for c in ALL_CHARS if c.category == CharCategory.PUNCT]
    names = {c.char: c.filename for c in punct_chars}
    assert names["!"] == "punct_exclamation.png"
    assert names["?"] == "punct_question.png"
    assert names["."] == "punct_period.png"
    assert names[","] == "punct_comma.png"
    assert names[":"] == "punct_colon.png"
    assert names[";"] == "punct_semicolon.png"


def test_sheet_spec_grid_rows():
    # 42 chars / 9 cols = ceil(42/9) = 5
    assert SHEET1_SPEC.grid_rows == 5
    # 26 chars / 9 cols = ceil(26/9) = 3
    assert SHEET2_SPEC.grid_rows == 3


def test_sheet_spec_grid_cols():
    assert SHEET1_SPEC.grid_cols == GRID_COLS
    assert SHEET2_SPEC.grid_cols == GRID_COLS
