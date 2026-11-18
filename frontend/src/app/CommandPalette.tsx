import { Moon, Sun } from 'lucide-react'
import { useNavigate } from 'react-router'
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import { SEGMENT_LABEL, zoneLabel } from '@/lib/format'
import { useCustomers } from '@/lib/queries'
import { useTheme } from '@/lib/theme'
import { NAV } from './nav'

export function CommandPalette({
  open,
  onOpenChange,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const navigate = useNavigate()
  const customers = useCustomers()
  const { theme, toggle } = useTheme()

  const go = (to: string) => {
    onOpenChange(false)
    navigate(to)
  }

  return (
    <CommandDialog
      open={open}
      onOpenChange={onOpenChange}
      title="Search"
      description="Jump to a page or find a customer by name or ID"
    >
      <CommandInput placeholder="Search customers or pages…" />
      <CommandList>
        <CommandEmpty>No customer or page matches that search.</CommandEmpty>
        <CommandGroup heading="Pages">
          {NAV.map((item) => (
            <CommandItem key={item.to} value={`page ${item.label}`} onSelect={() => go(item.to)}>
              <item.icon />
              {item.label}
              <span className="ml-auto truncate text-xs text-ink-faint">{item.description}</span>
            </CommandItem>
          ))}
          <CommandItem
            value="toggle theme dark light"
            onSelect={() => {
              toggle()
              onOpenChange(false)
            }}
          >
            {theme === 'dark' ? <Sun /> : <Moon />}
            Switch to {theme === 'dark' ? 'light' : 'dark'} mode
          </CommandItem>
        </CommandGroup>
        <CommandGroup heading="Customers">
          {customers.data?.map((c) => (
            <CommandItem
              key={c.id}
              value={`${c.name} #${c.id}`}
              onSelect={() => go(`/customers?id=${c.id}`)}
            >
              <span className="w-10 num text-xs text-ink-faint">#{c.id}</span>
              {c.name}
              <span className="ml-auto text-xs text-ink-faint">
                {SEGMENT_LABEL[c.segment]}, {zoneLabel(c.timezone)}
              </span>
            </CommandItem>
          ))}
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  )
}
