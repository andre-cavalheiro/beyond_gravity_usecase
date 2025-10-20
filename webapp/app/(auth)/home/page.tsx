// app/page.tsx
"use client"

import Link from "next/link"
import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react"
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
import {
  ArrowDown,
  ArrowUp,
  ArrowUpDown,
  CheckCircle2,
  ExternalLink,
  Loader2,
  XCircle,
} from "lucide-react"
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

type FiltersFormState = {
  status: string
  minMagnitude: string
  maxMagnitude: string
  title: string
  place: string
  ciimImage: "all" | "with" | "without"
}

const STATUS_FILTER_OPTIONS: { value: string; label: string }[] = [
  { value: "all", label: "All statuses" },
  { value: "reviewed", label: "Reviewed" },
  { value: "automatic", label: "Automatic" },
  { value: "deleted", label: "Deleted" },
]

const CIIM_IMAGE_FILTER_OPTIONS: { value: "all" | "with" | "without"; label: string }[] =
  [
    { value: "all", label: "All CIIM statuses" },
    { value: "with", label: "Has CIIM image" },
    { value: "without", label: "Missing CIIM image" },
  ]

function formatMagnitude(
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

function getDefaultFilters(): FiltersFormState {
  return {
    status: "all",
    minMagnitude: "",
    maxMagnitude: "",
    title: "",
    place: "",
    ciimImage: "all",
  }
}

function escapeIlikeValue(value: string): string {
  return value.replace(/[%_\\]/g, "\\$&")
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
  const [filtersForm, setFiltersForm] = useState<FiltersFormState>(
    () => getDefaultFilters()
  )
  const [appliedFilters, setAppliedFilters] = useState<FiltersFormState>(
    () => getDefaultFilters()
  )
  const [filtersError, setFiltersError] = useState<string | null>(null)
  const [sortState, setSortState] = useState<{
    field: string
    direction: "asc" | "desc"
  } | null>(null)
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

  const validateAndApplyFilters = useCallback(
    (nextFilters: FiltersFormState) => {
      const trimmedMin = nextFilters.minMagnitude.trim()
      const trimmedMax = nextFilters.maxMagnitude.trim()
      const trimmedTitle = nextFilters.title.trim()
      const trimmedPlace = nextFilters.place.trim()
      const normalizedStatus =
        nextFilters.status.trim().toLowerCase() || "all"
      const ciimImage = nextFilters.ciimImage

      const parsedMin = trimmedMin ? Number.parseFloat(trimmedMin) : null
      const parsedMax = trimmedMax ? Number.parseFloat(trimmedMax) : null

      if (trimmedMin && (parsedMin === null || Number.isNaN(parsedMin))) {
        setFiltersError("Enter a valid minimum magnitude.")
        return
      }

      if (trimmedMax && (parsedMax === null || Number.isNaN(parsedMax))) {
        setFiltersError("Enter a valid maximum magnitude.")
        return
      }

      if (parsedMin !== null && parsedMin < 0) {
        setFiltersError("Minimum magnitude cannot be negative.")
        return
      }

      if (parsedMax !== null && parsedMax < 0) {
        setFiltersError("Maximum magnitude cannot be negative.")
        return
      }

      if (parsedMin !== null && parsedMax !== null && parsedMin > parsedMax) {
        setFiltersError("Minimum magnitude cannot exceed the maximum magnitude.")
        return
      }

      setFiltersError(null)

      const normalizedFilters: FiltersFormState = {
        status: normalizedStatus,
        minMagnitude: trimmedMin,
        maxMagnitude: trimmedMax,
        title: trimmedTitle,
        place: trimmedPlace,
        ciimImage,
      }

      if (
        normalizedFilters.status === appliedFilters.status &&
        normalizedFilters.minMagnitude === appliedFilters.minMagnitude &&
        normalizedFilters.maxMagnitude === appliedFilters.maxMagnitude &&
        normalizedFilters.title === appliedFilters.title &&
        normalizedFilters.place === appliedFilters.place &&
        normalizedFilters.ciimImage === appliedFilters.ciimImage
      ) {
        return
      }

      setAppliedFilters(normalizedFilters)
    },
    [appliedFilters]
  )

  const handleFilterChange = useCallback(
    <K extends keyof FiltersFormState>(field: K, value: FiltersFormState[K]) => {
      setFiltersForm((prev) => {
        const next = { ...prev, [field]: value }
        validateAndApplyFilters(next)
        return next
      })
    },
    [validateAndApplyFilters]
  )

  const loadEarthquakes = useCallback(
    async (cursor: string | null, pageNumber: number, isInitial = false) => {
      setError(null)
      if (isInitial) {
        setIsLoading(true)
      } else {
        setIsPaginating(true)
      }

      const filterParams: string[] = []
      const trimmedStatus = appliedFilters.status.trim().toLowerCase()
      if (trimmedStatus && trimmedStatus !== "all") {
        filterParams.push(`status:eq:${trimmedStatus}`)
      }

      const trimmedMinMagnitude = appliedFilters.minMagnitude.trim()
      if (trimmedMinMagnitude) {
        filterParams.push(`magnitude:gte:${trimmedMinMagnitude}`)
      }

      const trimmedMaxMagnitude = appliedFilters.maxMagnitude.trim()
      if (trimmedMaxMagnitude) {
        filterParams.push(`magnitude:lte:${trimmedMaxMagnitude}`)
      }

      const trimmedTitle = appliedFilters.title.trim()
      if (trimmedTitle) {
        const escapedTitle = escapeIlikeValue(trimmedTitle)
        filterParams.push(`title:ilike:%${escapedTitle}%`)
      }

      const trimmedPlace = appliedFilters.place.trim()
      if (trimmedPlace) {
        const escapedPlace = escapeIlikeValue(trimmedPlace)
        filterParams.push(`place:ilike:%${escapedPlace}%`)
      }

      if (appliedFilters.ciimImage === "with") {
        filterParams.push("ciim_geo_image_url:isnotnull")
      } else if (appliedFilters.ciimImage === "without") {
        filterParams.push("ciim_geo_image_url:isnull")
      }

      const sortParams =
        sortState !== null
          ? [`${sortState.field}:${sortState.direction}`]
          : undefined

      try {
        const response = await getEarthquakes({
          cursor,
          filters: filterParams.length > 0 ? filterParams : undefined,
          sorts: sortParams,
        })
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
    [appliedFilters, sortState]
  )

  useEffect(() => {
    setCursorHistory([null])
    setCurrentPage(1)
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

  const hasAppliedFilters =
    appliedFilters.status !== "all" ||
    appliedFilters.minMagnitude !== "" ||
    appliedFilters.maxMagnitude !== "" ||
    appliedFilters.title !== "" ||
    appliedFilters.place !== "" ||
    appliedFilters.ciimImage !== "all"

  const normalizedFormState = useMemo(
    () => ({
      status: filtersForm.status.trim().toLowerCase() || "all",
      minMagnitude: filtersForm.minMagnitude.trim(),
      maxMagnitude: filtersForm.maxMagnitude.trim(),
      title: filtersForm.title.trim(),
      place: filtersForm.place.trim(),
      ciimImage: filtersForm.ciimImage,
    }),
    [filtersForm]
  )

  const filtersFormIsDefault =
    normalizedFormState.status === "all" &&
    normalizedFormState.minMagnitude === "" &&
    normalizedFormState.maxMagnitude === "" &&
    normalizedFormState.title === "" &&
    normalizedFormState.place === "" &&
    normalizedFormState.ciimImage === "all"

  const handleFiltersReset = useCallback(() => {
    setFiltersError(null)
    const defaults = getDefaultFilters()
    setFiltersForm(() => {
      validateAndApplyFilters(defaults)
      return defaults
    })
  }, [validateAndApplyFilters])

  const handleSortChange = useCallback((field: string) => {
    setSortState((prev) => {
      if (!prev || prev.field !== field) {
        return { field, direction: "asc" }
      }

      if (prev.direction === "asc") {
        return { field, direction: "desc" }
      }

      return null
    })
  }, [])

  const getAriaSort = useCallback(
    (field: string): "ascending" | "descending" | "none" => {
      if (sortState?.field !== field) {
        return "none"
      }

      return sortState.direction === "asc" ? "ascending" : "descending"
    },
    [sortState]
  )

  const renderSortIcon = useCallback(
    (field: string) => {
      if (sortState?.field !== field) {
        return <ArrowUpDown className="size-4" aria-hidden="true" />
      }

      if (sortState.direction === "asc") {
        return <ArrowUp className="size-4" aria-hidden="true" />
      }

      return <ArrowDown className="size-4" aria-hidden="true" />
    },
    [sortState]
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
                Choose up to a three day window to ingest fresh data. Enabeling CIIM geo images lookups will significantly increase the time it takes to pull data (possible time-outs).
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

        <form
          onSubmit={(event) => event.preventDefault()}
          className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-6"
        >
          <div className="space-y-1.5 xl:col-span-2">
            <label
              htmlFor="title-filter"
              className="text-sm font-medium text-foreground"
            >
              Title contains
            </label>
            <input
              id="title-filter"
              type="text"
              value={filtersForm.title}
              onChange={(event) => {
                handleFilterChange("title", event.target.value)
              }}
              placeholder="e.g. indonesia"
              className="w-full rounded-md border border-border/40 bg-background px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
            />
          </div>

          <div className="space-y-1.5 xl:col-span-2">
            <label
              htmlFor="place-filter"
              className="text-sm font-medium text-foreground"
            >
              Location contains
            </label>
            <input
              id="place-filter"
              type="text"
              value={filtersForm.place}
              onChange={(event) => {
                handleFilterChange("place", event.target.value)
              }}
              placeholder="e.g. Alaska"
              className="w-full rounded-md border border-border/40 bg-background px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
            />
          </div>

          <div className="space-y-1.5">
            <label
              htmlFor="status-filter"
              className="text-sm font-medium text-foreground"
            >
              Status
            </label>
            <select
              id="status-filter"
              value={filtersForm.status}
              onChange={(event) => {
                handleFilterChange("status", event.target.value)
              }}
              className="w-full rounded-md border border-border/40 bg-background px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
            >
              {STATUS_FILTER_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-1.5">
            <label
              htmlFor="ciim-filter"
              className="text-sm font-medium text-foreground"
            >
              CIIM image
            </label>
            <select
              id="ciim-filter"
              value={filtersForm.ciimImage}
              onChange={(event) => {
                handleFilterChange(
                  "ciimImage",
                  event.target.value as FiltersFormState["ciimImage"]
                )
              }}
              className="w-full rounded-md border border-border/40 bg-background px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
            >
              {CIIM_IMAGE_FILTER_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-1.5">
            <label
              htmlFor="min-magnitude-filter"
              className="text-sm font-medium text-foreground"
            >
              Min magnitude
            </label>
            <input
              id="min-magnitude-filter"
              type="number"
              min="0"
              step="0.1"
              value={filtersForm.minMagnitude}
              onChange={(event) => {
                handleFilterChange("minMagnitude", event.target.value)
              }}
              className="w-full rounded-md border border-border/40 bg-background px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
            />
          </div>

          <div className="space-y-1.5">
            <label
              htmlFor="max-magnitude-filter"
              className="text-sm font-medium text-foreground"
            >
              Max magnitude
            </label>
            <input
              id="max-magnitude-filter"
              type="number"
              min="0"
              step="0.1"
              value={filtersForm.maxMagnitude}
              onChange={(event) => {
                handleFilterChange("maxMagnitude", event.target.value)
              }}
              className="w-full rounded-md border border-border/40 bg-background px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
            />
          </div>

          <div className="flex flex-col justify-end gap-2 sm:col-span-2 xl:col-span-2 xl:flex-row xl:items-end xl:justify-end">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="w-full xl:w-auto"
              disabled={!hasAppliedFilters && filtersFormIsDefault}
              onClick={handleFiltersReset}
            >
              Reset filters
            </Button>
          </div>

          {filtersError && (
            <p className="sm:col-span-2 xl:col-span-6 text-sm text-destructive">
              {filtersError}
            </p>
          )}
        </form>

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
                  <TableHead aria-sort={getAriaSort("title")}>
                    <button
                      type="button"
                      onClick={() => handleSortChange("title")}
                      className="flex w-full items-center gap-2 text-left font-medium text-muted-foreground"
                    >
                      <span>Title</span>
                      {renderSortIcon("title")}
                    </button>
                  </TableHead>
                  <TableHead aria-sort={getAriaSort("place")}>
                    <button
                      type="button"
                      onClick={() => handleSortChange("place")}
                      className="flex w-full items-center gap-2 text-left font-medium text-muted-foreground"
                    >
                      <span>Place</span>
                      {renderSortIcon("place")}
                    </button>
                  </TableHead>
                  <TableHead aria-sort={getAriaSort("occurred_at")}>
                    <button
                      type="button"
                      onClick={() => handleSortChange("occurred_at")}
                      className="flex w-full items-center gap-2 text-left font-medium text-muted-foreground"
                    >
                      <span>Occurred At</span>
                      {renderSortIcon("occurred_at")}
                    </button>
                  </TableHead>
                  <TableHead
                    className="w-32"
                    aria-sort={getAriaSort("magnitude")}
                  >
                    <button
                      type="button"
                      onClick={() => handleSortChange("magnitude")}
                      className="flex w-full items-center gap-2 text-left font-medium text-muted-foreground"
                    >
                      <span>Magnitude</span>
                      {renderSortIcon("magnitude")}
                    </button>
                  </TableHead>
                  <TableHead
                    className="w-32"
                    aria-sort={getAriaSort("status")}
                  >
                    <button
                      type="button"
                      onClick={() => handleSortChange("status")}
                      className="flex w-full items-center gap-2 text-left font-medium text-muted-foreground"
                    >
                      <span>Status</span>
                      {renderSortIcon("status")}
                    </button>
                  </TableHead>
                  <TableHead
                    className="w-44 text-center"
                    aria-sort={getAriaSort("ciim_geo_image_url")}
                  >
                    <button
                      type="button"
                      onClick={() =>
                        handleSortChange("ciim_geo_image_url")
                      }
                      className="flex w-full items-center justify-center gap-2 text-center font-medium text-muted-foreground"
                    >
                      <span>CIIM Image Available</span>
                      {renderSortIcon("ciim_geo_image_url")}
                    </button>
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
                    <TableCell className="whitespace-nowrap">
                      {formatMagnitude(quake.magnitude)}
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
