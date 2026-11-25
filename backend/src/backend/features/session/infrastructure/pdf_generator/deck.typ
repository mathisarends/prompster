// Printable deck, "Zeitkapsel" design.
//
// QR side:     the answer side's layout before the reveal. The Spotify code sits
//              where the cover will be; artist, title and year are blanks.
//              Identical for every card, so nothing gives the song away.
// Answer side: the album cover in the medium of its era (LP, cassette, CD,
//              stream), coloured from the cover itself.
//
// Cards are drawn on a 100-unit grid (`u`). The on-screen card in
// frontend/src/features/deck/components/music-card.ts mirrors this layout.

#let songs = json(bytes(sys.inputs.at("songs")))
#let max_pages_input = sys.inputs.at("max_pages", default: "")
#let max_pages = if max_pages_input == "" { none } else { int(max_pages_input) }

#let page_width = 210mm
#let page_height = 297mm
#let margin_x = 2cm
#let margin_y = 1cm

#let rows = 5
#let cols = 3
#let card_size = 5cm
#let u = card_size / 100

#let marking_padding = 1cm

#set page(
  width: page_width,
  height: page_height,
  margin: (x: margin_x, y: margin_y),
)

#set square(stroke: none)

// Bundled in ./fonts. Only the condensed Barlow cuts ship, hence the stretch.
#let condensed = (font: "Barlow", stretch: 75%)
#let display = (font: "Archivo")
#let mono = (font: "Space Mono", weight: "bold")

// ------------------------------------------------------------------ helpers

#let card(fill, body) = box(width: card_size, height: card_size, clip: true, fill: fill, body)

#let at(x, y, body) = place(top + left, dx: x * u, dy: y * u, body)

// One line, shrunk until it fits `width`.
#let fit(body, width, size, min: 4 * u, ..args) = context {
  let natural = measure(text(size: size, ..args, body)).width
  let fitted = if natural > width { calc.max(min, size * (width / natural)) } else { size }
  text(size: fitted, ..args, body)
}

// Digits in a tight box: cap height on top, baseline at the bottom.
#let numerals(body, ..args) = text(top-edge: "cap-height", bottom-edge: "baseline", ..args, body)

// Every card colour comes from the cover's hue and saturation.
// Keep in sync with the custom properties in music-card.ts.
#let palette_of(song) = {
  let hue = song.hue * 1deg
  let saturation = song.saturation
  (
    paper: color.hsl(hue, saturation * 90%, 90%),
    ink: color.hsl(hue, saturation * 70%, 13%),
    mid: color.hsl(hue, saturation * 80%, 40%),
    accent: color.hsl(hue, calc.min(1, saturation * 1.15) * 100%, 60%),
  )
}

#let year_of(song) = if song.release_year.match(regex("^\d+$")) != none { int(song.release_year) } else { none }

#let era_of(year) = if year == none or year >= 2008 { "stream" } else if year < 1982 { "lp" } else if year < 1992 {
  "mc"
} else { "cd" }

#let era_labels = (lp: "LP · 33⅓ RPM", mc: "MC · CHROME", cd: "CD · DIGITAL AUDIO", stream: "STREAM · 320 KBPS")

// ------------------------------------------------------------------ media

#let cover(song, size, radius: 0pt, colours) = box(
  width: size,
  height: size,
  clip: true,
  radius: radius,
  fill: gradient.linear(colours.accent, colours.mid, angle: 45deg),
  if song.cover_file != none {
    image(song.cover_file, width: size, height: size, fit: "cover")
  } else {
    // No artwork: a blank sleeve with pressed rings.
    for ring in range(1, 7) {
      let radius = size * 0.22 * ring
      place(top + left, dx: size - radius, dy: size - radius, circle(
        radius: radius,
        stroke: 0.5 * u + white.transparentize(70%),
      ))
    }
  },
)

#let hard_shadow(width, height, radius: 0pt, ink) = rect(
  width: width,
  height: height,
  radius: radius,
  fill: ink.transparentize(78%),
)

