import colorsys
import math
from dataclasses import dataclass

from PIL import Image

_SAMPLE_EDGE_PIXELS = 24
_HUE_BIN_COUNT = 12
_CHROMA_WEIGHT_EXPONENT = 1.5
_MIN_COLOURFUL_WEIGHT = 0.0008
_MIN_SATURATION = 0.65
_MAX_SATURATION = 0.85
_FALLBACK_SATURATION = 0.7
_FALLBACK_HUE_STEP_DEGREES = 47


@dataclass(frozen=True, slots=True)
class CoverPalette:
    """One hue and saturation; deck.typ derives every card colour from them.

    The frontend runs the same extraction in cover-palette.ts, so a card looks
    the same on screen and in print.
    """

    hue_degrees: float
    saturation: float

    @classmethod
    def from_image(cls, image: Image.Image) -> "CoverPalette":
        rgb_image = image.convert("RGB")
        sample = rgb_image.resize(
            (_SAMPLE_EDGE_PIXELS, _SAMPLE_EDGE_PIXELS), Image.Resampling.BILINEAR
        )
        bins = [_HueBin() for _ in range(_HUE_BIN_COUNT)]
        pixels = sample.tobytes()
        for offset in range(0, len(pixels), 3):
            red, green, blue = pixels[offset : offset + 3]
            hue, _, saturation = colorsys.rgb_to_hls(red / 255, green / 255, blue / 255)
            chroma = (max(red, green, blue) - min(red, green, blue)) / 255
            weight = chroma**_CHROMA_WEIGHT_EXPONENT
            # Bins are centred on the primaries, so reds around 0° share one bin.
            index = int(hue * _HUE_BIN_COUNT + 0.5) % _HUE_BIN_COUNT
            bins[index].add(hue=hue, saturation=saturation, weight=weight)

        dominant = max(bins, key=lambda hue_bin: hue_bin.weight)
        pixel_count = _SAMPLE_EDGE_PIXELS * _SAMPLE_EDGE_PIXELS
        if dominant.weight / pixel_count < _MIN_COLOURFUL_WEIGHT:
            # Black-and-white covers keep a neutral card instead of a random tint.
            return cls(hue_degrees=0.0, saturation=0.0)
        saturation = min(_MAX_SATURATION, max(_MIN_SATURATION, dominant.saturation))
        return cls(hue_degrees=dominant.hue_degrees, saturation=saturation)

    @classmethod
    def for_year(cls, year: int) -> "CoverPalette":
        """Stand-in for tracks without a usable cover, stable per release year."""
        hue_degrees = float(year * _FALLBACK_HUE_STEP_DEGREES % 360)
        return cls(hue_degrees=hue_degrees, saturation=_FALLBACK_SATURATION)


class _HueBin:
    def __init__(self) -> None:
        self._weight = 0.0
        self._weighted_saturation = 0.0
        self._weighted_sin = 0.0
        self._weighted_cos = 0.0

    def add(self, *, hue: float, saturation: float, weight: float) -> None:
        angle = hue * math.tau
        self._weight += weight
        self._weighted_saturation += saturation * weight
        self._weighted_sin += math.sin(angle) * weight
        self._weighted_cos += math.cos(angle) * weight

    @property
    def weight(self) -> float:
        return self._weight

    @property
    def saturation(self) -> float:
        return self._weighted_saturation / self._weight

    @property
    def hue_degrees(self) -> float:
        angle = math.atan2(self._weighted_sin, self._weighted_cos)
        return math.degrees(angle) % 360
