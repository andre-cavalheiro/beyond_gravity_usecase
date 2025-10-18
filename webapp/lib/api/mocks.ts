import type { User, Organization } from "./types"


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
