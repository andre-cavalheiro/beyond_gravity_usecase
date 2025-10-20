import axios, { type AxiosError } from "axios"
import type { Organization, User, PaginatedResponse, Earthquake } from "./types"
import { mockOrganization, mockUser, mockEarthquake } from "./mocks"
import { env } from "@/app/env"
import { auth } from "@/lib/auth/firebase"

const api = axios.create({
  baseURL: env.NEXT_PUBLIC_API_URL,
  timeout: 10000, // 10 seconds timeout
})

// Add an interceptor to include the Firebase token in each request
api.interceptors.request.use(async (config) => {
  const user = auth.currentUser
  if (user) {
    const token = await user.getIdToken()
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Add an interceptor with generic error handling logic
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response) {
      console.error("API Error Response:", error.response.data)
      console.error("API Error Status:", error.response.status)
    } else if (error.request) {
      console.error("API Error Request:", error.request)
    } else {
      console.error("API Error Message:", error.message)
    }
    return Promise.reject(error)
  }
)

// Add a response interceptor for better error handling
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response) {
      console.error("API Error Response:", error.response.data)
      console.error("API Error Status:", error.response.status)
    } else if (error.request) {
      console.error("API Error Request:", error.request)
    } else {
      console.error("API Error Message:", error.message)
    }
    return Promise.reject(error)
  },
)

export async function getUser(): Promise<User> {
  if (env.NEXT_PUBLIC_USE_MOCKS) {
    return mockUser
  }

  try {
    const response = await api.get<User>("/users/self")
    return response.data
  } catch (error) {
    console.error("Error getting user:", error)
    throw error
  }
}

export async function getOrganization(): Promise<Organization> {
  if (env.NEXT_PUBLIC_USE_MOCKS) {
    return mockOrganizationFree
  }

  try {
    const response = await api.get<Organization>("/organizations/self")
    return response.data
  } catch (error) {
    console.error("Error getting organization:", error)
    throw error
  }
}

export async function createOrganization(name: string): Promise<Organization> {
  if (env.NEXT_PUBLIC_USE_MOCKS) {
    return mockOrganizationFree
  }

  try {
    const response = await api.post<Organization>("/organizations", { name })
    return response.data
  } catch (error) {
    console.error("Error creating organization:", error)
    throw error
  }
}

type GetEarthquakesParams = {
  cursor?: string | null
  filters?: Record<string, unknown>
}

const EARTHQUAKE_PAGE_SIZE = 20

export async function getEarthquakes(
  options?: GetEarthquakesParams
): Promise<PaginatedResponse<Earthquake>> {
  const { cursor, filters } = options ?? {}

  if (env.NEXT_PUBLIC_USE_MOCKS) {
    return {
      items: [mockEarthquake],
      total: 1,
      size: EARTHQUAKE_PAGE_SIZE,
      current_page: null,
      next_page: null,
      previous_page: null,
      current_page_backwards: null,
    }
  }

  try {
    const searchParams = new URLSearchParams()
    searchParams.set("includeTotal", "true")
    searchParams.set("size", String(EARTHQUAKE_PAGE_SIZE))

    if (cursor) {
      searchParams.set("cursor", cursor)
    }
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          searchParams.set(key, String(value))
        }
      })
    }

    const response = await api.get<PaginatedResponse<Earthquake>>(
      "/earthquakes",
      {
        params: searchParams,
      },
    )
    return response.data
  } catch (error) {
    console.error("Error getting earthquakes:", error)
    throw error
  }
}

export async function getEarthquake(
  id: string | number
): Promise<Earthquake> {
  if (env.NEXT_PUBLIC_USE_MOCKS) {
    return mockEarthquake
  }

  try {
    const response = await api.get<Earthquake>(
      `/earthquakes/${encodeURIComponent(String(id))}`
    )
    return response.data
  } catch (error) {
    console.error(`Error getting earthquake ${id}:`, error)
    throw error
  }
}

export async function getEarthquakeHeightmap(
  id: string | number
): Promise<Blob> {
  if (env.NEXT_PUBLIC_USE_MOCKS) {
    const response = await fetch("/mock-heightmap.png")
    if (!response.ok) {
      throw new Error("Failed to load mock heightmap")
    }
    return await response.blob()
  }

  try {
    const response = await api.get<Blob>(
      `/earthquakes/${encodeURIComponent(String(id))}/ciim_geo_heightmap`,
      {
        responseType: "blob",
        timeout: 45000,
      }
    )
    return response.data
  } catch (error) {
    console.error(`Error getting earthquake ${id} heightmap:`, error)
    throw error
  }
}
