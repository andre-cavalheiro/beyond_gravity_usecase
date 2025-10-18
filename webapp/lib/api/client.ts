import axios, { type AxiosError } from "axios"
import type { Organization, User, PaginatedResponse  } from "./types"
import { mockOrganization, mockUser } from "./mocks"
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
