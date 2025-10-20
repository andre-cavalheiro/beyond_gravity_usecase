'use client'

import Link from "next/link"
import { useParams } from "next/navigation"
import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import type { ReactNode } from "react"
import { ExternalLink, Image as ImageIcon, Loader2, Rotate3d } from "lucide-react"
import * as THREE from "three"
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls"

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
import { Button } from "@/components/ui/button"
import { getEarthquake, getEarthquakeHeightmap } from "@/lib/api/client"
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

type ViewerMode = "image" | "loading" | "heightmap"

function blobToDataUrl(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onloadend = () => {
      if (typeof reader.result === "string") {
        resolve(reader.result)
      } else {
        reject(new Error("Failed to convert blob to data URL"))
      }
    }
    reader.onerror = () => reject(new Error("Failed to read blob"))
    reader.readAsDataURL(blob)
  })
}

type HeightmapViewerProps = {
  src: string
  onLoadError?: (message: string) => void
}

function HeightmapViewer({ src, onLoadError }: HeightmapViewerProps) {
  const containerRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    const container = containerRef.current
    if (!container) {
      return
    }

    const scene = new THREE.Scene()
    scene.background = new THREE.Color("#0f172a")

    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
    })
    renderer.setPixelRatio(window.devicePixelRatio)
    renderer.outputColorSpace = THREE.SRGBColorSpace
    renderer.setSize(container.clientWidth, container.clientHeight)
    container.appendChild(renderer.domElement)

    const camera = new THREE.PerspectiveCamera(
      55,
      container.clientWidth / container.clientHeight,
      0.1,
      100
    )
    camera.position.set(6, 5, 6)

    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.dampingFactor = 0.05
    controls.target.set(0, 0.5, 0)
    controls.update()

    const ambient = new THREE.AmbientLight(0xffffff, 0.55)
    const directional = new THREE.DirectionalLight(0xffffff, 1.15)
    directional.position.set(6, 10, 6)
    scene.add(ambient, directional)

    const grid = new THREE.GridHelper(12, 12, 0x444444, 0x222222)
    scene.add(grid)

    const textureLoader = new THREE.TextureLoader()
    let mesh: THREE.Mesh<
      THREE.PlaneGeometry,
      THREE.MeshStandardMaterial
    > | null = null
    let frameId = 0

    textureLoader.load(
      src,
      (texture) => {
        texture.wrapS = texture.wrapT = THREE.ClampToEdgeWrapping
        texture.minFilter = THREE.LinearFilter
        texture.magFilter = THREE.LinearFilter
        texture.colorSpace = THREE.SRGBColorSpace

        const imageSource = texture.image as
          | { width?: number; height?: number }
          | undefined
        const sourceWidth = imageSource?.width ?? 128
        const sourceHeight = imageSource?.height ?? 128
        const segments = Math.min(
          256,
          Math.max(64, Math.max(sourceWidth, sourceHeight))
        )

        const geometry = new THREE.PlaneGeometry(10, 10, segments, segments)
        geometry.rotateX(-Math.PI / 2)

        const material = new THREE.MeshStandardMaterial({
          color: 0xf0f0f0,
          map: texture,
          displacementMap: texture,
          displacementScale: 2.4,
          metalness: 0.15,
          roughness: 0.85,
        })

        mesh = new THREE.Mesh(geometry, material)
        mesh.position.y = 0.5
        scene.add(mesh)

        const animate = () => {
          controls.update()
          renderer.render(scene, camera)
          frameId = requestAnimationFrame(animate)
        }
        animate()
      },
      undefined,
      (err) => {
        console.error("Failed to load heightmap texture", err)
        onLoadError?.("We couldn't render the 3D visualization. Try again or check the source image.")
      }
    )

    const handleResize = () => {
      if (!container) return
      const { clientWidth, clientHeight } = container
      renderer.setSize(clientWidth, clientHeight)
      camera.aspect = clientWidth / clientHeight
      camera.updateProjectionMatrix()
    }

    handleResize()
    window.addEventListener("resize", handleResize)

    return () => {
      cancelAnimationFrame(frameId)
      window.removeEventListener("resize", handleResize)
      controls.dispose()
      scene.remove(grid)
      grid.geometry.dispose()
      if (Array.isArray(grid.material)) {
        for (const material of grid.material) {
          material.dispose()
        }
      } else {
        grid.material.dispose()
      }
      if (mesh) {
        mesh.geometry.dispose()
        mesh.material.dispose()
        scene.remove(mesh)
      }
      renderer.dispose()
      if (renderer.domElement.parentNode === container) {
        container.removeChild(renderer.domElement)
      }
      scene.clear()
    }
  }, [onLoadError, src])

  return (
    <div
      ref={containerRef}
      className="h-[22rem] w-full overflow-hidden rounded-xl border border-border/40 bg-slate-950/60"
    />
  )
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
  const [viewerMode, setViewerMode] = useState<ViewerMode>("image")
  const [heightmapUrl, setHeightmapUrl] = useState<string | null>(null)
  const [heightmapError, setHeightmapError] = useState<string | null>(null)
  const isMountedRef = useRef(true)

  useEffect(() => {
    isMountedRef.current = true
    return () => {
      isMountedRef.current = false
    }
  }, [])

  useEffect(() => {
    setViewerMode("image")
    setHeightmapUrl(null)
    setHeightmapError(null)
  }, [earthquakeId])

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
        setViewerMode("image")
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

  const handleTransformClick = async () => {
    if (!earthquake) {
      return
    }

    if (viewerMode === "loading") {
      return
    }

    setHeightmapError(null)
    setHeightmapUrl(null)
    setViewerMode("loading")

    try {
      const blob = await getEarthquakeHeightmap(earthquake.id)
      const dataUrl = await blobToDataUrl(blob)
      if (!isMountedRef.current) {
        return
      }
      setHeightmapUrl(dataUrl)
      setViewerMode("heightmap")
    } catch (err) {
      console.error(err)
      setHeightmapError(
        "We couldn't generate the 3D visualization. Please try again."
      )
      setViewerMode("image")
    }
  }

  const handleBackToImage = () => {
    setViewerMode("image")
  }

  const hasImageUrl = Boolean(earthquake?.ciimGeoImageUrl)
  const showOriginalImage =
    viewerMode === "image" && hasImageUrl && !imageLoadError

  const handleViewerLoadError = useCallback((message: string) => {
    setHeightmapError(message)
    setHeightmapUrl(null)
    setViewerMode("image")
  }, [])

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
            {!hasImageUrl && (
              <div className="mb-8 rounded-md border border-border/40 bg-muted/20 px-4 py-3 text-sm text-muted-foreground">
                Earthquake CIIM geo image not available.
              </div>
            )}

            {hasImageUrl && (
              <div className="mb-10 flex flex-col items-center gap-5 px-4 py-6">
                {showOriginalImage && (
                  <img
                    src={earthquake.ciimGeoImageUrl ?? undefined}
                    alt={`Community intensity map for ${earthquake.title}`}
                    className="h-52 w-auto max-w-full rounded-lg border border-border/40 bg-background object-contain shadow-sm"
                    onError={() => setImageLoadError(true)}
                  />
                )}

                {viewerMode === "image" && imageLoadError && (
                  <div className="w-full max-w-3xl rounded-md border border-border/40 bg-muted/20 px-4 py-3 text-sm text-muted-foreground">
                    We couldn't load the intensity map image, but you can still attempt the 3D transformation.
                  </div>
                )}

                {viewerMode === "loading" && (
                  <div className="flex h-72 w-full max-w-3xl flex-col items-center justify-center gap-3 rounded-xl border border-border/40 bg-muted/20">
                    <Loader2 className="size-9 animate-spin text-primary" />
                    <p className="text-sm text-muted-foreground">
                      Generating 3D heightmap…
                    </p>
                  </div>
                )}

                {viewerMode === "heightmap" && heightmapUrl && (
                  <div className="w-full max-w-4xl">
                    <HeightmapViewer
                      src={heightmapUrl}
                      onLoadError={handleViewerLoadError}
                    />
                  </div>
                )}

                {heightmapError && (
                  <div className="w-full max-w-3xl rounded-md border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
                    {heightmapError}
                  </div>
                )}

                <div className="flex flex-wrap items-center justify-center gap-3">
                  <Button
                    onClick={handleTransformClick}
                    disabled={viewerMode === "loading"}
                    className="inline-flex items-center gap-2"
                  >
                    {viewerMode === "loading" ? (
                      <>
                        <Loader2 className="size-4 animate-spin" />
                        Transforming…
                      </>
                    ) : (
                      <>
                        <Rotate3d className="size-4" />
                        Transform to 3D
                      </>
                    )}
                  </Button>
                  {viewerMode === "heightmap" && (
                    <Button
                      variant="outline"
                      onClick={handleBackToImage}
                      className="inline-flex items-center gap-2"
                    >
                      <ImageIcon className="size-4" />
                      View original image
                    </Button>
                  )}
                </div>
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
