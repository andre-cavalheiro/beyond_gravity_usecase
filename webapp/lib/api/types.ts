export interface PaginatedResponse<T> {
  items: T[]
  total?: number
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
