import { svg } from "lit";
import { unsafeSVG } from "lit/directives/unsafe-svg.js";
import {
  ArrowUp,
  ArrowRight,
  Check,
  ChevronLeft,
  ChevronRight,
  Disc3,
  Download,
  Ellipsis,
  Headphones,
  HelpCircle,
  Layers,
  Menu,
  Music2,
  Mic,
  Maximize2,
  Minimize2,
  Grid2X2,
  ListMusic,
  PanelLeft,
  Plus,
  Search,
  Sparkles,
  Trash2,
  X,
  Play,
  Pause,
  SkipBack,
  SkipForward,
  Volume2,
  VolumeX,
  Paperclip,
  Settings,
  SquarePen,
  ExternalLink,
  AudioLines,
  Star,
  PanelRight,
  type IconNode,
} from "lucide";

const icons = {
  arrowUp: ArrowUp,
  arrow: ArrowRight,
  check: Check,
  left: ChevronLeft,
  right: ChevronRight,
  disc: Disc3,
  download: Download,
  more: Ellipsis,
  headphones: Headphones,
  help: HelpCircle,
  layers: Layers,
  menu: Menu,
  music: Music2,
  microphone: Mic,
  maximize: Maximize2,
  minimize: Minimize2,
  cards: Grid2X2,
  playlist: ListMusic,
  panelLeft: PanelLeft,
  plus: Plus,
  search: Search,
  sparkles: Sparkles,
  trash: Trash2,
  close: X,
  play: Play,
  pause: Pause,
  previous: SkipBack,
  next: SkipForward,
  volume: Volume2,
  mute: VolumeX,
  paperclip: Paperclip,
  settings: Settings,
  compose: SquarePen,
  external: ExternalLink,
  equalizer: AudioLines,
  star: Star,
  panelRight: PanelRight,
} satisfies Record<string, IconNode>;
export type IconName = keyof typeof icons;

// Same data-to-SVG adapter as the reference. Only bundled Lucide data is accepted.
const markup = Object.fromEntries(
  Object.entries(icons).map(([name, node]) => [
    name,
    node
      .map(
        ([tag, attrs]) =>
          `<${tag} ${Object.entries(attrs)
            .map(([key, value]) => `${key}="${value}"`)
            .join(" ")}/>`,
      )
      .join(""),
  ]),
) as Record<IconName, string>;
/** Pass `filled` for solid transport glyphs such as play and pause. */
export function icon(name: IconName, size = 20, filled = false) {
  return svg`<svg width=${size} height=${size} viewBox="0 0 24 24" fill=${filled ? "currentColor" : "none"} stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${unsafeSVG(markup[name])}</svg>`;
}
