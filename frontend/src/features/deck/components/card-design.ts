/**
 * Design rules shared by every music card. A card's colours come from one hue
 * and saturation taken from its album cover, and its medium from the release
 * year. The printable deck applies the same rules in the backend's
 * pdf_generator (cover_palette.py and deck.typ), so screen and print match.
 */
export type CoverPalette = { hue: number; saturation: number };

export type Era = "lp" | "mc" | "cd" | "stream";

export const eraLabels: Record<Era, string> = {
  lp: "LP · 33⅓ RPM",
  mc: "MC · CHROME",
  cd: "CD · DIGITAL AUDIO",
  stream: "STREAM · 320 KBPS",
};

export function eraOf(year: number): Era {
  if (year < 1982) {
    return "lp";
  }
  if (year < 1992) {
    return "mc";
  }
  return year < 2008 ? "cd" : "stream";
}

const SAMPLE_EDGE = 24;
const HUE_BINS = 12;
const CHROMA_WEIGHT_EXPONENT = 1.5;
const MIN_COLOURFUL_WEIGHT = 0.0008;
const MIN_SATURATION = 0.65;
const MAX_SATURATION = 0.85;
const FALLBACK_SATURATION = 0.7;
const FALLBACK_HUE_STEP = 47;
const NEUTRAL: CoverPalette = { hue: 0, saturation: 0 };

/** Stand-in for cards without a usable cover, stable per release year. */
export function paletteForYear(year: number): CoverPalette {
  return { hue: (year * FALLBACK_HUE_STEP) % 360, saturation: FALLBACK_SATURATION };
}

/** Dominant colourful hue of RGBA pixel data; black-and-white covers stay neutral. */
export function paletteFromPixels(rgba: ArrayLike<number>): CoverPalette {
  const bins = Array.from({ length: HUE_BINS }, () => ({
    weight: 0,
    saturation: 0,
    sin: 0,
    cos: 0,
  }));
  for (let offset = 0; offset < rgba.length; offset += 4) {
    const red = rgba[offset] / 255;
    const green = rgba[offset + 1] / 255;
    const blue = rgba[offset + 2] / 255;
    const max = Math.max(red, green, blue);
    const min = Math.min(red, green, blue);
    const chroma = max - min;
    if (chroma === 0) {
      continue;
    }
    const sector =
      max === red
        ? ((green - blue) / chroma + 6) % 6
        : max === green
          ? (blue - red) / chroma + 2
          : (red - green) / chroma + 4;
    const hue = sector / 6;
    const lightness = (max + min) / 2;
    const saturation = chroma / (lightness <= 0.5 ? max + min : 2 - max - min);
    const weight = chroma ** CHROMA_WEIGHT_EXPONENT;
    // Bins are centred on the primaries, so reds around 0° share one bin.
    const bin = bins[Math.floor(hue * HUE_BINS + 0.5) % HUE_BINS];
    bin.weight += weight;
    bin.saturation += saturation * weight;
    bin.sin += Math.sin(hue * 2 * Math.PI) * weight;
    bin.cos += Math.cos(hue * 2 * Math.PI) * weight;
  }
  const dominant = bins.reduce((best, bin) => (bin.weight > best.weight ? bin : best));
  if (dominant.weight / (rgba.length / 4) < MIN_COLOURFUL_WEIGHT) {
    return NEUTRAL;
  }
  const degrees = (Math.atan2(dominant.sin, dominant.cos) * 180) / Math.PI;
  return {
    hue: (degrees + 360) % 360,
    saturation: Math.min(
      MAX_SATURATION,
      Math.max(MIN_SATURATION, dominant.saturation / dominant.weight),
    ),
  };
}

/** Reads a loaded cover; null when the browser refuses pixel access (no CORS). */
export function paletteFromImage(image: HTMLImageElement): CoverPalette | null {
  const canvas = document.createElement("canvas");
  canvas.width = SAMPLE_EDGE;
  canvas.height = SAMPLE_EDGE;
  const context = canvas.getContext("2d", { willReadFrequently: true });
  if (!context) {
    return null;
  }
  context.imageSmoothingQuality = "high";
  try {
    context.drawImage(image, 0, 0, SAMPLE_EDGE, SAMPLE_EDGE);
    return paletteFromPixels(context.getImageData(0, 0, SAMPLE_EDGE, SAMPLE_EDGE).data);
  } catch {
    return null;
  }
}
