# ARTHSAVORA — WORKSPACE & IDENTITY API REFERENCE

## 1. Overview

This document provides complete contract specifications for the Identity, User Profile, Workspace Lifecycle, Membership Governance, and Cryptographic Invitation endpoints implemented in Prompt 07.

**Base URL:** `/api/v1`  
**Authentication:** Bearer JWT in `Authorization` header.  
**Multi-Tenancy Context:** `X-Workspace-ID` header required for workspace-scoped actions.

---

## 2. User Identity & Profiles Endpoints

### 2.1 Get Current User Profile
`GET /api/v1/users/me`

- **Headers:** `Authorization: Bearer <token>`
- **Response (200 OK):**
```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "email": "investor@example.com",
  "full_name": "Ashutosh Mishra",
  "phone_number": "+919876543210",
  "auth_provider": "local",
  "is_active": true,
  "is_verified": true,
  "created_at": "2026-11-14T05:00:00Z",
  "profile": {
    "display_name": "Ashutosh",
    "avatar_url": "https://assets.arthsavora.in/avatars/ashutosh.png",
    "preferred_language": "en-IN",
    "default_currency": "INR",
    "timezone": "Asia/Kolkata",
    "country": "IN",
    "locale": "en-IN",
    "theme": "dark",
    "notification_preferences": {},
    "is_profile_complete": true
  }
}
```

### 2.2 Update User Profile
`PATCH /api/v1/users/me`

- **Headers:** `Authorization: Bearer <token>`
- **Request Body:**
```json
{
  "display_name": "Ashutosh M.",
  "default_currency": "INR",
  "timezone": "Asia/Kolkata",
  "locale": "en-IN",
  "theme": "dark"
}
```
- **Response (200 OK):** Updated `UserDetailResponse`.

### 2.3 Deactivate Account
`POST /api/v1/users/me/deactivate`

- **Headers:** `Authorization: Bearer <token>`
- **Request Body:**
```json
{
  "confirm": true
}
```
- **Response (200 OK):**
```json
{
  "status": "success",
  "message": "Account has been safely deactivated."
}
```

---

## 3. Workspace Lifecycle Endpoints

### 3.1 List Accessible Workspaces
`GET /api/v1/workspaces`

- **Headers:** `Authorization: Bearer <token>`
- **Response (200 OK):** List of `WorkspaceResponse` items.

### 3.2 Create Workspace
`POST /api/v1/workspaces`

- **Headers:** `Authorization: Bearer <token>`
- **Request Body (Business Example):**
```json
{
  "name": "Artha Advisory Services",
  "type": "business",
  "currency": "INR",
  "timezone": "Asia/Kolkata",
  "country": "IN",
  "business_profile": {
    "legal_business_name": "Artha Advisory Services LLP",
    "trade_name": "Artha Advisory",
    "entity_type": "llp",
    "gstin": "27AAACA1234A1Z5",
    "pan": "AAACA1234A",
    "industry": "Financial Consulting",
    "financial_year_start_month": 4
  }
}
```
- **Response (201 Created):**
```json
{
  "id": "e83fbefb-4c2d-45f8-8098-90db20f5c71b",
  "name": "Artha Advisory Services",
  "slug": "artha-advisory-services-a1b2c3",
  "type": "business",
  "owner_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "currency": "INR",
  "default_currency": "INR",
  "timezone": "Asia/Kolkata",
  "country": "IN",
  "status": "active",
  "settings": {
    "business_profile": {
      "legal_business_name": "Artha Advisory Services LLP",
      "entity_type": "llp",
      "gstin": "27AAACA1234A1Z5",
      "pan": "AAACA1234A"
    }
  },
  "created_at": "2026-11-14T05:05:00Z"
}
```

### 3.3 Update Workspace Metadata
`PATCH /api/v1/workspaces/{workspace_id}`

- **Headers:** `Authorization: Bearer <token>`, `X-Workspace-ID: <id>`
- **Permission Required:** `Permission.UPDATE_WORKSPACE`
- **Request Body:**
```json
{
  "name": "Artha Advisory Services Group",
  "timezone": "Asia/Kolkata"
}
```

### 3.4 Archive Workspace
`POST /api/v1/workspaces/{workspace_id}/archive`

- **Headers:** `Authorization: Bearer <token>`, `X-Workspace-ID: <id>`
- **Permission Required:** `Permission.ARCHIVE_WORKSPACE`
- **Response (200 OK):** Workspace with `status="archived"`.

