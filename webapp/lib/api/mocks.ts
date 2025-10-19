import type { User, Organization, Earthquake } from "./types"

export const mockOrganization: Organization = {
  id: 1,
  name: "Mocked Organization",
}

export const mockUser: User = {
  id: 1,
  name: "Mocked User",
  email: "test@example.com",
  organization_id: 1,
}

export const mockEarthquake: Earthquake = {
  id: 1,
  externalId: "mock-1",
  magnitude: 4.6,
  magnitudeType: "Mw",
  place: "Mockville, Earth",
  status: "reviewed",
  eventType: "earthquake",
  title: "M 4.6 - Mockville, Earth",
  detailUrl: "https://example.com/detail/mock-1",
  infoUrl: "https://example.com/info/mock-1",
  ciimGeoImageUrl: "https://example.com/images/mock-1-ciim-geo.jpg",
  significance: 112,
  tsunami: false,
  feltReports: 5,
  cdi: 3.2,
  mmi: 2.1,
  alert: null,
  stationCount: 18,
  minimumDistance: 12.3,
  rms: 0.76,
  gap: 45,
  occurredAt: new Date().toISOString(),
  externalUpdatedAt: new Date().toISOString(),
  latitude: 37.7749,
  longitude: -122.4194,
  depthKm: 8.5,
}
