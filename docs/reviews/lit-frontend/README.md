# Lit frontend: review gallery

Recorded on 2026-10-04 from application commit `e92000a` in Chrome. Desktop:
1440 × 960; mobile: 390 × 844. The screenshots and videos use controlled HTTP
and WebSocket fixtures plus a simulated browser speech-recognition service.
They demonstrate layout, navigation, dictation controls and interactions;
they do not demonstrate live AI, OAuth, Spotify playback, real microphone
recognition or actual exports.
The production application uses the real backend.

## Walkthroughs

| View    | Video                                      | Covered interactions                                                                                                                |
| ------- | ------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------- |
| Desktop | [MP4 walkthrough](desktop-walkthrough.mp4) | Studio, dictation preview/accept, prompt starter, chat, workspace, cards, QR side, expansion, export, library, settings, DE/EN language switch |
| Mobile  | [MP4 walkthrough](mobile-walkthrough.mp4)  | Studio, dictation preview/discard, sidebar, existing session, chat, deck, cards, QR side, return to chat, DE/EN language switch |

### Desktop preview

![Desktop walkthrough](desktop-preview.gif)

### Mobile preview

![Mobile walkthrough](mobile-preview.gif)

## Screenshots

| Desktop                                                | Mobile                              |
| ------------------------------------------------------ | ----------------------------------- |
| [01 · Login](01-login-desktop.png)                     | [08 · Studio](08-studio-mobile.png) |
| [02 · Studio](02-studio-desktop.png)                   | [09 · Chat](09-chat-mobile.png)     |
| [03 · Chat and playlist](03-chat-playlist-desktop.png) | [10 · Cards](10-cards-mobile.png)   |
| [04 · Cards](04-cards-desktop.png)                     |                                     |
| [05 · Export options](05-export-desktop.png)           |                                     |
| [06 · Library](06-library-desktop.png)                 |                                     |
| [07 · Settings](07-settings-desktop.png)               |                                     |

### Workspace and voice input

- [11 · QR side of the cards](11-qr-desktop.png)
- [12 · Expanded workspace](12-workspace-expanded.png)
- [13 · Desktop dictation preview](13-dictation-desktop.png)
- [14 · Mobile dictation preview](14-dictation-mobile.png)

### English and refreshed branding

- [15 · English studio](15-studio-desktop-en.png)
- [16 · English card workspace](16-cards-desktop-en.png)
- [17 · English mobile chat](17-chat-mobile-en.png)

The 17 screenshots include the full-height workspace with keyboard-accessible
tabs, compact composer, card monogram and both card faces. Header divider lines,
the composer reference button and the game-rules entry have been removed.
Deck captions and the text button for closing the deck are also removed;
workspace actions use icons with hover labels and keyboard-shortcut hints.
The composer shows the concrete model label and OpenAI mark from the reference.
The fixtures use representative backend registry entries instead of a generic
"Standard" option: GPT 6 Luna is the default, and the desktop walkthrough selects
GPT 6 Sol. Codex variants remain distinguishable by their model labels.
Language selection is available exclusively in settings. Visiting settings
preserves the chat draft and selected deck tab, while stopping active dictation.
The language switch updates the interface while preserving the fixture's
original German conversation and deck name. Card colors and proportions follow
the existing PDF template; its precise print font and crop marks remain in the
generated PDF. The browser preview uses an available serif font.

![Desktop studio](02-studio-desktop.png)

![Desktop cards](04-cards-desktop.png)

![English studio](15-studio-desktop-en.png)

## Reproduce

From `frontend`, run `npm ci`, then start Vite in one terminal:

```sh
npm run dev -- --port 5175 --strictPort
```

In a second terminal, run `npm run review:capture`. `REVIEW_BASE_URL` can override
the default URL. Windows uses installed Chrome; other platforms need
`npx playwright install chromium` first. The capture script shares the browser
test fixtures, waits for fonts, checks page errors and mobile overflow, and saves
screenshots here and raw WebM recordings in `frontend/test-results/review-raw`.

With FFmpeg installed, run these commands from the repository root to produce
the portable H.264 videos and inline GIF previews:

```sh
ffmpeg -y -ss 0.5 -i frontend/test-results/review-raw/desktop.webm -c:v libx264 -preset slow -crf 25 -pix_fmt yuv420p -movflags +faststart -an docs/reviews/lit-frontend/desktop-walkthrough.mp4
ffmpeg -y -ss 0.5 -i frontend/test-results/review-raw/desktop.webm -filter_complex "fps=10,scale=960:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=96[p];[b][p]paletteuse=dither=bayer:bayer_scale=3" -loop 0 docs/reviews/lit-frontend/desktop-preview.gif
ffmpeg -y -ss 0.5 -i frontend/test-results/review-raw/mobile.webm -c:v libx264 -preset slow -crf 24 -pix_fmt yuv420p -movflags +faststart -an docs/reviews/lit-frontend/mobile-walkthrough.mp4
ffmpeg -y -ss 0.5 -i frontend/test-results/review-raw/mobile.webm -filter_complex "fps=10,split[a][b];[a]palettegen=max_colors=96[p];[b][p]paletteuse=dither=bayer:bayer_scale=3" -loop 0 docs/reviews/lit-frontend/mobile-preview.gif
```

The MP4 files retain the original viewport dimensions; the desktop GIF is
scaled to 960 pixels wide for the PR. Raw recordings are excluded from Git.
