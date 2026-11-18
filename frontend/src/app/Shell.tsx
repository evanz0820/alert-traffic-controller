import { Menu, Moon, Search, Sun } from 'lucide-react'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { useState } from 'react'
import { NavLink, useLocation, useOutlet } from 'react-router'
import { Wordmark } from '@/components/brand/Logo'
import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetDescription, SheetTitle } from '@/components/ui/sheet'
import { useTheme } from '@/lib/theme'
import { cn } from '@/lib/utils'
import { useCommandPalette } from '@/hooks/useCommandPalette'
import { CommandPalette } from './CommandPalette'
import { NAV } from './nav'
import { RunPicker } from './RunPicker'

function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <nav aria-label="Main" className="flex flex-col gap-0.5">
      {NAV.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          end={to === '/'}
          onClick={onNavigate}
          className={({ isActive }) =>
            cn(
              'group relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors',
              isActive
                ? 'bg-console font-medium text-ink'
                : 'text-ink-muted hover:bg-console/60 hover:text-ink',
            )
          }
        >
          {({ isActive }) => (
            <>
              <span
                aria-hidden="true"
                className={cn(
                  'absolute top-2 bottom-2 left-0 w-0.5 rounded-full bg-sent transition-opacity',
                  isActive ? 'opacity-100' : 'opacity-0',
                )}
              />
              <Icon className="size-4" />
              {label}
            </>
          )}
        </NavLink>
      ))}
    </nav>
  )
}

function ThemeButton({ className }: { className?: string }) {
  const { theme, toggle } = useTheme()
  const next = theme === 'dark' ? 'light' : 'dark'
  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={toggle}
      aria-label={`Switch to ${next} mode`}
      className={className}
    >
      {theme === 'dark' ? <Sun /> : <Moon />}
    </Button>
  )
}

function SearchButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex w-full items-center gap-2 rounded-lg border border-rim bg-console px-3 py-2 text-sm text-ink-faint transition-colors hover:text-ink"
    >
      <Search className="size-4" />
      Find a customer
      <kbd className="ml-auto rounded border border-rim px-1.5 font-sans text-[11px]">⌘K</kbd>
    </button>
  )
}

export function Shell() {
  const location = useLocation()
  const outlet = useOutlet()
  const reduce = useReducedMotion()
  const palette = useCommandPalette()
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <div className="min-h-dvh bg-night">
      <a
        href="#main"
        className="sr-only z-50 rounded-md bg-deck px-3 py-2 focus:not-sr-only focus:fixed focus:top-3 focus:left-3"
      >
        Skip to content
      </a>

      <aside className="fixed inset-y-0 left-0 z-30 hidden w-[232px] flex-col border-r border-rim bg-deck px-4 py-5 lg:flex">
        <Wordmark className="px-2" />
        <div className="mt-8">
          <NavLinks />
        </div>
        <div className="mt-auto space-y-4">
          <SearchButton onClick={() => palette.setOpen(true)} />
          <RunPicker />
          <div className="flex items-center justify-between border-t border-rim pt-4 text-xs text-ink-faint">
            <span>Synthetic data, seed 42</span>
            <ThemeButton className="-mr-2" />
          </div>
        </div>
      </aside>

      <header className="sticky top-0 z-30 flex h-14 items-center gap-2 border-b border-rim bg-deck/90 px-4 backdrop-blur lg:hidden">
        <Wordmark />
        <div className="ml-auto flex items-center">
          <Button
            variant="ghost"
            size="icon"
            aria-label="Find a customer"
            onClick={() => palette.setOpen(true)}
          >
            <Search />
          </Button>
          <ThemeButton />
          <Button
            variant="ghost"
            size="icon"
            aria-label="Open menu"
            onClick={() => setMenuOpen(true)}
          >
            <Menu />
          </Button>
        </div>
      </header>

      <Sheet open={menuOpen} onOpenChange={setMenuOpen}>
        <SheetContent side="left" className="w-[280px] gap-0 border-rim bg-deck p-4">
          <SheetTitle className="sr-only">Navigation</SheetTitle>
          <SheetDescription className="sr-only">Pages in the ATC dashboard</SheetDescription>
          <Wordmark className="px-2 pt-1" />
          <div className="mt-8">
            <NavLinks onNavigate={() => setMenuOpen(false)} />
          </div>
          <div className="mt-8">
            <RunPicker />
          </div>
        </SheetContent>
      </Sheet>

      <main id="main" className="lg:pl-[232px]">
        <div className="mx-auto w-full max-w-[1280px] px-4 py-8 sm:px-6 lg:px-10 lg:py-10">
          <AnimatePresence mode="wait" initial={false}>
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, y: reduce ? 0 : 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.18, ease: 'easeOut' }}
            >
              {outlet}
            </motion.div>
          </AnimatePresence>
        </div>
      </main>

      <CommandPalette open={palette.open} onOpenChange={palette.setOpen} />
    </div>
  )
}
