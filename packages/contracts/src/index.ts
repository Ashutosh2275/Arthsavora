/**
 * Arthsavora Shared API Contracts
 * Single source of truth for frontend, mobile, and backend DTOs.
 */

// -------------------------------------------------------------------------
// Common & Primitives
// -------------------------------------------------------------------------

export type UUID = string;
export type ISODateString = string;
export type CurrencyCode = 'INR' | 'USD' | 'EUR' | 'GBP';

export interface MoneyAmount {
  /** Exact amount in standard currency units as a formatted decimal string (e.g. "1500.50") */
  amount: string;
  /** Amount in integer minor currency units (e.g. 150050 paise) */
  paise: number;
  /** ISO 4217 currency code */
  currency: CurrencyCode;
}

export interface PaginationParams {
  page?: number;
  limit?: number;
  cursor?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
  has_more: boolean;
}

export interface ApiErrorDetail {
  loc: (string | number)[];
  msg: string;
  type: string;
}

export interface ApiErrorResponse {
  error: {
    code: string;
    message: string;
    details?: ApiErrorDetail[];
    request_id?: string;
  };
}

// -------------------------------------------------------------------------
// Identity & Workspace Contracts
// -------------------------------------------------------------------------

export interface UserResponse {
  id: UUID;
  email: string;
  full_name: string;
  is_active: boolean;
  created_at: ISODateString;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in?: number;
}

export type WorkspaceType = 'PERSONAL' | 'FAMILY' | 'BUSINESS';
export type WorkspaceRole = 'OWNER' | 'ADMIN' | 'MEMBER' | 'VIEWER' | 'BOOKKEEPER';

export interface WorkspaceResponse {
  id: UUID;
  name: string;
  type: WorkspaceType;
  currency: CurrencyCode;
  owner_id: UUID;
  created_at: ISODateString;
}

export interface UserProfileResponse {
  display_name?: string | null;
  avatar_url?: string | null;
  preferred_language: string;
  default_currency: CurrencyCode;
  timezone: string;
  country: string;
  locale: string;
  theme: string;
  notification_preferences: Record<string, unknown>;
  is_profile_complete: boolean;
}

export interface UserProfileUpdateRequest {
  full_name?: string;
  display_name?: string;
  avatar_url?: string;
  preferred_language?: string;
  locale?: string;
  default_currency?: CurrencyCode;
  timezone?: string;
  country?: string;
  theme?: string;
  notification_preferences?: Record<string, unknown>;
}

export interface DeactivateAccountRequest {
  confirm: boolean;
}

export interface UserDetailResponse {
  id: UUID;
  email: string;
  full_name: string;
  phone_number?: string | null;
  auth_provider: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: ISODateString;
  profile?: UserProfileResponse | null;
}

export interface WorkspaceMemberResponse {
  id: UUID;
  workspace_id: UUID;
  user_id: UUID;
  email?: string;
  full_name?: string;
  role: WorkspaceRole | string;
  status?: string;
  joined_at: ISODateString;
}

export interface BusinessProfile {
  legal_business_name?: string | null;
  trade_name?: string | null;
  business_name?: string | null;
  entity_type?: string | null;
  business_type?: string | null;
  industry?: string | null;
  tax_identifier?: string | null;
  financial_year_start_month?: number;
  business_email?: string | null;
  contact_number?: string | null;
  address?: Record<string, unknown>;
  gstin?: string | null;
  pan?: string | null;
  profile_status?: string;
}

export interface WorkspaceCreateRequest {
  name: string;
  type: 'personal' | 'family' | 'business' | WorkspaceType;
  currency?: CurrencyCode;
  timezone?: string;
  country?: string;
  business_profile?: BusinessProfile;
}

export interface WorkspaceUpdateRequest {
  name?: string;
  timezone?: string;
  default_currency?: CurrencyCode;
  country?: string;
  business_profile?: BusinessProfile;
}

export interface OwnershipTransferRequest {
  new_owner_id: UUID;
  previous_owner_role?: string;
  confirm: boolean;
}

export interface UpdateMemberRoleRequest {
  role: string;
}

export interface CreateInvitationRequest {
  email: string;
  role: string;
}

export interface InvitationResponse {
  id: UUID;
  workspace_id: UUID;
  email: string;
  role: string;
  invited_by_id: UUID;
  status: 'pending' | 'accepted' | 'revoked' | 'expired';
  expires_at: ISODateString;
  accepted_at?: ISODateString | null;
  created_at: ISODateString;
  invitation_token?: string | null;
}

