import pytest
from PIL import Image

from backend.features.session.infrastructure.pdf_generator.cover_palette import (
    CoverPalette,
)


class TestCoverPaletteFromImage:
    @pytest.mark.parametrize(
        ("colour", "expected_hue", "expected_saturation"),
        [
            ((220, 30, 30), 0.0, 0.76),
            ((30, 200, 60), 131.0, 0.74),
            ((30, 60, 220), 231.0, 0.76),
        ],
    )
    def test_solid_colour_cover_keeps_its_hue_and_saturation(
        self,
        colour: tuple[int, int, int],
        expected_hue: float,
        expected_saturation: float,
    ) -> None:
        image = Image.new("RGB", (64, 64), colour)

        palette = CoverPalette.from_image(image)

        assert palette.hue_degrees == pytest.approx(expected_hue, abs=1.0)
        assert palette.saturation == pytest.approx(expected_saturation, abs=0.01)

    def test_black_and_white_cover_stays_neutral(self) -> None:
        image = Image.linear_gradient("L")

        palette = CoverPalette.from_image(image)

        assert palette == CoverPalette(hue_degrees=0.0, saturation=0.0)

    def test_colourful_detail_on_a_dark_cover_sets_the_hue(self) -> None:
        image = Image.new("RGB", (120, 120), (8, 8, 8))
        image.paste((250, 190, 20), (40, 40, 80, 80))

        palette = CoverPalette.from_image(image)

        assert palette.hue_degrees == pytest.approx(44.0, abs=2.0)

    def test_muted_cover_is_lifted_to_a_readable_saturation(self) -> None:
        image = Image.new("RGB", (64, 64), (150, 140, 120))

        palette = CoverPalette.from_image(image)

        assert palette.saturation == 0.65

    def test_dominant_colour_wins_over_a_smaller_area(self) -> None:
        image = Image.new("RGB", (120, 120), (30, 60, 220))
        image.paste((220, 30, 30), (0, 0, 30, 30))

        palette = CoverPalette.from_image(image)

        assert palette.hue_degrees == pytest.approx(231.0, abs=2.0)


class TestCoverPaletteForYear:
    def test_same_year_gives_the_same_palette(self) -> None:
        assert CoverPalette.for_year(1976) == CoverPalette.for_year(1976)

    def test_neighbouring_years_get_distinct_hues(self) -> None:
        first = CoverPalette.for_year(1970)
        second = CoverPalette.for_year(1971)

        assert first.hue_degrees == 70.0
        assert second.hue_degrees == 117.0

    def test_hue_stays_on_the_colour_wheel(self) -> None:
        palette = CoverPalette.for_year(2024)

        assert palette == CoverPalette(hue_degrees=88.0, saturation=0.7)
