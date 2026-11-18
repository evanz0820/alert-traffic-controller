import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState, type ReactNode } from 'react'
import { TooltipProvider } from '@/components/ui/tooltip'
import { RunProvider } from '@/lib/run-context'
import { ThemeProvider } from '@/lib/theme'

export function Providers({ children }: { children: ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
      }),
  )
  return (
    <QueryClientProvider client={client}>
      <ThemeProvider>
        <RunProvider>
          <TooltipProvider delayDuration={150}>{children}</TooltipProvider>
        </RunProvider>
      </ThemeProvider>
    </QueryClientProvider>
  )
}
