import {
  Info,
  LayoutDashboard,
  RadioTower,
  ScrollText,
  SlidersHorizontal,
  Users,
  type LucideIcon,
} from 'lucide-react'

export interface NavItem {
  to: string
  label: string
  icon: LucideIcon
  description: string
}

export const NAV: NavItem[] = [
  {
    to: '/',
    label: 'Overview',
    icon: LayoutDashboard,
    description: 'Headline results versus no controller',
  },
  {
    to: '/tower',
    label: 'Live Tower',
    icon: RadioTower,
    description: 'Replay 30 days of decisions',
  },
  {
    to: '/rules',
    label: 'Rules Lab',
    icon: SlidersHorizontal,
    description: 'Tune rules and rerun the simulation',
  },
  {
    to: '/customers',
    label: 'Customers',
    icon: Users,
    description: 'What each customer actually received',
  },
  { to: '/log', label: 'Alert Log', icon: ScrollText, description: 'Every decision, filterable' },
  { to: '/about', label: 'About', icon: Info, description: 'Why this exists and how it works' },
]