#let vinyl_disc(diameter, label) = box(width: diameter, height: diameter)[
  #place(center + horizon, circle(radius: diameter / 2, fill: rgb("#141414")))
  #for groove in range(4, 12) {
    place(center + horizon, circle(
      radius: diameter / 2 * groove / 12.5,
      stroke: 0.25 * u + white.transparentize(if calc.odd(groove) { 82% } else { 90% }),
    ))
  }
  #place(center + horizon, circle(radius: diameter * 0.17, fill: label))
  #place(center + horizon, circle(radius: diameter * 0.17 - 1.2 * u, stroke: 0.25 * u + black.transparentize(60%)))
  #place(center + horizon, circle(radius: diameter * 0.022, fill: rgb("#141414")))
]

#let compact_disc(diameter) = box(width: diameter, height: diameter)[
  #place(center + horizon, circle(
    radius: diameter / 2,
    fill: gradient.conic(
      rgb("#f4f4f6"), rgb("#c9ccd4"), rgb("#ffd9f0"), rgb("#d5f3ff"), rgb("#f4f4f6"),
      rgb("#b9bcc6"), rgb("#fff4c9"), rgb("#d9ffe6"), rgb("#f4f4f6"),
      angle: 20deg,
    ),
    stroke: 0.3 * u + rgb("#9a9da8"),
  ))
  #place(center + horizon, circle(
    radius: diameter * 0.2,
    fill: rgb("#e9eaee").transparentize(35%),
    stroke: 0.25 * u + rgb("#9a9da8"),
  ))
  #place(center + horizon, circle(radius: diameter * 0.11, stroke: 0.25 * u + rgb("#9a9da8")))
  #place(center + horizon, circle(radius: diameter * 0.075, fill: rgb("#3a3a40")))
]

#let tape_reel(diameter) = box(width: diameter, height: diameter)[
  #place(center + horizon, circle(radius: diameter / 2, fill: rgb("#f3efe6")))
  #place(center + horizon, circle(radius: diameter * 0.3, fill: rgb("#1b1b1d")))
  #for tooth in range(6) {
    place(center + horizon, rotate(tooth * 60deg, rect(
      width: diameter * 0.1,
      height: diameter * 0.56,
      fill: rgb("#f3efe6"),
    )))
  }
  #place(center + horizon, circle(radius: diameter * 0.12, fill: rgb("#1b1b1d")))
]

#let cassette(width, height, accent) = box(
  width: width,
  height: height,
  clip: true,
  radius: 2.2 * u,
  fill: rgb("#26262a"),
)[
  // label with two stripes
  #place(top + left, dx: 3 * u, dy: 3 * u, rect(
    width: width - 6 * u,
    height: height * 0.62,
    radius: 1.4 * u,
    fill: rgb("#f3ead7"),
  ))
  #place(top + left, dx: 3 * u, dy: 3 * u + height * 0.62 - 7.5 * u, rect(
    width: width - 6 * u,
    height: 2.2 * u,
    fill: accent,
  ))
  #place(top + left, dx: 3 * u, dy: 3 * u + height * 0.62 - 4.6 * u, rect(
    width: width - 6 * u,
    height: 1 * u,
    fill: accent,
  ))
  // window
  #place(top + left, dx: width * 0.2, dy: height * 0.25, rect(
    width: width * 0.6,
    height: height * 0.27,
    radius: 1.6 * u,
    fill: rgb("#101012"),
  ))
  #place(top + left, dx: width * 0.26, dy: height * 0.275, tape_reel(height * 0.22))
  #place(top + left, dx: width * 0.74 - height * 0.22, dy: height * 0.275, tape_reel(height * 0.22))
  // head opening
  #place(bottom + center, polygon(
    fill: rgb("#19191c"),
    (0pt, height * 0.24),
    (width * 0.09, 0pt),
    (width * 0.55, 0pt),
    (width * 0.64, height * 0.24),
  ))
  #for offset in (-0.12, 0.12) {
    place(bottom + center, dx: offset * width, dy: -height * 0.07, circle(
      radius: 1.3 * u,
      fill: rgb("#f3ead7").transparentize(30%),
    ))
  }
]

