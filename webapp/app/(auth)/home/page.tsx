// app/page.tsx
"use client"

import Link from "next/link"
import { useCallback, useEffect, useState, type FormEvent } from "react"
import { useRouter } from "next/navigation"

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
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import {
  Sheet,
  SheetClose,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet"
import { getEarthquakes, ingestEarthquakes } from "@/lib/api/client"
import type { Earthquake } from "@/lib/api/types"
import { cn } from "@/lib/utils"
import { CheckCircle2, ExternalLink, Loader2, XCircle } from "lucide-react"
import {
  formatEarthquakeDate,
  getStatusBadgeVariant,
} from "@/lib/earthquakes/utils"

function getLocalDateInputValue(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, "0")
  const day = String(date.getDate()).padStart(2, "0")
  return `${year}-${month}-${day}`
}

function getTodayDateInputValue(): string {
  return getLocalDateInputValue(new Date())
}

type IngestFormState = {
  startDate: string
  endDate: string
  minMagnitude: string
  enforceCiimGeo: boolean
}

export default function HomePage() {
  const [earthquakes, setEarthquakes] = useState<Earthquake[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isPaginating, setIsPaginating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [currentPage, setCurrentPage] = useState(1)
  const [cursorHistory, setCursorHistory] = useState<(string | null)[]>([null])
  const [paginationInfo, setPaginationInfo] = useState({
    nextCursor: null as string | null,
    previousCursor: null as string | null,
    total: 0,
    totalPages: 1,
    size: 20,
  })
  const today = getTodayDateInputValue()
  const defaultStartDate = getLocalDateInputValue(
    new Date(Date.now() - 3 * 24 * 60 * 60 * 1000)
  )
  const [isIngestSheetOpen, setIsIngestSheetOpen] = useState(false)
  const [ingestForm, setIngestForm] = useState<IngestFormState>({
    startDate: defaultStartDate,
    endDate: today,
    minMagnitude: "",
    enforceCiimGeo: false,
  })
  const [ingestFormError, setIngestFormError] = useState<string | null>(null)
  const [isIngesting, setIsIngesting] = useState(false)
  const [ingestAlert, setIngestAlert] = useState<{
    type: "success" | "error"
    message: string
  } | null>(null)
  const router = useRouter()

  const loadEarthquakes = useCallback(
    async (cursor: string | null, pageNumber: number, isInitial = false) => {
      setError(null)
      if (isInitial) {
        setIsLoading(true)
      } else {
        setIsPaginating(true)
      }

      try {
        const response = await getEarthquakes({ cursor })
        const size = response.size ?? 20
        const total = response.total ?? response.items.length
        const totalPages =
          total > 0 ? Math.max(1, Math.ceil(total / Math.max(size, 1))) : 1

        setEarthquakes(response.items)
        setPaginationInfo({
          nextCursor: response.next_page ?? null,
          previousCursor: response.previous_page ?? null,
          total,
          totalPages,
          size,
        })
        setCurrentPage(pageNumber)
        setCursorHistory((prev) => {
          const history = [...prev]
          if (history.length < pageNumber) {
            history.length = pageNumber
          }
          history[pageNumber - 1] = cursor
          return history
        })
      } catch {
        setError("We couldn't load earthquakes right now. Please try again.")
      } finally {
        if (isInitial) {
          setIsLoading(false)
        } else {
          setIsPaginating(false)
        }
      }
    },
    []
  )

  useEffect(() => {
    void loadEarthquakes(null, 1, true)
  }, [loadEarthquakes])

  const handleNextPage = useCallback(() => {
    if (!paginationInfo.nextCursor) {
      return
    }
    void loadEarthquakes(paginationInfo.nextCursor, currentPage + 1)
  }, [paginationInfo.nextCursor, currentPage, loadEarthquakes])

  const handlePreviousPage = useCallback(() => {
    if (currentPage === 1) {
      return
    }
    const targetCursor = cursorHistory[currentPage - 2] ?? null
    void loadEarthquakes(targetCursor, currentPage - 1)
  }, [cursorHistory, currentPage, loadEarthquakes])

  const handleIngestSheetOpenChange = useCallback((open: boolean) => {
    setIsIngestSheetOpen(open)
    if (!open) {
      setIngestFormError(null)
    }
  }, [])

  const handlePullSubmit = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault()
      if (isIngesting) {
        return
      }

      setIngestFormError(null)
      setIngestAlert(null)

      const { startDate, endDate, minMagnitude, enforceCiimGeo } = ingestForm

      if (!startDate || !endDate) {
        setIngestFormError("Select start and end dates before pulling data.")
        return
      }

      const start = new Date(`${startDate}T00:00:00Z`)
      const end = new Date(`${endDate}T00:00:00Z`)
      if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
        setIngestFormError("Enter valid start and end dates.")
        return
      }
      if (end < start) {
        setIngestFormError("End date must be the same as or after the start date.")
        return
      }
      if (startDate > today || endDate > today) {
        setIngestFormError("Dates cannot be in the future.")
        return
      }
      const diffDays = (end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24)
      if (diffDays > 3) {
        setIngestFormError("Select a window of three days or less.")
        return
      }

      const trimmedMagnitude = minMagnitude.trim()
      let parsedMagnitude: number | null = null
      if (trimmedMagnitude) {
        const numericMagnitude = Number.parseFloat(trimmedMagnitude)
        if (Number.isNaN(numericMagnitude)) {
          setIngestFormError("Enter a valid minimum magnitude.")
          return
        }
        if (numericMagnitude < 0) {
          setIngestFormError("Minimum magnitude cannot be negative.")
          return
        }
        parsedMagnitude = numericMagnitude
      }

      setIsIngesting(true)

      try {
        const response = await ingestEarthquakes({
          start_date: startDate,
          end_date: endDate,
          ...(parsedMagnitude !== null ? { min_magnitude: parsedMagnitude } : {}),
          search_ciim_geo_image_url: enforceCiimGeo,
          enforce_ciim_geo_image_url: enforceCiimGeo,
          limit: 100,
        })

        setIngestAlert({
          type: "success",
          message:
            response.count > 0
              ? `Pulled ${response.count} earthquake${response.count === 1 ? "" : "s"} from USGS.`
              : "No new earthquakes found for the selected range.",
        })

        setIsIngestSheetOpen(false)
        setIngestForm({
          startDate: defaultStartDate,
          endDate: today,
          minMagnitude: "",
          enforceCiimGeo: false,
        })
        setCursorHistory([null])
        void loadEarthquakes(null, 1, true)
      } catch {
        setIngestFormError("We couldn't pull new earthquakes. Please try again.")
        setIngestAlert({
          type: "error",
          message: "We couldn't pull new earthquakes. Please try again.",
        })
      } finally {
        setIsIngesting(false)
      }
    },
    [ingestForm, isIngesting, loadEarthquakes, today, defaultStartDate]
  )

  return (
    <Card>
      <CardHeader className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <CardTitle>Earthquakes</CardTitle>
          <CardDescription>
            Select a row to inspect the event in detail or open the title for the
            official source.
          </CardDescription>
        </div>

        <Sheet open={isIngestSheetOpen} onOpenChange={handleIngestSheetOpenChange}>
          <SheetTrigger asChild>
            <Button size="sm" className="w-full sm:w-auto">
              Sync Earthquakes
            </Button>
          </SheetTrigger>
          <SheetContent className="gap-0 p-0 sm:max-w-md">
            <SheetHeader className="p-4 pb-2">
              <SheetTitle>Pull new earthquakes</SheetTitle>
              <SheetDescription>
                Choose up to a three day window to ingest fresh data. Enabeling CIIM geo images lookups will significantly increase the time it takes to pull data.
              </SheetDescription>
            </SheetHeader>
            <form onSubmit={handlePullSubmit} className="flex h-full flex-col">
              <div className="flex flex-1 flex-col gap-4 overflow-y-auto px-4 pb-2 pt-4">
                <div className="space-y-1.5">
                  <label
                    htmlFor="ingest-start-date"
                    className="text-sm font-medium text-foreground"
                  >
                    Start date
                  </label>
                  <input
                    id="ingest-start-date"
                    type="date"
                    required
                    value={ingestForm.startDate}
                    max={
                      ingestForm.endDate && ingestForm.endDate < today
                        ? ingestForm.endDate
                        : today
                    }
                    onChange={(event) => {
                      const value = event.target.value || ""
                      const normalizedValue =
                        value && value > today ? today : value
                      setIngestForm((prev) => ({
                        ...prev,
                        startDate: normalizedValue,
                      }))
                      setIngestFormError(null)
                    }}
                    className="w-full rounded-md border border-border/40 bg-background px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
                  />
                </div>

                <div className="space-y-1.5">
                  <label
                    htmlFor="ingest-end-date"
                    className="text-sm font-medium text-foreground"
                  >
                    End date
                  </label>
                  <input
                    id="ingest-end-date"
                    type="date"
                    required
                    value={ingestForm.endDate}
                    min={ingestForm.startDate || undefined}
                    max={today}
                    onChange={(event) => {
                      const value = event.target.value || ""
                      const normalizedValue =
                        value && value > today ? today : value
                      setIngestForm((prev) => ({
                        ...prev,
                        endDate: normalizedValue,
                      }))
                      setIngestFormError(null)
                    }}
                    className="w-full rounded-md border border-border/40 bg-background px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
                  />
                </div>

                <div className="space-y-1.5">
                  <label
                    htmlFor="ingest-min-magnitude"
                    className="text-sm font-medium text-foreground"
                  >
                    Min magnitude
                  </label>
                  <input
                    id="ingest-min-magnitude"
                    type="number"
                    min="0"
                    step="0.1"
                    value={ingestForm.minMagnitude}
                    onChange={(event) => {
                      const value = event.target.value
                      setIngestForm((prev) => ({ ...prev, minMagnitude: value }))
                      setIngestFormError(null)
                    }}
                    className="w-full rounded-md border border-border/40 bg-background px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
                  />
                </div>

                <label className="flex items-start gap-3 rounded-md border border-border/40 bg-background px-3 py-3 text-sm shadow-sm transition hover:border-border">
                  <input
                    type="checkbox"
                    checked={ingestForm.enforceCiimGeo}
                    onChange={(event) => {
                      const checked = event.target.checked
                      setIngestForm((prev) => ({ ...prev, enforceCiimGeo: checked }))
                    }}
                    className="mt-1 size-4 rounded border border-border/60 accent-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
                  />
                  <span className="text-sm text-foreground">
                    Only collect earthquakes with available CIIM geo images
                  </span>
                </label>

                {ingestFormError && (
                  <p className="text-sm text-destructive">{ingestFormError}</p>
                )}
              </div>
              <SheetFooter className="mt-0 flex flex-col-reverse gap-2 p-4 pt-0 sm:flex-row sm:justify-end">
                <SheetClose asChild>
                  <Button
                    type="button"
                    variant="ghost"
                    disabled={isIngesting}
                  >
                    Cancel
                  </Button>
                </SheetClose>
                <Button
                  type="submit"
                  className="inline-flex items-center gap-2"
                  disabled={isIngesting}
                >
                  {isIngesting ? (
                    <>
                      <Loader2 className="size-4 animate-spin" />
                      Pulling…
                    </>
                  ) : (
                    "Pull data"
                  )}
                </Button>
              </SheetFooter>
            </form>
          </SheetContent>
        </Sheet>
      </CardHeader>
      <CardContent className="pb-6">
        {ingestAlert && (
          <div
            className={cn(
              "mb-6 rounded-md border px-4 py-3 text-sm",
              ingestAlert.type === "success"
                ? "border-emerald-400/60 bg-emerald-500/10 text-emerald-400"
                : "border-destructive/40 bg-destructive/10 text-destructive"
            )}
          >
            {ingestAlert.message}
          </div>
        )}

        {isLoading && (
          <div className="py-8 text-center text-muted-foreground">
            Loading earthquakes…
          </div>
        )}

        {!isLoading && error && (
          <div className="rounded-md border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            {error}
          </div>
        )}

        {!isLoading && !error && earthquakes.length === 0 && (
          <div className="py-8 text-center text-muted-foreground">
            No earthquakes to display yet.
          </div>
        )}

        {!isLoading && !error && earthquakes.length > 0 && (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Title</TableHead>
                  <TableHead>Place</TableHead>
                  <TableHead>Occurred At</TableHead>
                  <TableHead className="w-32">Status</TableHead>
                  <TableHead className="w-44 text-center">
                    CIIM Image Available
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {earthquakes.map((quake) => (
                  <TableRow
                    key={quake.id}
                    tabIndex={0}
                    onClick={() => router.push(`/home/${quake.id}`)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault()
                        router.push(`/home/${quake.id}`)
                      }
                    }}
                    className={cn(
                      "cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
                    )}
                  >
                    <TableCell className="font-medium">
                      <Link
                        href={quake.infoUrl}
                        target="_blank"
                        rel="noopener"
                        onClick={(event) => event.stopPropagation()}
                        className="inline-flex items-center gap-1 text-foreground underline-offset-4 hover:underline"
                      >
                        <span>{quake.title}</span>
                        <ExternalLink className="size-3.5" aria-hidden="true" />
                      </Link>
                    </TableCell>
                    <TableCell>{quake.place}</TableCell>
                    <TableCell>
                      {formatEarthquakeDate(quake.occurredAt)}
                    </TableCell>
                    <TableCell>
                      <Badge variant={getStatusBadgeVariant(quake.status)}>
                        {quake.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-center">
                      {quake.ciimGeoImageUrl ? (
                        <span className="inline-flex items-center justify-center">
                          <CheckCircle2
                            className="size-5 text-emerald-500"
                            aria-hidden="true"
                          />
                          <span className="sr-only">CIIM image available</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center justify-center">
                          <XCircle
                            className="size-5 text-destructive"
                            aria-hidden="true"
                          />
                          <span className="sr-only">CIIM image unavailable</span>
                        </span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>

            <div className="mt-10 flex flex-col gap-2 rounded-lg bg-muted/30 px-5 py-6 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
              <span className="text-sm text-muted-foreground">
                Total earthquakes: {paginationInfo.total} • Page {currentPage} of{" "}
                {paginationInfo.totalPages}
              </span>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handlePreviousPage}
                  disabled={isPaginating || currentPage === 1}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleNextPage}
                  disabled={isPaginating || !paginationInfo.nextCursor}
                >
                  Next
                </Button>
              </div>
            </div>
            {isPaginating && (
              <div className="mt-4 text-sm text-muted-foreground">
                Loading page…
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
}
