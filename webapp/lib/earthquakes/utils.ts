type BadgeVariant = "default" | "secondary" | "destructive" | "outline"

export const earthquakeStatusVariants: Record<string, BadgeVariant> = {
  reviewed: "default",
  automatic: "secondary",
  deleted: "destructive",
}

export function getStatusBadgeVariant(
  status: string | null | undefined
): BadgeVariant {
  if (!status) {
    return "outline"
  }

  return (
    earthquakeStatusVariants[status.toLowerCase()] ??
    "outline"
  )
}

export function formatEarthquakeDate(
  isoString: string | null | undefined,
  options: Intl.DateTimeFormatOptions = {
    dateStyle: "medium",
    timeStyle: "short",
  }
): string {
  if (!isoString) {
    return "—"
  }

  try {
    return new Intl.DateTimeFormat(undefined, options).format(
      new Date(isoString)
    )
  } catch {
    return isoString
  }
}