// Deterministic "equaliser" so the same song always draws the same bars.
#let equaliser(seed, colours) = {
  let levels = (0.45, 0.8, 0.6, 1, 0.7, 0.35, 0.9, 0.55)
  for (bar, level) in levels.enumerate() {
    let wobble = calc.abs(calc.sin((bar * 37 + seed * 13) * 1deg))
    let height = 26 * u * (wobble * 0.6 + level * 0.4)
    place(top + left, dx: (65 + bar * 3.4) * u, dy: 38 * u - height, rect(
      width: 2.1 * u,
      height: height,
      radius: 1 * u,
      fill: if bar == 3 { colours.accent } else { colours.ink },
    ))
  }
  at(65, 43, rect(width: 26.5 * u, height: 0.8 * u, radius: 0.4 * u, fill: colours.ink.transparentize(75%)))
  at(65, 43, rect(width: 11 * u, height: 0.8 * u, radius: 0.4 * u, fill: colours.ink))
  at(75.2, 42.1, circle(radius: 1.3 * u, fill: colours.ink))
}

// ------------------------------------------------------------------ sides

#let cover_edge = 47

#let era_scene(song, era, seed, colours) = {
  let edge = cover_edge * u
  let outline = 0.3 * u + colours.ink.transparentize(50%)
  if era == "lp" {
    at(47, 8.5, vinyl_disc(44 * u, colours.accent))
    at(13.2, 8.2, hard_shadow(edge, edge, colours.ink))
    at(12, 7, cover(song, edge, colours))
    at(12, 7, rect(width: edge, height: edge, stroke: outline))
  } else if era == "mc" {
    at(40, 14, cassette(50 * u, 33 * u, colours.accent))
    at(13.2, 8.2, hard_shadow(edge, edge, radius: 1.5 * u, colours.ink))
    at(12, 7, cover(song, edge, radius: 1.5 * u, colours))
    // case spine
    at(12, 7, box(width: 4.2 * u, height: edge, radius: (left: 1.5 * u), fill: white.transparentize(45%)))
    at(12, 7, rect(width: edge, height: edge, radius: 1.5 * u, stroke: outline))
  } else if era == "cd" {
    at(46, 8.5, compact_disc(44 * u))
    at(13.2, 8.2, hard_shadow(edge + 5 * u, edge, radius: 0.8 * u, colours.ink))
    // jewel case with hinge
    at(12, 7, rect(width: edge + 5 * u, height: edge, radius: 0.8 * u, fill: rgb("#dfe1e6")))
    for notch in range(6) {
      at(13.4, 9.5 + notch * 8, rect(width: 2.2 * u, height: 3 * u, radius: 0.4 * u, fill: rgb("#a9acb6")))
    }
    at(17, 7, cover(song, edge, radius: (right: 0.8 * u), colours))
    at(12, 7, rect(width: edge + 5 * u, height: edge, radius: 0.8 * u, stroke: outline))
  } else {
    at(13.2, 8.2, hard_shadow(edge, edge, radius: 5 * u, colours.ink))
    at(12, 7, cover(song, edge, radius: 5 * u, colours))
    equaliser(seed, colours)
  }
}

#let answer_side(song, index) = {
  let colours = palette_of(song)
  let year = year_of(song)
  let era = era_of(year)
  card(colours.paper)[
    // soft sun behind the medium
    #at(-20, -30, circle(radius: 62 * u, fill: white.transparentize(55%)))
    #era_scene(song, era, if year == none { index } else { year }, colours)

    #at(12, 59.5, fit(
      upper(song.artist_names),
      76 * u,
      6.2 * u,
      ..condensed,
      weight: "bold",
      fill: colours.ink,
      tracking: 0.05em,
    ))
    #at(12, 66.3, fit(
      song.title,
      76 * u,
      6.2 * u,
      ..condensed,
      weight: "medium",
      style: "italic",
      fill: colours.mid,
    ))

    #place(bottom + left, dx: 11.2 * u, dy: -7.5 * u, numerals(
      song.release_year,
      ..display,
      size: 22 * u,
      fill: colours.ink,
      tracking: -0.02em,
    ))
    #place(bottom + right, dx: -8 * u, dy: -7.5 * u, rotate(-90deg, reflow: true, box(
      inset: (x: 1.6 * u, y: 1.1 * u),
      radius: 0.8 * u,
      stroke: 0.3 * u + colours.ink,
      text(..mono, size: 2.5 * u, fill: colours.ink, era_labels.at(era)),
    )))
  ]
}

