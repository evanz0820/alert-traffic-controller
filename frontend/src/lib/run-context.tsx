import { useQuery } from '@tanstack/react-query'
import { createContext, useContext, useState, type ReactNode } from 'react'
import { api } from './api'

interface RunState {
  /** Selected ATC run; falls back to the most recent one. */
  runId: string | undefined
  setRunId: (id: string) => void
}

const RunContext = createContext<RunState | null>(null)

export function RunProvider({ children }: { children: ReactNode }) {
  const [selected, setSelected] = useState<string>()
  const runs = useQuery({ queryKey: ['runs'], queryFn: () => api.runs(20) })
  const runId = selected ?? runs.data?.[0]?.id
  return (
    <RunContext.Provider value={{ runId, setRunId: setSelected }}>{children}</RunContext.Provider>
  )
}

export function useRun() {
  const ctx = useContext(RunContext)
  if (!ctx) throw new Error('useRun must be used inside <RunProvider>')
  return ctx
}
