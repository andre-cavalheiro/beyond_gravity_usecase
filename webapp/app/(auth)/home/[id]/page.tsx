'use client'

import Link from "next/link"
import { useParams } from "next/navigation"
import { useEffect, useMemo, useState } from "react"
import type { ReactNode } from "react"
import { ExternalLink } from "lucide-react"

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableRow,
} from "@/components/ui/table"
import { getEarthquake } from "@/lib/api/client"
import type { Earthquake } from "@/lib/api/types"
import {
  formatEarthquakeDate,
  getStatusBadgeVariant,
} from "@/lib/earthquakes/utils"
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"

type DetailItem = { label: string; value: ReactNode }
type DetailGroup = {
  id: string
  title: string
  items: DetailItem[]
}

function formatNumber(
  value: number | null | undefined,
  options?: Intl.NumberFormatOptions
): string {
  if (value === null || value === undefined) {
    return "—"
  }

  return value.toLocaleString(undefined, options)
}

function formatDecimal(
  value: number | null | undefined,
  fractionDigits = 1
): string {
  if (value === null || value === undefined) {
    return "—"
  }

  return value.toLocaleString(undefined, {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  })
}

function formatBoolean(value: boolean | null | undefined): string {
  if (value === null || value === undefined) {
    return "—"
  }

  return value ? "Yes" : "No"
}

function formatText(value: string | null | undefined): string {
  if (!value) {
    return "—"
  }

  return value
}

function formatDistance(value: number | null | undefined): string {
  const formatted = formatDecimal(value, 1)
  return formatted === "—" ? formatted : `${formatted} km`
}

function formatDepth(value: number | null | undefined): string {
  const formatted = formatDecimal(value, 1)
  return formatted === "—" ? formatted : `${formatted} km`
}

function formatGeoCoordinate(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "—"
  }

  return value.toFixed(3)
}

