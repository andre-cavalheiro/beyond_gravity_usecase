export interface PaginatedResponse<T> {
  items: T[]
  total?: number
  size?: number
  current_page?: string | null
  current_page_backwards?: string | null
  previous_page?: string | null
  next_page?: string | null
}

export interface User {
  id: number
  name: string
  email: string
  organization_id: number
}

export interface Organization {
  id: number
  name: string
}

export interface Earthquake {
  id: number
  externalId: string
  magnitude: number
  magnitudeType: string
  place: string
  status: string
  eventType: string
  title: string
  detailUrl: string
  infoUrl: string
  ciimGeoImageUrl: string | null
  significance: number
  tsunami: boolean
  feltReports: number | null
  cdi: number | null
  mmi: number | null
  alert: string | null
  stationCount: number | null
  minimumDistance: number | null
  rms: number
  gap: number | null
  occurredAt: string
  externalUpdatedAt: string
  latitude: number
  longitude: number
  depthKm: number
}