// -------------------------------------------------------------------------
// Expense & Transaction Contracts
// -------------------------------------------------------------------------

export type ExpenseCategory =
  | 'Food'
  | 'Travel'
  | 'Shopping'
  | 'Bills'
  | 'Entertainment'
  | 'Health'
  | 'Housing'
  | 'Education'
  | 'Investment'
  | 'Business'
  | 'Uncategorized';

export type TransactionSource = 'MANUAL' | 'SMS' | 'OCR' | 'BANK_FEED' | 'IMPORT';
export type TransactionStatus = 'DRAFT' | 'PENDING' | 'POSTED' | 'RECONCILED' | 'REVERSED';

export interface ExpenseResponse {
  id: string;
  user_id: string;
  workspace_id?: string;
  amount: number;
  description: string;
  category: ExpenseCategory;
  date: ISODateString;
  source: TransactionSource;
  created_at?: ISODateString;
}

export interface ExpenseCreateRequest {
  amount: number;
  description: string;
  category?: ExpenseCategory;
  date?: ISODateString;
  source?: TransactionSource;
  workspace_id?: string;
}

// -------------------------------------------------------------------------
// Budget & Analytics Contracts
// -------------------------------------------------------------------------

export interface BudgetStatusItem {
  category: ExpenseCategory;
  limit: number;
  spent: number;
  remaining: number;
  percent: number;
}

export interface BudgetForecastResponse {
  prediction: number;
  status: string;
  confidence?: 'Low' | 'Medium' | 'High';
}

export interface AnalyticsSummaryResponse {
  totalSpent: number;
  avgDaily: number;
  categoryData: { name: string; value: number }[];
  trendData: { date: string; amount: number }[];
  anomalies: ExpenseResponse[];
}

// -------------------------------------------------------------------------
// Goal & Ingestion Contracts
// -------------------------------------------------------------------------

export interface GoalResponse {
  id: string;
  user_id: string;
  name: string;
  target_amount: number;
  current_amount: number;
  category: string;
  deadline?: ISODateString | null;
  predicted_completion_date?: string | null;
  is_on_track: boolean;
}

export interface GoalInsightResponse {
  surplus: number;
  recommendations: { type: string; text: string }[];
}

export interface SmsParseResponse {
  amount: number;
  description: string;
  category: ExpenseCategory;
  source: 'SMS';
}

export interface OcrReceiptResponse {
  amount: number;
  description: string;
  category: ExpenseCategory;
  image_url?: string | null;
  source: 'OCR';
}

export interface ChatMessageResponse {
  reply: string;
}

// -------------------------------------------------------------------------
// V1 Financial Account & Operational Transaction Contracts
// -------------------------------------------------------------------------

export type AccountType =
  | 'cash'
  | 'bank'
  | 'savings'
  | 'current'
  | 'credit_card'
  | 'loan'
  | 'wallet'
  | 'investment'
  | 'other';

export interface AccountCreateRequest {
  name: string;
  account_type: AccountType | string;
  currency?: CurrencyCode;
  institution_name?: string | null;
  masked_identifier?: string | null;
}

export interface AccountResponse {
  id: UUID;
  workspace_id: UUID;
  name: string;
  account_type: AccountType | string;
  currency: CurrencyCode;
  institution_name?: string | null;
  masked_identifier?: string | null;
  status: string;
  created_at: ISODateString;
}

export interface TransactionCreateRequest {
  account_id: UUID;
  amount: string;
  currency?: CurrencyCode;
  transaction_type: 'income' | 'expense' | 'transfer' | 'refund' | 'repayment' | 'adjustment';
  transaction_date: string;
  description: string;
  merchant_name?: string | null;
  category_id?: UUID | null;
  external_transaction_id?: string | null;
  is_ai_predicted?: boolean;
  ai_confidence?: number | null;
}

export interface TransactionResponse {
  id: UUID;
  workspace_id: UUID;
  account_id: UUID;
  amount: string;
  currency: CurrencyCode;
  transaction_type: string;
  transaction_date: string;
  settlement_date?: string | null;
  description: string;
  merchant_name?: string | null;
  category_id?: UUID | null;
  status: string;
  external_transaction_id?: string | null;
  is_ai_predicted: boolean;
  ai_confidence?: number | null;
  created_at: ISODateString;
}