// Same for every card, and never coloured from the cover.
#let back_paper = rgb("#f4ecdc")
#let back_ink = rgb("#1b1820")
#let back_accent = rgb("#ff5a3c")

#let qr_edge = 56

#let qr_side(song) = card(back_paper)[
  #at(-20, -30, circle(radius: 62 * u, fill: white.transparentize(45%)))
  #at(50, 11, box(width: 46 * u, height: 46 * u)[
    #vinyl_disc(46 * u, back_accent)
    #place(center + horizon, dy: 0.3 * u, text(..display, size: 8 * u, fill: back_paper)[?])
  ])

  // the code sits where the cover will be
  #at(11.2, 8.2, hard_shadow(qr_edge * u, qr_edge * u, back_ink))
  #at(10, 7, box(width: qr_edge * u, height: qr_edge * u, fill: white, image(song.qr_file, width: 100%)))
  #at(10, 7, rect(width: qr_edge * u, height: qr_edge * u, stroke: 0.3 * u + back_ink.transparentize(50%)))

  // artist, title and year: not revealed yet
  #at(10, 67.4, rect(width: 40 * u, height: 3.2 * u, radius: 1.6 * u, fill: back_ink.transparentize(78%)))
  #at(10, 72.6, rect(width: 27 * u, height: 3.2 * u, radius: 1.6 * u, fill: back_ink.transparentize(88%)))
  #place(bottom + left, dx: 9.4 * u, dy: -7 * u, numerals(
    "????",
    ..display,
    size: 17 * u,
    fill: back_ink.transparentize(80%),
    tracking: 0.03em,
  ))
  #place(bottom + right, dx: -8 * u, dy: -7 * u, rotate(-90deg, reflow: true, box(
    inset: (x: 1.6 * u, y: 1.1 * u),
    radius: 0.8 * u,
    fill: back_ink,
    text(..mono, size: 2.5 * u, fill: back_paper)[SCAN · LISTEN · GUESS],
  )))
]

// ------------------------------------------------------------------ sheets

#let marking_line = line(
  stroke: (paint: rgb("#8a8a8a"), thickness: 0.5pt),
  length: marking_padding / 2,
)

#let marking(angle) = {
  rotate(
    angle,
    reflow: true,
    box(
      width: marking_padding,
      height: card_size,
      stack(
        spacing: card_size,
        ..(marking_line,) * 2,
      ),
    ),
  )
}

#let marking_row(angle) = {
  (
    square(size: marking_padding),
    ..(marking(angle),) * cols,
    square(size: marking_padding),
  )
}

#let pad_page(page) = {
  let page_rows = page.chunks(cols)
  let padded_rows = page_rows.map(row => (marking(0deg), ..row, marking(180deg)))
  return (
    ..marking_row(90deg),
    ..padded_rows.flatten(),
    ..marking_row(270deg),
  )
}

#let get_pages(songs) = {
  let pages = ()

  let index = 0
  for page in songs.chunks(rows * cols) {
    let qr_sides = ()
    let answer_sides = ()

    for song in page {
      qr_sides.push(qr_side(song))
      answer_sides.push(answer_side(song, index))
      index += 1
    }

    for _ in range(rows * cols - page.len()) {
      qr_sides.push(square(size: card_size))
      answer_sides.push(square(size: card_size))
    }

    // Mirror each row so both sides line up after duplex printing.
    let mirrored_answers = answer_sides.chunks(cols).map(row => row.rev()).flatten()

    pages.push(pad_page(qr_sides))
    pages.push(pad_page(mirrored_answers))
  }

  return pages
}

#let pages = get_pages(songs)
#let visible_pages = if max_pages == none { pages } else { pages.slice(0, calc.min(max_pages, pages.len())) }

#for (i, page) in visible_pages.enumerate() {
  if i != 0 { pagebreak() }
  grid(
    columns: cols + 2,
    ..page
  )
}