export default function EarthquakeDetailPage() {
  const params = useParams<{ id: string }>()
  const earthquakeId = params?.id
  const [earthquake, setEarthquake] = useState<Earthquake | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [imageLoadError, setImageLoadError] = useState(false)

  useEffect(() => {
    if (!earthquakeId) {
      setError("Earthquake not found.")
      setIsLoading(false)
      return
    }

    let isActive = true
    const loadEarthquake = async () => {
      try {
        const data = await getEarthquake(earthquakeId)
        if (!isActive) return
        setEarthquake(data)
        setImageLoadError(false)
      } catch {
        if (!isActive) return
        setError("We couldn't load this earthquake right now. Please try again.")
      } finally {
        if (isActive) {
          setIsLoading(false)
        }
      }
    }

    void loadEarthquake()

    return () => {
      isActive = false
    }
  }, [earthquakeId])

  const detailGroups = useMemo<DetailGroup[]>(() => {
    if (!earthquake) {
      return []
    }

    const metadataItems: DetailItem[] = [
      {
        label: "External ID",
        value: formatText(earthquake.externalId),
      },
      {
        label: "Occurred At",
        value: formatEarthquakeDate(earthquake.occurredAt),
      },
      {
        label: "Event Type",
        value: formatText(earthquake.eventType),
      },
      {
        label: "Status",
        value: (
          <Badge variant={getStatusBadgeVariant(earthquake.status)}>
            {formatText(earthquake.status)}
          </Badge>
        ),
      },
      {
        label: "Info URL",
        value: earthquake.infoUrl ? (
          <Link
            href={earthquake.infoUrl}
            target="_blank"
            rel="noopener"
            className="inline-flex items-center gap-1 text-primary underline-offset-4 hover:underline"
          >
            View details
            <ExternalLink className="size-3.5" aria-hidden="true" />
          </Link>
        ) : (
          "—"
        ),
      },
      {
        label: "JSON Payload",
        value: earthquake.detailUrl ? (
          <Link
            href={earthquake.detailUrl}
            target="_blank"
            rel="noopener"
            className="inline-flex items-center gap-1 text-primary underline-offset-4 hover:underline"
          >
            View payload
            <ExternalLink className="size-3.5" aria-hidden="true" />
          </Link>
        ) : (
          "—"
        ),
      },
    ]

    const impactItems: DetailItem[] = [
      {
        label: "Magnitude",
        value: (() => {
          const formattedMagnitude = formatDecimal(earthquake.magnitude, 1)
          if (formattedMagnitude === "—") {
            return formattedMagnitude
          }

          const magnitudeLabel = earthquake.magnitudeType
            ? `${formattedMagnitude} ${earthquake.magnitudeType.toUpperCase()}`
            : formattedMagnitude

          return magnitudeLabel
        })(),
      },
      {
        label: "Significance",
        value: formatNumber(earthquake.significance),
      },
      {
        label: "RMS",
        value: formatDecimal(earthquake.rms, 2),
      },
      {
        label: "Tsunami",
        value: formatBoolean(earthquake.tsunami),
      },
      {
        label: "Felt Reports",
        value: formatNumber(earthquake.feltReports),
      },
      {
        label: "CDI",
        value: formatDecimal(earthquake.cdi),
      },
      {
        label: "MMI",
        value: formatDecimal(earthquake.mmi),
      },
      {
        label: "Alert",
        value: formatText(earthquake.alert),
      },
      {
        label: "Station Count",
        value: formatNumber(earthquake.stationCount),
      },
    ]

    const geometryItems: DetailItem[] = [
      {
        label: "Place",
        value: formatText(earthquake.place),
      },
      {
        label: "Latitude",
        value: formatGeoCoordinate(earthquake.latitude),
      },
      {
        label: "Longitude",
        value: formatGeoCoordinate(earthquake.longitude),
      },
      {
        label: "Depth",
        value: formatDepth(earthquake.depthKm),
      },
      {
        label: "Minimum Distance",
        value: formatDistance(earthquake.minimumDistance),
      },
      {
        label: "Gap",
        value: (() => {
          const gap = formatNumber(earthquake.gap)
          return gap === "—" ? gap : `${gap}°`
        })(),
      },
    ]

    return [
      { id: "metadata", title: "Metadata", items: metadataItems },
      { id: "impact", title: "Impact", items: impactItems },
      { id: "geometry", title: "Geometry", items: geometryItems },
    ]
  }, [earthquake])

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex flex-wrap items-center gap-2">
          {earthquake?.title ?? "Earthquake details"}
          {earthquake && (
            <Badge variant={getStatusBadgeVariant(earthquake.status)}>
              {earthquake.status}
            </Badge>
          )}
        </CardTitle>
        <CardDescription>
          {earthquake
            ? `${earthquake.place} • ${formatEarthquakeDate(earthquake.occurredAt)}`
            : "Review seismic event information in detail."}
        </CardDescription>
      </CardHeader>
      <CardContent className="pb-6">
        {isLoading && (
          <div className="py-8 text-center text-muted-foreground">
            Loading earthquake…
          </div>
        )}

        {!isLoading && error && (
          <div className="rounded-md border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            {error}
          </div>
        )}

        {!isLoading && !error && earthquake && (
          <>
            {earthquake.ciimGeoImageUrl && !imageLoadError && (
              <div className="mb-10 flex justify-center px-4 py-6">
                <img
                  src={earthquake.ciimGeoImageUrl}
                  alt={`Community intensity map for ${earthquake.title}`}
                  className="h-40 w-auto object-contain"
                  onError={() => setImageLoadError(true)}
                />
              </div>
            )}

            {earthquake.ciimGeoImageUrl && imageLoadError && (
              <div className="mb-8 rounded-md border border-border/40 bg-muted/20 px-4 py-3 text-sm text-muted-foreground">
                We couldn't load the intensity map image.
              </div>
            )}

            {!earthquake.ciimGeoImageUrl && (
              <div className="mb-8 rounded-md border border-border/40 bg-muted/20 px-4 py-3 text-sm text-muted-foreground">
                Earthquake CIIM geo image not available.
              </div>
            )}

            <Accordion
              type="multiple"
              className="mt-6 flex flex-col gap-6"
            >
              {detailGroups.map((group) => {
                const rows: Array<[DetailItem, DetailItem | undefined]> = []
                for (let index = 0; index < group.items.length; index += 2) {
                  rows.push([group.items[index], group.items[index + 1]])
                }

                return (
                  <AccordionItem
                    key={group.id}
                    value={group.id}
                    className="overflow-hidden rounded-xl border border-border/40 bg-card shadow-sm"
                  >
                    <AccordionTrigger className="bg-muted/30 px-6 text-left text-base font-semibold leading-6 hover:bg-muted/60 min-h-[3.5rem]">
                      {group.title}
                    </AccordionTrigger>
                    <AccordionContent className="px-0 py-0">
                      <div className="overflow-x-auto border-t border-border/40 bg-background/40 px-6 py-4">
                        <Table>
                          <TableBody>
                            {rows.map(([left, right], rowIndex) => (
                              <TableRow key={`${group.id}-${rowIndex}`}>
                                <TableCell className="w-48 align-top text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                                  {left.label}
                                </TableCell>
                                <TableCell className="align-top text-base text-foreground">
                                  {left.value}
                                </TableCell>
                                <TableCell className="w-48 align-top text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                                  {right?.label ?? ""}
                                </TableCell>
                                <TableCell className="align-top text-base text-foreground">
                                  {right?.value ?? "—"}
                                </TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </div>
                    </AccordionContent>
                  </AccordionItem>
                )
              })}
            </Accordion>
          </>
        )}
      </CardContent>
    </Card>
  )
}
