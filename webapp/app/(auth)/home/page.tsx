// app/page.tsx
"use client"

import Link from "next/link"
import { useCallback, useEffect, useState } from "react"
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
import { getEarthquakes } from "@/lib/api/client"
import type { Earthquake } from "@/lib/api/types"
import { cn } from "@/lib/utils"
import { ExternalLink } from "lucide-react"
import {
  formatEarthquakeDate,
  getStatusBadgeVariant,
} from "@/lib/earthquakes/utils"

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

  return (
    <Card>
      <CardHeader>
        <CardTitle>Earthquakes</CardTitle>
        <CardDescription>
          Select a row to inspect the event in detail or open the title for the
          official source.
        </CardDescription>
      </CardHeader>
      <CardContent className="pb-6">
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
