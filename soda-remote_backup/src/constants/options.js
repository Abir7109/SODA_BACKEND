import { COLORS } from './colors'

export const DIAMOND_OPTIONS = [
  {
    id: 'capture',
    label: 'CAPTURE',
    icon: 'camera',
    color: COLORS.nodeColors.capture,
    screen: 'Capture',
  },
  {
    id: 'mouse',
    label: 'MOUSE',
    icon: 'mouse-pointer',
    color: COLORS.nodeColors.mouse,
    screen: 'Touchpad',
  },
  {
    id: 'keyboard',
    label: 'TYPE',
    icon: 'type',
    color: COLORS.nodeColors.keyboard,
    screen: 'Keyboard',
  },
  {
    id: 'volume',
    label: 'VOLUME',
    icon: 'volume-2',
    color: COLORS.nodeColors.volume,
    screen: 'Volume',
  },
  {
    id: 'brightness',
    label: 'BRIGHT',
    icon: 'sun',
    color: COLORS.nodeColors.brightness,
    screen: 'Brightness',
  },
  {
    id: 'files',
    label: 'FILES',
    icon: 'folder',
    color: COLORS.nodeColors.files,
    screen: 'Files',
  },
  {
    id: 'terminal',
    label: 'TERMINAL',
    icon: 'terminal',
    color: COLORS.nodeColors.terminal,
    screen: 'Terminal',
  },
  {
    id: 'apps',
    label: 'APPS',
    icon: 'grid',
    color: COLORS.nodeColors.apps,
    screen: 'Apps',
  },
]

export const SCREEN_MAP = {}
for (const opt of DIAMOND_OPTIONS) {
  SCREEN_MAP[opt.screen] = opt.id
}