### 3.5 Restore Workspace
`POST /api/v1/workspaces/{workspace_id}/restore`

- **Headers:** `Authorization: Bearer <token>`, `X-Workspace-ID: <id>`
- **Permission Required:** `Permission.RESTORE_WORKSPACE`
- **Response (200 OK):** Workspace with `status="active"`.

### 3.6 Transfer Ownership
`POST /api/v1/workspaces/{workspace_id}/ownership-transfer`

- **Headers:** `Authorization: Bearer <token>`, `X-Workspace-ID: <id>`
- **Permission Required:** Only current workspace Owner
- **Request Body:**
```json
{
  "new_owner_id": "7b848c7f-9f79-4d8e-9088-751726a8d79a",
  "previous_owner_role": "admin",
  "confirm": true
}
```
- **Response (200 OK):** Updated workspace with `owner_id` set to successor.

---

## 4. Memberships & Invitations Endpoints

### 4.1 List Workspace Members
`GET /api/v1/workspaces/{workspace_id}/members`

- **Headers:** `Authorization: Bearer <token>`, `X-Workspace-ID: <id>`
- **Permission Required:** `Permission.VIEW_MEMBERS`

### 4.2 Add Member Directly
`POST /api/v1/workspaces/{workspace_id}/members`

- **Headers:** `Authorization: Bearer <token>`, `X-Workspace-ID: <id>`
- **Permission Required:** `Permission.INVITE_MEMBERS`
- **Request Body:**
```json
{
  "email": "colleague@example.com",
  "role": "staff"
}
```

### 4.3 Update Member Role
`PATCH /api/v1/workspaces/{workspace_id}/members/{membership_id}`

- **Headers:** `Authorization: Bearer <token>`, `X-Workspace-ID: <id>`
- **Permission Required:** `Permission.UPDATE_MEMBER_ROLE`
- **Request Body:**
```json
{
  "role": "accountant"
}
```

### 4.4 Remove Member
`DELETE /api/v1/workspaces/{workspace_id}/members/{membership_id}`

- **Headers:** `Authorization: Bearer <token>`, `X-Workspace-ID: <id>`
- **Permission Required:** `Permission.REMOVE_MEMBERS` (or self-removal)

### 4.5 Issue Workspace Invitation
`POST /api/v1/workspaces/{workspace_id}/invitations`

- **Headers:** `Authorization: Bearer <token>`, `X-Workspace-ID: <id>`
- **Permission Required:** `Permission.INVITE_MEMBERS`
- **Request Body:**
```json
{
  "email": "partner@example.com",
  "role": "admin"
}
```
- **Response (201 Created):**
```json
{
  "id": "18c0df11-7a6e-4fa0-b384-569d27a1b87a",
  "workspace_id": "e83fbefb-4c2d-45f8-8098-90db20f5c71b",
  "email": "partner@example.com",
  "role": "admin",
  "invited_by_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "pending",
  "expires_at": "2026-11-21T05:05:00Z",
  "created_at": "2026-11-14T05:05:00Z",
  "invitation_token": "k8X2m_9Pz1Q7vL4eA..."
}
```

### 4.6 List Pending Invitations
`GET /api/v1/workspaces/{workspace_id}/invitations`

- **Headers:** `Authorization: Bearer <token>`, `X-Workspace-ID: <id>`
- **Response (200 OK):** List of invitations (`invitation_token` is masked as `null`).

### 4.7 Revoke Invitation
`POST /api/v1/workspaces/{workspace_id}/invitations/{invitation_id}/revoke`

- **Headers:** `Authorization: Bearer <token>`, `X-Workspace-ID: <id>`
- **Permission Required:** `Permission.INVITE_MEMBERS`

### 4.8 Accept Invitation
`POST /api/v1/invitations/{token}/accept`

- **Headers:** `Authorization: Bearer <token>`
- **Path Parameter:** `token` (32-byte raw urlsafe token from email invite link)
- **Response (200 OK):**
```json
{
  "id": "67a3e811-92b0-4f81-801a-3a21bc98fa12",
  "workspace_id": "e83fbefb-4c2d-45f8-8098-90db20f5c71b",
  "user_id": "2bc89172-11da-45ca-9a00-1123456789ab",
  "email": "partner@example.com",
  "full_name": "Partner User",
  "role": "admin",
  "status": "active",
  "joined_at": "2026-11-14T05:10:00Z"
}
```
