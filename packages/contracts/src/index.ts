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
  | 'salary'
  | 'fixed_deposit'
  | 'recurring_deposit'
  | 'credit_card'
  | 'loan'
  | 'wallet'
  | 'digital_wallet'
  | 'investment'
  | 'business_cash'
  | 'business_bank'
  | 'business_current'
  | 'business_credit_card'
  | 'petty_cash'
  | 'loan_account'
  | 'other_business'
  | 'other';

export type AccountStatus = 'active' | 'inactive' | 'archived' | 'closed';

export type BalanceType = 'book' | 'available' | 'provider_reported' | 'liability' | 'opening';

export interface BalanceBreakdown {
  currency: CurrencyCode | string;
  book_balance: string;
  book_balance_paise: number;
  available_balance?: string | null;
  available_balance_paise?: number | null;
  provider_reported_balance?: string | null;
  provider_reported_balance_paise?: number | null;
  provider_reported_at?: ISODateString | null;
  outstanding_liability?: string | null;
  outstanding_liability_paise?: number | null;
  pending_amount: string;
  pending_amount_paise: number;
  opening_balance: string;
  opening_balance_paise: number;
  opening_balance_date?: string | null;
  opening_balance_source?: string | null;
  credit_limit?: string | null;
  credit_limit_paise?: number | null;
  available_credit?: string | null;
  available_credit_paise?: number | null;
  statement_balance?: string | null;
  statement_balance_paise?: number | null;
  minimum_due?: string | null;
  minimum_due_paise?: number | null;
  due_date?: string | null;
  original_principal?: string | null;
  original_principal_paise?: number | null;
  outstanding_principal?: string | null;
  outstanding_principal_paise?: number | null;
  interest_rate?: number | null;
  repayment_amount?: string | null;
  repayment_amount_paise?: number | null;
}

export interface AccountBalanceSnapshotResponse {
  id: UUID;
  account_id: UUID;
  workspace_id: UUID;
  balance_type: BalanceType | string;
  balance_amount: string;
  balance_paise: number;
  currency: CurrencyCode | string;
  effective_at: ISODateString;
  source: string;
  source_reference?: string | null;
  reconciliation_status: string;
  created_at: ISODateString;
}

export interface AccountBalanceSnapshotCreateRequest {
  balance_type: BalanceType | string;
  balance_amount: string;
  currency?: CurrencyCode | string;
  effective_at?: ISODateString;
  source?: string;
  source_reference?: string;
  reconciliation_status?: string;
}

export interface AccountCreateRequest {
  name: string;
  account_type: AccountType | string;
  account_subtype?: string | null;
  description?: string | null;
  currency?: CurrencyCode | string;
  institution_name?: string | null;
  masked_identifier?: string | null;
  opening_date?: string | null;
  opening_balance?: string;
  opening_balance_source?: string;
  credit_limit?: string | null;
  due_date?: string | null;
  minimum_due?: string | null;
  statement_balance?: string | null;
  initial_liability?: string | null;
  outstanding_liability?: string | null;
  original_principal?: string | null;
  outstanding_principal?: string | null;
  interest_rate?: number | null;
  repayment_amount?: string | null;
  loan_due_date?: string | null;
  provider_name?: string | null;
  provider_account_id?: string | null;
  connection_id?: string | null;
  metadata?: Record<string, unknown>;
}

export interface AccountUpdateRequest {
  name?: string;
  account_subtype?: string | null;
  description?: string | null;
  institution_name?: string | null;
  masked_identifier?: string | null;
  credit_limit?: string | null;
  minimum_due?: string | null;
  due_date?: string | null;
  metadata?: Record<string, unknown>;
}

export interface AccountCloseRequest {
  closing_date: string;
  closing_notes?: string;
}

export interface AccountResponse {
  id: UUID;
  workspace_id: UUID;
  name: string;
  account_type: AccountType | string;
  account_subtype?: string | null;
  description?: string | null;
  currency: CurrencyCode | string;
  institution_name?: string | null;
  masked_identifier?: string | null;
  status: AccountStatus | string;
  opening_date?: string | null;
  closing_date?: string | null;
  created_at: ISODateString;
  updated_at: ISODateString;
  current_book_balance: string;
  current_book_balance_paise: number;
  available_balance?: string | null;
  available_balance_paise?: number | null;
  provider_reported_balance?: string | null;
  provider_reported_balance_paise?: number | null;
  provider_reported_at?: ISODateString | null;
  outstanding_liability?: string | null;
  outstanding_liability_paise?: number | null;
  pending_amount: string;
  pending_amount_paise: number;
  credit_limit?: string | null;
  available_credit?: string | null;
  due_date?: string | null;
  interest_rate?: number | null;
  repayment_amount?: string | null;
  provider_name?: string | null;
  connection_status?: string | null;
  last_synced_at?: ISODateString | null;
  source_metadata?: Record<string, unknown>;
  balances: BalanceBreakdown;
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

