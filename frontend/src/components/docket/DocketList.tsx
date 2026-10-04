import { useState } from 'react'

import { ClaimCard } from './ClaimCard'
import { StatusFilter } from './StatusFilter'
import { useClaims, useClaimStatusCounts, useSelectedClaim } from '@/hooks'
import { useDocketStore } from '@/store/docketStore'

export interface DocketListProps {
  className?: string
}

export function DocketList({ className }: DocketListProps) {
  const claims = useClaims()
  const counts = useClaimStatusCounts()
  const selectedClaim = useSelectedClaim()
  const selectClaim = useDocketStore((state) => state.selectClaim)

  const [statusFilter, setStatusFilter] = useState<string | null>(null)

  const filteredClaims = statusFilter
    ? claims.filter((claim) => claim.status === statusFilter)
    : claims

  if (claims.length === 0) {
    return (
      <div className="flex h-full min-h-[160px] items-center justify-center p-6 text-center text-xs text-slate-500">
        No claims found in this docket.
      </div>
    )
  }

  return (
    <div className={['flex flex-col gap-3 p-4', className].filter(Boolean).join(' ')}>
      <StatusFilter
        selectedStatus={statusFilter}
        onSelectStatus={setStatusFilter}
        counts={counts}
        totalCount={claims.length}
      />

      <div className="grid grid-cols-1 gap-2.5">
        {filteredClaims.map((claim) => (
          <ClaimCard
            key={claim.id}
            claim={claim}
            isSelected={claim.id === selectedClaim?.id}
            onSelect={(id) => selectClaim(id === selectedClaim?.id ? null : id)}
          />
        ))}
      </div>
    </div>
  )
}
