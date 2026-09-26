"""plate_normalizer.py — Indian plate format validation, confusable-
character correction, and BH-series support. Pure string logic, no model
needed.
"""

from __future__ import annotations

import plate_normalizer as pn


class TestStandardFormat:
    def test_already_valid_plate_passes_through(self):
        assert pn.normalize("MH12AB1234") == ("MH12AB1234", "MH")

    def test_lowercase_and_spaces_are_normalized(self):
        assert pn.normalize("mh 12 ab 1234") == ("MH12AB1234", "MH")

    def test_punctuation_is_stripped(self):
        assert pn.normalize("MH-12-AB-1234") == ("MH12AB1234", "MH")

    def test_unrecognized_state_code_is_rejected(self):
        # "XX" is not a real Indian state/UT code.
        assert pn.normalize("XX12AB1234") is None

    def test_garbage_text_is_rejected(self):
        assert pn.normalize("NOT A PLATE") is None

    def test_empty_string_is_rejected(self):
        assert pn.normalize("") is None

    def test_single_letter_series_is_valid(self):
        assert pn.normalize("DL1A1234") == ("DL1A1234", "DL")

    def test_three_letter_series_is_valid(self):
        assert pn.normalize("KA01ABC1234") == ("KA01ABC1234", "KA")


class TestConfusableCorrection:
    def test_zero_to_letter_o_correction(self):
        # "GJ01A81234" -> only valid if the '8' should be 'B'.
        assert pn.normalize("GJ01A81234") == ("GJ01AB1234", "GJ")

    def test_correction_only_applied_when_needed(self):
        # Already valid — must NOT be "corrected" into a different plate.
        assert pn.normalize("MH12AB1234") == ("MH12AB1234", "MH")

    def test_uncorrectable_garbage_is_rejected(self):
        # No single confusable swap makes this a valid plate.
        assert pn.normalize("QQQQQQQQQQ") is None


class TestBhSeries:
    def test_valid_bh_series_plate(self):
        assert pn.normalize("22BH1234AB") == ("22BH1234AB", "BH")

    def test_bh_series_single_letter_suffix(self):
        assert pn.normalize("21BH1234A") == ("21BH1234A", "BH")

    def test_bh_series_lowercase_and_spaces(self):
        assert pn.normalize("22 bh 1234 ab") == ("22BH1234AB", "BH")

    def test_bh_series_wrong_digit_count_is_rejected(self):
        assert pn.normalize("2BH1234AB") is None
