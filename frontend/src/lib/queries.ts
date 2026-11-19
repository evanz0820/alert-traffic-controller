import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { api } from './api'
import { useRun } from './run-context'
import type { AlertFilters } from './types'

export function useRuns() {
  return useQuery({ queryKey: ['runs'], queryFn: () => api.runs(20) })
}

export function useSummary(runId?: string) {
  const current = useRun().runId
  const id = runId ?? current
  return useQuery({
    queryKey: ['summary', id],
    queryFn: () => api.summary(id!),
    enabled: !!id,
    staleTime: Infinity,
  })
}

export function useFlows() {
  const { runId } = useRun()
  return useQuery({
    queryKey: ['flows', runId],
    queryFn: () => api.flows(runId!),
    enabled: !!runId,
    staleTime: Infinity,
  })
}

export function useTimeseries() {
  const { runId } = useRun()
  return useQuery({
    queryKey: ['timeseries', runId],
    queryFn: () => api.timeseries(runId!),
    enabled: !!runId,
    staleTime: Infinity,
  })
}

export function useReplay() {
  const { runId } = useRun()
  return useQuery({
    queryKey: ['replay', runId],
    queryFn: () => api.replay(runId!),
    enabled: !!runId,
    staleTime: Infinity,
  })
}

export function useAlerts(filters: AlertFilters, page: number, pageSize: number, sort: string) {
  const { runId } = useRun()
  return useQuery({
    queryKey: ['alerts', runId, filters, page, pageSize, sort],
    queryFn: () => api.alerts(runId!, filters, page, pageSize, sort),
    enabled: !!runId,
    placeholderData: keepPreviousData,
  })
}

export function useCustomers() {
  const { runId } = useRun()
  return useQuery({
    queryKey: ['customers', runId],
    queryFn: () => api.customers(runId!),
    enabled: !!runId,
    staleTime: Infinity,
  })
}

export function useCustomer(id: number | null) {
  const { runId } = useRun()
  return useQuery({
    queryKey: ['customer', runId, id],
    queryFn: () => api.customer(runId!, id!),
    enabled: !!runId && id !== null,
    staleTime: Infinity,
  })
}

export function useTimeline(id: number | null) {
  const { runId } = useRun()
  return useQuery({
    queryKey: ['timeline', runId, id],
    queryFn: () => api.timeline(runId!, id!),
    enabled: !!runId && id !== null,
    staleTime: Infinity,
  })
}

export function useConfig() {
  return useQuery({ queryKey: ['config'], queryFn: api.config })
}
