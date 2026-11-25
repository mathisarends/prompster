import { test } from "node:test";
import assert from "node:assert/strict";
import {
  eraOf,
  paletteForYear,
  paletteFromPixels,
} from "../src/features/deck/components/card-design.ts";

type Rgb = [number, number, number];

/** RGBA pixel data of a square cover with an optional patch in another colour. */
function cover(edge: number, colour: Rgb, patch?: { colour: Rgb; edge: number }): number[] {
  const pixels: number[] = [];
  for (let y = 0; y < edge; y++) {
    for (let x = 0; x < edge; x++) {
      const inPatch = patch !== undefined && x < patch.edge && y < patch.edge;
      pixels.push(...(inPatch ? patch.colour : colour), 255);
    }
  }
  return pixels;
}

function assertClose(actual: number, expected: number, tolerance: number): void {
  assert.ok(
    Math.abs(actual - expected) <= tolerance,
    `${actual} is not within ${tolerance} of ${expected}`,
  );
}

// The expected values match backend test_cover_palette.py: both sides must agree.
const solidCovers: { colour: Rgb; hue: number; saturation: number }[] = [
  { colour: [220, 30, 30], hue: 0, saturation: 0.76 },
  { colour: [30, 200, 60], hue: 131, saturation: 0.74 },
  { colour: [30, 60, 220], hue: 231, saturation: 0.76 },
];
for (const { colour, hue, saturation } of solidCovers) {
  test(`solid cover rgb(${colour}) keeps its hue and saturation`, () => {
    const palette = paletteFromPixels(cover(24, colour));
    assertClose(palette.hue, hue, 1);
    assertClose(palette.saturation, saturation, 0.01);
  });
}

test("black-and-white cover stays neutral", () => {
  const greys = Array.from({ length: 24 * 24 }, (_, i) => [i % 256, i % 256, i % 256, 255]).flat();
  assert.deepEqual(paletteFromPixels(greys), { hue: 0, saturation: 0 });
});

test("colourful detail on a dark cover sets the hue", () => {
  const palette = paletteFromPixels(cover(24, [8, 8, 8], { colour: [250, 190, 20], edge: 8 }));
  assertClose(palette.hue, 44, 2);
});

test("muted cover is lifted to a readable saturation", () => {
  assert.equal(paletteFromPixels(cover(24, [150, 140, 120])).saturation, 0.65);
});

test("dominant colour wins over a smaller area", () => {
  const palette = paletteFromPixels(cover(24, [30, 60, 220], { colour: [220, 30, 30], edge: 6 }));
  assertClose(palette.hue, 231, 2);
});

test("cards without a cover get a stable hue per release year", () => {
  assert.deepEqual(paletteForYear(1970), { hue: 70, saturation: 0.7 });
  assert.deepEqual(paletteForYear(1971), { hue: 117, saturation: 0.7 });
  assert.deepEqual(paletteForYear(2024), { hue: 88, saturation: 0.7 });
});

test("release year picks the medium of its era", () => {
  assert.deepEqual([1969, 1981, 1982, 1991, 1992, 2007, 2008, 2024].map(eraOf), [
    "lp",
    "lp",
    "mc",
    "mc",
    "cd",
    "cd",
    "stream",
    "stream",
  ]);
});
