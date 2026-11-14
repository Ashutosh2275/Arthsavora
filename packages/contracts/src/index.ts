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

export interface LegacyGoalResponse {
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

export type TransactionDirection = 'inflow' | 'outflow' | 'neutral';

export type TransactionStatus =
  | 'pending'
  | 'posted'
  | 'failed'
  | 'cancelled'
  | 'reversed'
  | 'DRAFT'
  | 'PENDING'
  | 'POSTED'
  | 'RECONCILED'
  | 'REVERSED';

export type TransactionSourceType =
  | 'manual'
  | 'csv_import'
  | 'pdf_import'
  | 'bank_feed'
  | 'account_aggregator'
  | 'credit_card_statement'
  | 'ocr'
  | 'internal_adjustment'
  | 'system';

export type TransactionType =
  | 'income'
  | 'expense'
  | 'transfer'
  | 'refund'
  | 'reversal'
  | 'adjustment'
  | 'deposit'
  | 'withdrawal'
  | 'interest'
  | 'bank_fee'
  | 'tax'
  | 'credit_card_purchase'
  | 'credit_card_payment'
  | 'credit_card_refund'
  | 'credit_card_fee'
  | 'credit_card_interest'
  | 'loan_disbursal'
  | 'loan_principal_repayment'
  | 'loan_interest_payment'
  | 'loan_fee'
  | 'investment_contribution'
  | 'investment_withdrawal'
  | 'dividend'
  | 'interest_income'
  | 'investment_fee'
  | 'cash_transaction'
  | 'unknown';

export interface TransactionCreateRequest {
  account_id: UUID;
  amount: string;
  currency?: CurrencyCode | string;
  transaction_type: TransactionType | string;
  direction?: TransactionDirection;
  transaction_date: string;
  settlement_date?: string | null;
  description: string;
  merchant_name?: string | null;
  category_id?: UUID | null;
  status?: 'posted' | 'pending';
  source_type?: TransactionSourceType | string;
  source_reference?: string | null;
  external_transaction_id?: string | null;
  related_transaction_id?: UUID | null;
  is_ai_predicted?: boolean;
  ai_confidence?: number | null;
  source_provenance?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}

export interface TransactionUpdateRequest {
  description?: string;
  merchant_name?: string | null;
  category_id?: UUID | null;
  metadata?: Record<string, unknown>;
}

export interface TransactionPostRequest {
  settlement_date?: string | null;
}

export interface TransactionCancelRequest {
  cancellation_reason?: string | null;
}

export interface TransactionReverseRequest {
  reason: string;
}

export interface TransactionRefundRequest {
  refund_amount: string;
  refund_date?: string | null;
  description?: string | null;
  external_refund_id?: string | null;
}

export interface TransferCreateRequest {
  source_account_id: UUID;
  destination_account_id: UUID;
  amount: string;
  currency?: CurrencyCode | string;
  transfer_date: string;
  description?: string;
  status?: 'posted' | 'pending';
  external_transaction_id?: string | null;
  exchange_rate?: number | null;
  destination_amount?: string | null;
  metadata?: Record<string, unknown>;
}

export interface TransferResponse {
  transfer_id: UUID;
  workspace_id: UUID;
  source_account_id: UUID;
  destination_account_id: UUID;
  amount: string;
  currency: string;
  transfer_date: string;
  status: string;
  description: string;
  source_transaction_id: UUID;
  destination_transaction_id: UUID;
  created_at: ISODateString;
}

export interface TransactionResponse {
  id: UUID;
  workspace_id: UUID;
  account_id: UUID;
  amount: string;
  amount_paise: number;
  currency: CurrencyCode | string;
  transaction_type: TransactionType | string;
  direction: TransactionDirection;
  transaction_date: string;
  settlement_date?: string | null;
  description: string;
  merchant_name?: string | null;
  category_id?: UUID | null;
  status: TransactionStatus | string;
  source_type: TransactionSourceType | string;
  source_reference?: string | null;
  external_transaction_id?: string | null;
  related_transaction_id?: UUID | null;
  original_transaction_id?: UUID | null;
  transfer_id?: UUID | null;
  created_by_id?: UUID | null;
  reversal_reason?: string | null;
  is_ai_predicted: boolean;
  ai_confidence?: number | null;
  source_provenance: Record<string, unknown>;
  metadata: Record<string, unknown>;
  created_at: ISODateString;
  updated_at: ISODateString;
}

export interface TransactionHistoryEntry {
  id: UUID;
  action: string;
  actor_id?: UUID | null;
  timestamp: ISODateString;
  details: Record<string, unknown>;
}

// -------------------------------------------------------------------------
// General Ledger & Double-Entry Accounting Contracts
// -------------------------------------------------------------------------

export type LedgerAccountType = 'asset' | 'liability' | 'equity' | 'revenue' | 'expense';
export type LedgerNormalBalance = 'debit' | 'credit';
export type JournalEntryStatus = 'draft' | 'posted' | 'reversed';
export type AccountingPeriodStatus = 'open' | 'closed';

export interface LedgerAccountResponse {
  id: UUID;
  workspace_id: UUID;
  code: string;
  name: string;
  account_type: LedgerAccountType | string;
  normal_balance: LedgerNormalBalance | string;
  sub_type?: string | null;
  description?: string | null;
  parent_id?: UUID | null;
  linked_account_id?: UUID | null;
  is_active: boolean;
  is_system: boolean;
  created_at: ISODateString;
  updated_at: ISODateString;
}

export interface LedgerAccountCreateRequest {
  code: string;
  name: string;
  account_type: LedgerAccountType | string;
  normal_balance?: LedgerNormalBalance | string;
  sub_type?: string | null;
  description?: string | null;
  parent_id?: UUID | null;
  linked_account_id?: UUID | null;
}

export interface LedgerAccountUpdateRequest {
  name?: string;
  description?: string;
  is_active?: boolean;
}

export interface AccountingPeriodResponse {
  id: UUID;
  workspace_id: UUID;
  fiscal_year: string;
  period_number: number;
  name: string;
  start_date: string;
  end_date: string;
  status: AccountingPeriodStatus | string;
  closed_at?: ISODateString | null;
  closed_by_id?: UUID | null;
  created_at: ISODateString;
  updated_at: ISODateString;
}

export interface AccountingPeriodCreateRequest {
  fiscal_year: string;
  period_number: number;
  name: string;
  start_date: string;
  end_date: string;
}

export interface JournalLineResponse {
  id: UUID;
  journal_entry_id: UUID;
  ledger_account_id: UUID;
  line_number: number;
  entry_type: 'debit' | 'credit';
  amount: string;
  amount_paise: number;
  currency: string;
  description?: string | null;
  financial_account_id?: UUID | null;
  counterparty_name?: string | null;
  ledger_account_code?: string | null;
  ledger_account_name?: string | null;
}

export interface JournalLineCreateRequest {
  ledger_account_id: UUID;
  entry_type: 'debit' | 'credit';
  amount: string;
  amount_paise?: number;
  currency?: string;
  description?: string | null;
  financial_account_id?: UUID | null;
  counterparty_name?: string | null;
}

export interface JournalEntryResponse {
  id: UUID;
  workspace_id: UUID;
  entry_number: string;
  entry_date: string;
  posting_date?: ISODateString | null;
  status: JournalEntryStatus | string;
  description: string;
  source_type: string;
  source_id?: UUID | null;
  reversal_of_entry_id?: UUID | null;
  reversal_reason?: string | null;
  accounting_period_id?: UUID | null;
  created_by?: UUID | null;
  posted_by_id?: UUID | null;
  metadata: Record<string, unknown>;
  lines: JournalLineResponse[];
  total_debits: string;
  total_credits: string;
  is_balanced: boolean;
  created_at: ISODateString;
  updated_at: ISODateString;
}

export interface JournalEntryCreateRequest {
  entry_number?: string;
  entry_date: string;
  description: string;
  source_type?: string;
  lines: JournalLineCreateRequest[];
  metadata?: Record<string, unknown>;
}

export interface JournalEntryReverseRequest {
  reason: string;
  reversal_number?: string;
}

export interface JournalListResponse {
  items: JournalEntryResponse[];
  total: number;
  limit: number;
  offset: number;
}

export interface AccountBalanceResponse {
  account_id: string;
  code: string;
  name: string;
  account_type: string;
  normal_balance: string;
  total_debits: string;
  total_credits: string;
  total_debits_paise: number;
  total_credits_paise: number;
  net_balance: string;
  net_balance_paise: number;
}

export interface TrialBalanceEntry {
  account_id: string;
  code: string;
  name: string;
  account_type: string;
  normal_balance: string;
  debit_balance: string;
  credit_balance: string;
  debit_balance_paise: number;
  credit_balance_paise: number;
}

export interface TrialBalanceResponse {
  as_of_date: string;
  is_balanced: boolean;
  total_debits: string;
  total_credits: string;
  total_debits_paise: number;
  total_credits_paise: number;
  difference: string;
  difference_paise: number;
  entries: TrialBalanceEntry[];
}

// -------------------------------------------------------------------------
// Statement Ingestion & Data Acquisition Contracts
// -------------------------------------------------------------------------

export type ImportStatus =
  | 'uploaded'
  | 'validating'
  | 'processing'
  | 'awaiting_review'
  | 'confirmed'
  | 'partially_confirmed'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | 'expired';

export type ImportSourceType =
  | 'csv'
  | 'xlsx'
  | 'pdf_statement'
  | 'credit_card_statement'
  | 'manual';

export type SourceFormat = 'csv' | 'xlsx' | 'pdf_text' | 'pdf_ocr' | 'manual';
export type ValidationStatus = 'valid' | 'invalid' | 'ambiguous' | 'duplicate';
export type DuplicateStatus = 'none' | 'exact' | 'probable';
export type ReviewStatus = 'pending' | 'accepted' | 'rejected' | 'edited';

export interface ImportCandidateResponse {
  id: string;
  import_batch_id: string;
  workspace_id: string;
  account_id?: string | null;
  source_row_number: number;
  raw_data: Record<string, unknown>;
  normalized_data: {
    transaction_date?: string | null;
    description?: string | null;
    amount?: string | null;
    amount_paise?: number | null;
    direction?: string | null;
    transaction_type?: string | null;
    currency?: string | null;
    reference_number?: string | null;
    balance?: string | null;
    balance_paise?: number | null;
  };
  validation_status: ValidationStatus;
  validation_errors: string[];
  duplicate_status: DuplicateStatus;
  duplicate_match_id?: string | null;
  duplicate_reason?: string | null;
  confidence_score: string | number;
  review_status: ReviewStatus;
  selected_for_import: boolean;
  created_transaction_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ImportCandidateUpdateRequest {
  selected_for_import?: boolean;
  review_status?: ReviewStatus;
  description?: string;
  transaction_date?: string;
  amount?: number | string;
  direction?: string;
  transaction_type?: string;
  category_id?: string;
}

export interface ImportBatchResponse {
  id: string;
  import_job_id: string;
  workspace_id: string;
  source_format: SourceFormat;
  sheet_name?: string | null;
  row_count: number;
  valid_row_count: number;
  invalid_row_count: number;
  duplicate_count: number;
  processing_status: string;
  column_mapping: Record<string, string>;
  opening_balance?: string | null;
  closing_balance?: string | null;
  calculated_closing_balance?: string | null;
  reconciliation_difference?: string | null;
  metadata_payload: Record<string, unknown>;
  created_at: string;
}

export interface ImportJobSummary {
  id: string;
  workspace_id: string;
  user_id: string;
  account_id?: string | null;
  source_type: ImportSourceType;
  original_filename?: string | null;
  file_size?: number | null;
  mime_type?: string | null;
  status: ImportStatus;
  total_records: number;
  valid_records: number;
  invalid_records: number;
  duplicate_records: number;
  imported_records: number;
  error_summary?: string | null;
  created_at: string;
  completed_at?: string | null;
}

export interface ImportUploadResponse {
  job_id: string;
  batch_id: string;
  status: ImportStatus;
  source_type: ImportSourceType;
  original_filename?: string | null;
  total_records: number;
  valid_records: number;
  invalid_records: number;
  duplicate_records: number;
  available_sheets: string[];
  reconciliation: {
    opening_balance?: string | null;
    closing_balance?: string | null;
    calculated_closing_balance?: string | null;
    difference?: string | null;
    is_reconciled?: boolean | null;
  };
  candidates_preview: {
    id: string;
    row: number;
    date?: string | null;
    description?: string | null;
    amount?: string | null;
    direction?: string | null;
    status: string;
    duplicate: string;
    selected: boolean;
  }[];
}

export interface ImportConfirmRequest {
  target_account_id?: string | null;
}

export interface ImportConfirmResponse {
  job_id: string;
  status: ImportStatus;
  imported_count: number;
  created_transaction_ids: string[];
  completed_at?: string | null;
}

export interface ImportReconciliationReport {
  batch_id: string;
  opening_balance?: string | null;
  closing_balance?: string | null;
  total_inflows: string;
  total_outflows: string;
  calculated_closing_balance?: string | null;
  difference?: string | null;
  is_reconciled: boolean;
  details: Record<string, unknown>;
}

export interface ImportJobListResponse {
  items: ImportJobSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface ImportCandidateListResponse {
  items: ImportCandidateResponse[];
  total: number;
  limit: number;
  offset: number;
}

// ===========================================================================
// Transaction Intelligence & Categorization Types
// ===========================================================================

export type ConfidenceBand = 'high' | 'medium' | 'low' | 'unknown';
export type ClassificationMethod = 'system_rule' | 'user_rule' | 'merchant_alias' | 'ml_model' | 'manual';
export type FeedbackAction = 'accept' | 'correct_category' | 'correct_merchant' | 'mark_unknown' | 'create_rule';

export interface CategoryCreateRequest {
  name: string;
  category_type: string;
  parent_id?: string | null;
  slug?: string | null;
  description?: string | null;
  icon?: string | null;
  color?: string | null;
  workspace_type?: string;
  display_order?: number;
}

export interface CategoryUpdateRequest {
  name?: string;
  parent_id?: string | null;
  description?: string | null;
  icon?: string | null;
  color?: string | null;
  status?: string;
  workspace_type?: string;
  display_order?: number;
}

export interface CategoryResponse {
  id: string;
  workspace_id?: string | null;
  parent_id?: string | null;
  name: string;
  slug: string;
  category_type: string;
  description?: string | null;
  icon?: string | null;
  color?: string | null;
  is_system: boolean;
  status: string;
  workspace_type: string;
  display_order: number;
  created_at: string;
  updated_at: string;
}

export interface CategoryTreeResponse extends CategoryResponse {
  children: CategoryTreeResponse[];
}

export interface MerchantAliasResponse {
  id: string;
  alias: string;
  normalized_alias: string;
  match_type: string;
  confidence: number;
}

export interface MerchantResponse {
  id: string;
  workspace_id?: string | null;
  canonical_name: string;
  slug: string;
  default_category_id?: string | null;
  merchant_type: string;
  website?: string | null;
  logo_url?: string | null;
  is_verified: boolean;
  status: string;
  aliases: MerchantAliasResponse[];
}

export interface RuleCreateRequest {
  name: string;
  conditions: Record<string, unknown>;
  suggested_category_id: string;
  suggested_merchant_id?: string | null;
  priority?: number;
  is_enabled?: boolean;
  rule_scope?: string;
}

export interface RuleUpdateRequest {
  name?: string;
  conditions?: Record<string, unknown>;
  suggested_category_id?: string;
  suggested_merchant_id?: string | null;
  priority?: number;
  is_enabled?: boolean;
}

export interface RuleResponse {
  id: string;
  workspace_id?: string | null;
  name: string;
  priority: number;
  is_enabled: boolean;
  rule_scope: string;
  conditions: Record<string, unknown>;
  suggested_category_id: string;
  suggested_category_name?: string | null;
  suggested_merchant_id?: string | null;
  suggested_merchant_name?: string | null;
  created_at: string;
}

export interface ClassificationResponse {
  classification_id: string;
  workspace_id: string;
  transaction_id: string;
  original_description: string;
  normalized_description?: string | null;
  merchant_name?: string | null;
  suggested_category_id: string;
  suggested_category_name: string;
  confidence_score: number;
  confidence_band: ConfidenceBand | string;
  method: ClassificationMethod | string;
  model_version: string;
  explanation: string;
  status: string;
  created_at?: string | null;
}

export interface BatchCategorizeRequest {
  transaction_ids: string[];
  force_reclassify?: boolean;
}

export interface BatchCategorizeResponse {
  total_requested: number;
  categorized_count: number;
  results: ClassificationResponse[];
}

export interface PreviewSuggestRequest {
  description: string;
  direction?: string;
  amount_paise?: number | null;
}

export interface PreviewSuggestResponse {
  normalized_description: string;
  merchant_candidate?: string | null;
  payment_channel: string;
  suggested_category_id?: string | null;
  suggested_category_name: string;
  confidence_score: number;
  confidence_band: ConfidenceBand | string;
  method: string;
  explanation: string;
}

export interface FeedbackSubmitRequest {
  action: FeedbackAction | string;
  confirmed_category_id?: string | null;
  confirmed_merchant_name?: string | null;
  feedback_reason?: string | null;
  create_rule?: boolean;
  rule_name?: string | null;
}

export interface FeedbackResponse {
  feedback_id: string;
  workspace_id: string;
  transaction_id: string;
  action: string;
  confirmed_category_id?: string | null;
  confirmed_merchant_name?: string | null;
  created_rule_id?: string | null;
  status: string;
}

// -------------------------------------------------------------------------
// Prompt 13: Financial Analytics & Dashboard Intelligence Contracts
// -------------------------------------------------------------------------

export type PeriodGrouping = 'day' | 'week' | 'month' | 'quarter' | 'financial_year';
export type ReportType = 'overview' | 'cash_flow' | 'categories' | 'merchants' | 'net_worth';
export type FinancialSentiment = 'favorable' | 'unfavorable' | 'neutral';

export interface DataQualityIndicator {
  uncategorized_count: number;
  uncategorized_amount_paise: number;
  uncategorized_amount: number;
  excluded_transfers_count: number;
  excluded_transfers_amount_paise: number;
  excluded_transfers_amount: number;
  excluded_pending_count: number;
  excluded_pending_amount_paise: number;
  excluded_pending_amount: number;
}

export interface FinancialOverviewResponse {
  workspace_id: string;
  currency: string;
  start_date: string;
  end_date: string;
  total_income_paise: number;
  total_income: number;
  gross_expenses_paise: number;
  refunds_paise: number;
  total_expenses_paise: number;
  total_expenses: number;
  net_cash_flow_paise: number;
  net_cash_flow: number;
  savings_paise: number;
  savings: number;
  savings_rate_percentage: number;
  transaction_count: number;
  average_daily_spend_paise: number;
  average_daily_spend: number;
  days_in_period: number;
  data_quality: DataQualityIndicator;
}

export interface CashFlowTrendPoint {
  period_start: string;
  period_label: string;
  income_paise: number;
  income: number;
  expenses_paise: number;
  expenses: number;
  net_cash_flow_paise: number;
  net_cash_flow: number;
  cumulative_cash_flow_paise: number;
  cumulative_cash_flow: number;
  transaction_count: number;
}

export interface CashFlowTrendsResponse {
  currency: string;
  grouping: PeriodGrouping;
  start_date: string;
  end_date: string;
  trends: CashFlowTrendPoint[];
}

export interface CategorySpendingItem {
  category_id?: string | null;
  category_name: string;
  category_slug: string;
  icon: string;
  color: string;
  is_system: boolean;
  is_uncategorized: boolean;
  total_amount_paise: number;
  total_amount: number;
  percentage_of_total: number;
  transaction_count: number;
}

export interface CategorySpendingResponse {
  direction: string;
  currency: string;
  total_spend_paise: number;
  total_spend: number;
  categories: CategorySpendingItem[];
}

export interface MerchantSpendingItem {
  merchant_name: string;
  total_amount_paise: number;
  total_amount: number;
  percentage_of_total: number;
  transaction_count: number;
  average_ticket_paise: number;
  average_ticket: number;
  last_transaction_date?: string | null;
}

export interface MerchantSpendingResponse {
  currency: string;
  total_spend_paise: number;
  total_spend: number;
  merchants: MerchantSpendingItem[];
}

export interface AssetAccountSummary {
  id: string;
  name: string;
  account_type: string;
  institution_name?: string | null;
  masked_identifier?: string | null;
  current_book_balance_paise: number;
  current_book_balance: number;
}

export interface LiabilityAccountSummary {
  id: string;
  name: string;
  account_type: string;
  institution_name?: string | null;
  masked_identifier?: string | null;
  outstanding_liability_paise: number;
  outstanding_liability: number;
  credit_limit_paise?: number | null;
  credit_limit?: number | null;
  due_date?: string | null;
}

export interface NetWorthResponse {
  workspace_id: string;
  currency: string;
  as_of_date: string;
  total_assets_paise: number;
  total_assets: number;
  total_liabilities_paise: number;
  total_liabilities: number;
  net_worth_paise: number;
  net_worth: number;
  asset_accounts: AssetAccountSummary[];
  liability_accounts: LiabilityAccountSummary[];
}

export interface PeriodMetrics {
  start_date: string;
  end_date: string;
  income_paise: number;
  income: number;
  expenses_paise: number;
  expenses: number;
  net_cash_flow_paise: number;
  net_cash_flow: number;
  savings_rate_percentage: number;
}

export interface PeriodDeltas {
  income_delta_paise: number;
  income_delta: number;
  income_percentage_delta?: number | null;
  income_sentiment: FinancialSentiment | string;
  expenses_delta_paise: number;
  expenses_delta: number;
  expenses_percentage_delta?: number | null;
  expenses_sentiment: FinancialSentiment | string;
  net_cash_flow_delta_paise: number;
  net_cash_flow_delta: number;
  net_cash_flow_percentage_delta?: number | null;
  net_cash_flow_sentiment: FinancialSentiment | string;
  savings_rate_delta_percentage: number;
  savings_rate_sentiment: FinancialSentiment | string;
}

export interface PeriodComparisonResponse {
  currency: string;
  current_period: PeriodMetrics;
  previous_period: PeriodMetrics;
  deltas: PeriodDeltas;
}

// -------------------------------------------------------------------------
// Personal Budgeting & Spending Controls Contracts (Prompt 14)
// -------------------------------------------------------------------------

export type BudgetType = 'monthly' | 'custom_period' | 'category' | 'annual' | 'flexible';
export type RecurrenceInterval = 'none' | 'monthly' | 'quarterly' | 'annual';
export type BudgetStatus = 'active' | 'archived' | 'closed';
export type BudgetWarningState = 'normal' | 'caution' | 'warning' | 'critical' | 'exceeded';

export interface BudgetAllocationCreateItem {
  category_id: UUID;
  allocated_amount_paise: number;
  warning_threshold_percentage?: number;
  notes?: string | null;
}

export interface BudgetCreateRequest {
  name: string;
  start_date: string;
  end_date: string;
  total_allocated_paise: number;
  budget_type?: BudgetType | string;
  currency?: string;
  recurrence_interval?: RecurrenceInterval | string;
  allocations?: BudgetAllocationCreateItem[];
  settings?: Record<string, any>;
}

export interface BudgetUpdateRequest {
  name?: string;
  start_date?: string;
  end_date?: string;
  total_allocated_paise?: number;
  status?: BudgetStatus | string;
  recurrence_interval?: RecurrenceInterval | string;
  settings?: Record<string, any>;
  revision_reason?: string;
}

export interface AllocationCreateRequest {
  category_id: UUID;
  allocated_amount_paise: number;
  warning_threshold_percentage?: number;
  notes?: string;
  revision_reason?: string;
}

export interface AllocationUpdateRequest {
  allocated_amount_paise?: number;
  warning_threshold_percentage?: number;
  notes?: string;
  revision_reason?: string;
}

export interface BudgetRolloverRequest {
  new_start_date?: string;
  new_end_date?: string;
  adjust_allocation_paise?: number;
}

export interface BudgetAllocationResponse {
  id: UUID;
  budget_id: UUID;
  category_id: UUID;
  category_name?: string | null;
  category_color?: string | null;
  allocated_amount_paise: number;
  allocated_amount: number | string;
  warning_threshold_percentage: number;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface BudgetRevisionResponse {
  id: UUID;
  budget_id: UUID;
  revision_number: number;
  change_type: string;
  previous_state: Record<string, any>;
  new_state: Record<string, any>;
  reason?: string | null;
  changed_by_id?: UUID | null;
  created_at: string;
}

export interface BudgetAlertResponse {
  id: UUID;
  budget_id: UUID;
  allocation_id?: UUID | null;
  category_name?: string | null;
  threshold_percentage: number;
  triggered_at_paise: number;
  triggered_at_amount: number | string;
  utilization_percentage: number;
  message: string;
  created_at: string;
}

export interface BudgetSummaryResponse {
  id: UUID;
  workspace_id: UUID;
  name: string;
  budget_type: BudgetType | string;
  currency: string;
  start_date: string;
  end_date: string;
  total_allocated_paise: number;
  total_allocated: number | string;
  recurrence_interval: RecurrenceInterval | string;
  status: BudgetStatus | string;
  allocations_count: number;
  created_at: string;
  updated_at: string;
}

export interface BudgetDetailResponse extends BudgetSummaryResponse {
  allocations: BudgetAllocationResponse[];
  settings: Record<string, any>;
}

export interface BudgetAllocationProgressResponse {
  allocation_id: UUID;
  category_id: UUID;
  category_name: string;
  category_color?: string | null;
  allocated_paise: number;
  allocated_amount: number | string;
  spent_paise: number;
  spent_amount: number | string;
  remaining_paise: number;
  remaining_amount: number | string;
  utilization_percentage: number;
  overspent: boolean;
  warning_state: BudgetWarningState | string;
  warning_threshold_percentage: number;
}

export interface BudgetLinearProjectionResponse {
  days_in_period: number;
  elapsed_days: number;
  remaining_days: number;
  daily_run_rate_paise: number;
  daily_run_rate: number | string;
  projected_period_end_spend_paise: number;
  projected_period_end_spend: number | string;
  projected_variance_paise: number;
  projected_variance: number | string;
  projected_overspent: boolean;
  methodology: string;
  assumptions: string;
}

export interface BudgetProgressResponse {
  budget_id: UUID;
  name: string;
  currency: string;
  start_date: string;
  end_date: string;
  as_of_date: string;
  total_allocated_paise: number;
  total_allocated_amount: number | string;
  total_spent_paise: number;
  total_spent_amount: number | string;
  remaining_paise: number;
  remaining_amount: number | string;
  utilization_percentage: number;
  overspent: boolean;
  warning_state: BudgetWarningState | string;
  period_days: number;
  elapsed_days: number;
  remaining_days: number;
  period_elapsed_percentage: number;
  linear_projection: BudgetLinearProjectionResponse;
  allocations: BudgetAllocationProgressResponse[];
  unallocated_capacity_paise: number;
  unallocated_capacity_amount: number | string;
  new_alerts_triggered: number;
}

// -------------------------------------------------------------------------
// Financial Savings Goals Contracts (Prompt 14)
// -------------------------------------------------------------------------

export type GoalType =
  | 'emergency_fund'
  | 'education'
  | 'travel'
  | 'vehicle'
  | 'home'
  | 'debt_repayment'
  | 'personal_savings'
  | 'custom';

export type GoalStatus = 'active' | 'completed' | 'paused' | 'archived';
export type GoalPriority = 'low' | 'medium' | 'high';
export type GoalActivityType =
  | 'contribution'
  | 'withdrawal'
  | 'reversal'
  | 'transfer_in'
  | 'transfer_out';

export interface GoalCreateRequest {
  name: string;
  target_amount_paise: number;
  goal_type?: GoalType | string;
  currency?: string;
  start_date?: string;
  target_date?: string | null;
  priority?: GoalPriority | string;
  color?: string;
  icon?: string;
  description?: string;
  metadata_payload?: Record<string, any>;
}

export interface GoalUpdateRequest {
  name?: string;
  target_amount_paise?: number;
  target_date?: string | null;
  status?: GoalStatus | string;
  priority?: GoalPriority | string;
  color?: string;
  icon?: string;
  description?: string;
  metadata_payload?: Record<string, any>;
}

export interface GoalActivityRequest {
  amount_paise: number;
  transaction_id?: UUID;
  notes?: string;
}

export interface GoalActivityResponse {
  id: UUID;
  goal_id: UUID;
  workspace_id: UUID;
  activity_type: GoalActivityType | string;
  amount_paise: number;
  amount: number | string;
  currency: string;
  resulting_balance_paise: number;
  transaction_id?: UUID | null;
  notes?: string | null;
  performed_by_id?: UUID | null;
  created_at: string;
}

export interface GoalResponse {
  id: UUID;
  workspace_id: UUID;
  name: string;
  description?: string | null;
  goal_type: GoalType | string;
  currency: string;
  target_amount_paise: number;
  target_amount: number | string;
  current_amount_paise: number;
  current_amount: number | string;
  start_date: string;
  target_date?: string | null;
  status: GoalStatus | string;
  priority: GoalPriority | string;
  color?: string | null;
  icon?: string | null;
  created_by_id?: UUID | null;
  metadata_payload: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface GoalProgressResponse {
  goal_id: UUID;
  name: string;
  goal_type: GoalType | string;
  currency: string;
  status: GoalStatus | string;
  priority: GoalPriority | string;
  color?: string | null;
  icon?: string | null;
  target_amount_paise: number;
  target_amount: number | string;
  current_amount_paise: number;
  current_amount: number | string;
  start_date: string;
  target_date?: string | null;
  as_of_date: string;
  remaining_paise: number;
  remaining_amount: number | string;
  completion_percentage: number;
  is_completed: boolean;
  days_remaining?: number | null;
  required_monthly_savings_paise?: number | null;
  required_monthly_savings_amount?: number | string | null;
}

// -------------------------------------------------------------------------
// Recurring Transactions, Subscriptions & Cash-Flow Commitments Contracts
// -------------------------------------------------------------------------

export type RecurringDirection = 'inflow' | 'outflow';
export type RecurringFrequency = 'daily' | 'weekly' | 'biweekly' | 'monthly' | 'quarterly' | 'semi_annual' | 'annual' | 'custom';
export type EndOfMonthPolicy = 'last_day' | 'closest_before' | 'skip';
export type RecurringStatus = 'active' | 'paused' | 'cancelled' | 'completed';
export type OccurrenceStatus = 'scheduled' | 'upcoming' | 'due' | 'matched' | 'confirmed' | 'skipped' | 'cancelled' | 'overdue';
export type SubscriptionStatus = 'active' | 'trial' | 'paused' | 'cancelled' | 'expired' | 'unknown';
export type BillingFrequency = 'weekly' | 'monthly' | 'quarterly' | 'semi_annual' | 'annual';
export type ReminderType = 'upcoming_payment' | 'upcoming_renewal' | 'trial_ending' | 'payment_overdue' | 'cancellation_deadline';
export type SuggestionStatus = 'pending' | 'confirmed' | 'dismissed';

export interface RecurringDefinitionCreateRequest {
  name: string;
  description?: string;
  direction?: RecurringDirection;
  transaction_type?: string;
  expected_amount_paise: number;
  is_variable_amount?: boolean;
  currency?: string;
  category_id?: UUID;
  merchant_id?: UUID;
  merchant_name?: string;
  account_id?: UUID;
  frequency?: RecurringFrequency;
  interval?: number;
  day_of_month?: number;
  day_of_week?: number;
  end_of_month_policy?: EndOfMonthPolicy;
  start_date: string;
  end_date?: string;
  timezone?: string;
}

export interface RecurringDefinitionUpdateRequest {
  name?: string;
  description?: string;
  expected_amount_paise?: number;
  is_variable_amount?: boolean;
  category_id?: UUID;
  merchant_id?: UUID;
  merchant_name?: string;
  account_id?: UUID;
  frequency?: RecurringFrequency;
  interval?: number;
  day_of_month?: number;
  day_of_week?: number;
  end_of_month_policy?: EndOfMonthPolicy;
  end_date?: string;
  next_expected_date?: string;
  status?: RecurringStatus;
}

export interface RecurringDefinitionResponse {
  id: UUID;
  workspace_id: UUID;
  name: string;
  description?: string | null;
  direction: RecurringDirection | string;
  transaction_type: string;
  expected_amount_paise: number;
  expected_amount: number | string;
  is_variable_amount: boolean;
  currency: string;
  category_id?: UUID | null;
  category_name?: string | null;
  merchant_id?: UUID | null;
  merchant_name?: string | null;
  account_id?: UUID | null;
  account_name?: string | null;
  frequency: RecurringFrequency | string;
  interval: number;
  day_of_month?: number | null;
  day_of_week?: number | null;
  end_of_month_policy: string;
  start_date: string;
  end_date?: string | null;
  next_expected_date: string;
  timezone: string;
  status: RecurringStatus | string;
  normalized_monthly_paise: number;
  normalized_annual_paise: number;
  created_at: string;
  updated_at: string;
}

export interface OccurrenceMatchRequest {
  transaction_id: UUID;
  notes?: string;
}

export interface OccurrenceConfirmRequest {
  notes?: string;
}

export interface OccurrenceSkipRequest {
  reason?: string;
}

export interface OccurrenceResponse {
  id: UUID;
  workspace_id: UUID;
  recurring_definition_id: UUID;
  recurring_name?: string | null;
  direction?: string | null;
  expected_date: string;
  expected_amount_paise: number;
  expected_amount: number | string;
  currency: string;
  status: OccurrenceStatus | string;
  matched_transaction_id?: UUID | null;
  matched_amount_paise?: number | null;
  matched_amount?: number | string | null;
  amount_variance_paise?: number | null;
  match_confidence?: number | null;
  notes?: string | null;
  generated_at: string;
  confirmed_at?: string | null;
  updated_at: string;
}

export interface SubscriptionCreateRequest {
  name: string;
  provider_name?: string;
  merchant_id?: UUID;
  category_id?: UUID;
  expected_amount_paise: number;
  currency?: string;
  billing_frequency?: BillingFrequency;
  billing_cycle_interval?: number;
  start_date: string;
  next_billing_date: string;
  renewal_date?: string;
  trial_end_date?: string;
  account_id?: UUID;
  payment_method_display?: string;
  is_variable_pricing?: boolean;
  notes?: string;
  create_recurring_definition?: boolean;
}

export interface SubscriptionUpdateRequest {
  name?: string;
  provider_name?: string;
  expected_amount_paise?: number;
  billing_frequency?: BillingFrequency;
  billing_cycle_interval?: number;
  next_billing_date?: string;
  renewal_date?: string;
  trial_end_date?: string;
  cancellation_date?: string;
  status?: SubscriptionStatus;
  account_id?: UUID;
  payment_method_display?: string;
  is_variable_pricing?: boolean;
  notes?: string;
}

export interface SubscriptionResponse {
  id: UUID;
  workspace_id: UUID;
  recurring_definition_id?: UUID | null;
  name: string;
  provider_name?: string | null;
  merchant_id?: UUID | null;
  merchant_name?: string | null;
  category_id?: UUID | null;
  category_name?: string | null;
  expected_amount_paise: number;
  expected_amount: number | string;
  currency: string;
  billing_frequency: BillingFrequency | string;
  billing_cycle_interval: number;
  start_date: string;
  next_billing_date: string;
  renewal_date?: string | null;
  trial_end_date?: string | null;
  cancellation_date?: string | null;
  account_id?: UUID | null;
  account_name?: string | null;
  payment_method_display?: string | null;
  status: SubscriptionStatus | string;
  is_variable_pricing: boolean;
  notes?: string | null;
  estimated_monthly_paise: number;
  estimated_annual_paise: number;
  created_at: string;
  updated_at: string;
}

export interface RecurringReminderResponse {
  id: UUID;
  workspace_id: UUID;
  occurrence_id?: UUID | null;
  recurring_definition_id?: UUID | null;
  subscription_id?: UUID | null;
  reminder_type: ReminderType | string;
  days_before: number;
  scheduled_for: string;
  notification_channel: string;
  is_sent: boolean;
  sent_at?: string | null;
  is_read: boolean;
  message: string;
  created_at: string;
}

export interface RecurringDetectRequest {
  lookback_days?: number;
  as_of_date?: string;
}

export interface RecurringSuggestionResponse {
  id: UUID;
  workspace_id: UUID;
  merchant_id?: UUID | null;
  merchant_name: string;
  normalized_description: string;
  direction: string;
  suggested_frequency: string;
  suggested_amount_paise: number;
  suggested_amount: number | string;
  min_amount_paise: number;
  max_amount_paise: number;
  currency: string;
  category_id?: UUID | null;
  confidence_score: number;
  evidence_count: number;
  evidence_summary: Record<string, any>;
  first_seen_date: string;
  last_seen_date: string;
  estimated_next_date: string;
  status: SuggestionStatus | string;
  dismissed_reason?: string | null;
  created_at: string;
}

export interface SuggestionConfirmRequest {
  name?: string;
  category_id?: UUID;
  account_id?: UUID;
  adjusted_amount_paise?: number;
  adjusted_frequency?: RecurringFrequency;
  is_subscription?: boolean;
}

export interface SuggestionDismissRequest {
  reason?: string;
}

export interface CommitmentBreakdownByType {
  type_name: string;
  count: number;
  total_amount_paise: number;
  total_amount: number | string;
}

export interface CashFlowCommitmentsResponse {
  workspace_id: UUID;
  window_days: number;
  start_date: string;
  end_date: string;
  total_expected_inflow_paise: number;
  total_expected_inflow: number | string;
  total_expected_outflow_paise: number;
  total_expected_outflow: number | string;
  net_commitment_paise: number;
  net_commitment: number | string;
  active_recurring_count: number;
  active_subscription_count: number;
  normalized_monthly_expenses_paise: number;
  normalized_monthly_expenses: number | string;
  normalized_annual_expenses_paise: number;
  normalized_annual_expenses: number | string;
  commitments_by_category: Array<{
    category_name: string;
    count: number;
    total_amount_paise: number;
    total_amount: number | string;
  }>;
  commitments_by_type: CommitmentBreakdownByType[];
  upcoming_occurrences: OccurrenceResponse[];
}

// -------------------------------------------------------------------------
// Financial Forecasting, Cash-Flow Prediction & Scenarios Contracts
// -------------------------------------------------------------------------

export interface ForecastGenerateRequest {
  horizon_days?: number;
  resolution?: string;
  preferred_model?: string | null;
  include_recurring?: boolean;
  confidence_level?: number;
}

export interface ForecastPointResponse {
  id?: UUID | null;
  forecast_date: string;
  metric_type: string;
  category_id?: UUID | null;
  category_name?: string | null;
  point_estimate_paise: number;
  point_estimate: number | string;
  lower_estimate_paise: number;
  lower_estimate: number | string;
  upper_estimate_paise: number;
  upper_estimate: number | string;
  confidence_level: number;
  is_recurring_commitment: boolean;
  breakdown_metadata?: Record<string, any>;
}

export interface CashFlowForecastResponse {
  workspace_id: UUID;
  forecast_run_id: UUID;
  horizon_days: number;
  resolution: string;
  currency: string;
  starting_balance_paise: number;
  starting_balance: number | string;
  projected_ending_balance_paise: number;
  projected_ending_balance: number | string;
  total_projected_inflow_paise: number;
  total_projected_inflow: number | string;
  total_projected_outflow_paise: number;
  total_projected_outflow: number | string;
  net_cash_flow_paise: number;
  net_cash_flow: number | string;
  model_name: string;
  model_version: string;
  data_quality_score: number;
  status: string;
  timeline: Array<{
    date: string;
    starting_balance_paise: number;
    inflow_paise: number;
    inflow_recurring_paise: number;
    outflow_paise: number;
    outflow_recurring_paise: number;
    net_cash_flow_paise: number;
    projected_balance_paise: number;
    lower_balance_paise: number;
    upper_balance_paise: number;
  }>;
  created_at: string;
}

export interface IncomeForecastResponse {
  workspace_id: UUID;
  forecast_run_id: UUID;
  horizon_days: number;
  total_expected_income_paise: number;
  total_expected_income: number | string;
  scheduled_income_paise: number;
  scheduled_income: number | string;
  estimated_discretionary_income_paise: number;
  estimated_discretionary_income: number | string;
  model_used: string;
  points: ForecastPointResponse[];
}

export interface ExpenseForecastResponse {
  workspace_id: UUID;
  forecast_run_id: UUID;
  horizon_days: number;
  total_expected_expense_paise: number;
  total_expected_expense: number | string;
  scheduled_commitments_paise: number;
  scheduled_commitments: number | string;
  discretionary_expense_paise: number;
  discretionary_expense: number | string;
  model_used: string;
  points: ForecastPointResponse[];
}

export interface CategoryForecastItem {
  category_id?: UUID | null;
  category_name: string;
  projected_amount_paise: number;
  projected_amount: number | string;
  lower_amount_paise: number;
  lower_amount: number | string;
  upper_amount_paise: number;
  upper_amount: number | string;
  historical_monthly_average_paise: number;
  historical_monthly_average: number | string;
  trend_direction: string;
}

export interface CategoryForecastResponse {
  workspace_id: UUID;
  forecast_run_id: UUID;
  horizon_days: number;
  categories: CategoryForecastItem[];
}

export interface BudgetExhaustionItem {
  budget_id: string;
  budget_name: string;
  category_id?: string | null;
  category_name?: string | null;
  total_allocated_paise: number;
  total_allocated: number | string;
  current_spend_paise: number;
  current_spend: number | string;
  remaining_paise: number;
  remaining: number | string;
  burn_rate_daily_paise: number;
  burn_rate_daily: number | string;
  utilization_pct: number;
  estimated_exhaustion_date?: string | null;
  days_to_exhaustion?: number | null;
  status: string;
}

export interface BudgetExhaustionResponse {
  workspace_id: UUID;
  as_of_date: string;
  estimates: BudgetExhaustionItem[];
}

export interface GoalTrajectoryItem {
  goal_id: string;
  goal_name: string;
  target_amount_paise: number;
  target_amount: number | string;
  current_balance_paise: number;
  current_balance: number | string;
  remaining_paise: number;
  remaining: number | string;
  target_date?: string | null;
  monthly_savings_pace_paise: number;
  monthly_savings_pace: number | string;
  projected_completion_date?: string | null;
  is_on_track: boolean;
  status: string;
}

export interface GoalTrajectoryResponse {
  workspace_id: UUID;
  as_of_date: string;
  goals: GoalTrajectoryItem[];
}

export interface ScenarioCreateRequest {
  name: string;
  description?: string;
  scenario_type?: string;
  horizon_days?: number;
  income_change_pct?: number;
  expense_change_pct?: number;
  one_time_inflows?: Array<{ date: string; amount_paise: number; description?: string }>;
  one_time_outflows?: Array<{ date: string; amount_paise: number; description?: string }>;
  monthly_savings_change_paise?: number;
}

export interface ScenarioResponse {
  id: UUID;
  workspace_id: UUID;
  name: string;
  description?: string | null;
  scenario_type: string;
  horizon_days: number;
  assumptions: Record<string, any>;
  results: Record<string, any>;
  created_at: string;
}

export interface EvaluationResponse {
  id: UUID;
  workspace_id: UUID;
  model_name: string;
  metric_type: string;
  horizon_days: number;
  mae_paise: number;
  mae: number | string;
  rmse_paise: number;
  rmse: number | string;
  wape: number;
  bias_paise: number;
  bias: number | string;
  interval_coverage?: number | null;
  sample_size: number;
  is_best_model: boolean;
  created_at: string;
}

// -----------------------------------------------------------------------------
// Financial Anomaly Detection, Fraud Signals & Risk Intelligence Contracts [17]
// -----------------------------------------------------------------------------

export type AnomalyCategory =
  | 'amount'
  | 'frequency'
  | 'merchant'
  | 'category'
  | 'timing'
  | 'account'
  | 'recurring'
  | 'duplicate'
  | 'import';

export type DetectionMethod =
  | 'deterministic_rule'
  | 'statistical_mad'
  | 'statistical_iqr'
  | 'statistical_zscore'
  | 'ml_isolation_forest'
  | 'deduplication_engine';

export type AnomalySeverity = 'informational' | 'low' | 'medium' | 'high' | 'critical';

export type AnomalyStatus =
  | 'new'
  | 'under_review'
  | 'acknowledged'
  | 'expected_activity'
  | 'dismissed'
  | 'escalated';

export type ReviewAction =
  | 'acknowledge'
  | 'mark_expected'
  | 'mark_suspicious'
  | 'dismiss'
  | 'escalate'
  | 'reopen'
  | 'create_exception';

export interface AnomalyTransactionSummary {
  id: UUID;
  transaction_date: string;
  amount_paise: number;
  amount: number | string;
  currency: string;
  direction: 'inflow' | 'outflow' | string;
  description: string;
  merchant_name?: string | null;
  category_name?: string | null;
  account_name?: string | null;
}

export interface AnomalyReviewResponse {
  id: UUID;
  anomaly_id: UUID;
  workspace_id: UUID;
  reviewer_id?: UUID | null;
  action: string;
  reason?: string | null;
  notes?: string | null;
  created_at: string;
}

export interface AnomalyDetectionResponse {
  id: UUID;
  workspace_id: UUID;
  transaction_id?: UUID | null;
  account_id?: UUID | null;
  detection_type: string;
  detection_method: string;
  severity: AnomalySeverity | string;
  risk_score: number;
  status: AnomalyStatus | string;
  explanation: string;
  evidence_metadata: Record<string, any>;
  rule_code?: string | null;
  model_version: string;
  detected_at: string;
  resolved_at?: string | null;
  resolved_by_id?: UUID | null;
  resolution_notes?: string | null;
  transaction?: AnomalyTransactionSummary | null;
  reviews?: AnomalyReviewResponse[];
}

export interface AnomalyReviewRequest {
  action: string;
  reason?: string | null;
  notes?: string | null;
  create_exception?: boolean;
  exception_expires_in_days?: number | null;
}

export interface DetectionRuleResponse {
  id: UUID;
  workspace_id?: UUID | null;
  rule_code: string;
  name: string;
  description: string;
  detection_category: string;
  severity: AnomalySeverity | string;
  threshold_config: Record<string, any>;
  is_enabled: boolean;
  version: string;
}

export interface DetectionRuleUpdateRequest {
  is_enabled?: boolean;
  severity?: string;
  threshold_config?: Record<string, any>;
}

export interface DetectionExceptionCreateRequest {
  rule_code?: string | null;
  merchant_id?: UUID | null;
  category_id?: UUID | null;
  account_id?: UUID | null;
  merchant_name_pattern?: string | null;
  max_amount_paise?: number | null;
  reason: string;
  expires_at?: string | null;
}

export interface DetectionExceptionResponse {
  id: UUID;
  workspace_id: UUID;
  rule_code?: string | null;
  merchant_id?: UUID | null;
  merchant_name?: string | null;
  category_id?: UUID | null;
  category_name?: string | null;
  account_id?: UUID | null;
  account_name?: string | null;
  merchant_name_pattern?: string | null;
  max_amount_paise?: number | null;
  max_amount?: number | string | null;
  reason: string;
  expires_at?: string | null;
  created_at: string;
}

export interface AnomalySummaryResponse {
  total_detections: number;
  open_anomalies: number;
  high_severity_anomalies: number;
  resolved_anomalies: number;
  average_risk_score: number;
}

export interface AnomalyTrendPoint {
  date: string;
  informational: number;
  low: number;
  medium: number;
  high: number;
  critical: number;
  total: number;
}

export interface AnomalyTrendsResponse {
  workspace_id: UUID;
  lookback_days: number;
  trends: AnomalyTrendPoint[];
}

export interface AnomalyScanRequest {
  lookback_days?: number;
  force_recheck?: boolean;
}

// -------------------------------------------------------------------------
// Prompt 18: AI Financial Assistant & Conversational Intelligence
// -------------------------------------------------------------------------

export type AssistantConversationStatus = 'active' | 'archived' | 'deleted';
export type AssistantMessageRole = 'user' | 'assistant' | 'system';
export type AssistantActionDraftStatus = 'pending' | 'confirmed' | 'cancelled' | 'expired';

export interface AssistantConversation {
  id: UUID;
  workspace_id: UUID;
  user_id: UUID;
  title: string;
  status: AssistantConversationStatus;
  model_provider: string;
  model_name: string;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface AssistantConversationCreateRequest {
  title?: string;
}

export interface AssistantConversationUpdateRequest {
  title?: string;
  status?: AssistantConversationStatus;
}

export interface AssistantActionDraft {
  id: UUID;
  conversation_id: UUID;
  workspace_id: UUID;
  action_type: string;
  action_summary: string;
  parameters: Record<string, any>;
  status: AssistantActionDraftStatus;
  confirmation_token: string;
  expires_at: string;
  created_at: string;
}

export interface AssistantActionConfirmRequest {
  confirmation_token: string;
}

export interface AssistantActionConfirmResponse {
  action_id: UUID;
  status: string;
  action_type: string;
  message: string;
  execution_result: Record<string, any>;
}

export interface AssistantToolCall {
  name: string;
  arguments: Record<string, any>;
}

export interface AssistantToolResult {
  tool_name: string;
  status: string;
  summary?: string;
  data?: any;
}

export interface AssistantMessage {
  id: UUID;
  conversation_id: UUID;
  workspace_id: UUID;
  role: AssistantMessageRole;
  content: string;
  intent?: string | null;
  tool_calls: Record<string, any>[];
  tool_results: Record<string, any>[];
  structured_data: Record<string, any>;
  action_draft?: AssistantActionDraft | null;
  tokens_prompt: number;
  tokens_completion: number;
  latency_ms: number;
  created_at: string;
}

export interface AssistantMessageCreateRequest {
  content: string;
}

export interface AssistantUsageSummary {
  total_requests: number;
  total_tokens: number;
  tokens_prompt: number;
  tokens_completion: number;
  estimated_cost_usd: number;
  avg_latency_ms: number;
}

// -------------------------------------------------------------------------
// Receipt Intelligence, OCR & Document Extraction Contracts (Prompt 19)
// -------------------------------------------------------------------------

export type DocumentType = 'receipt' | 'invoice' | 'bill' | 'supporting_doc';
export type DocumentStatus =
  | 'pending'
  | 'preprocessing'
  | 'processing'
  | 'extracted'
  | 'review_required'
  | 'confirmed'
  | 'rejected'
  | 'failed';
export type TransactionMatchStatus = 'exact' | 'candidate' | 'ambiguous' | 'none';
export type DocumentPaymentMethod = 'upi' | 'card' | 'cash' | 'netbanking' | 'unknown';
export type DocumentValidationStatus = 'valid' | 'warning' | 'invalid_math' | 'incomplete';

export interface DocumentLineItem {
  description: string;
  hsn_sac?: string | null;
  quantity: string;
  unit_price: string;
  unit_price_paise: number;
  tax_rate?: string | null;
  amount: string;
  amount_paise: number;
}

export interface TaxBreakdown {
  cgst: string;
  cgst_paise: number;
  sgst: string;
  sgst_paise: number;
  igst: string;
  igst_paise: number;
  total_tax: string;
  total_tax_paise: number;
  gstin?: string | null;
}

export interface StructuredReceiptData {
  merchant_name?: string | null;
  gstin?: string | null;
  receipt_date?: string | null;
  invoice_number?: string | null;
  currency: string;
  subtotal: string;
  subtotal_paise: number;
  taxes: TaxBreakdown;
  discount: string;
  discount_paise: number;
  total_amount: string;
  total_amount_paise: number;
  payment_method: string;
  payment_reference?: string | null;
  suggested_category_id?: string | null;
  suggested_category_name?: string | null;
  line_items: DocumentLineItem[];
}

export interface DocumentExtractionResult {
  id: UUID;
  document_id: UUID;
  workspace_id: UUID;
  ocr_provider: string;
  ocr_version?: string | null;
  raw_text: string;
  structured_data: StructuredReceiptData;
  field_confidences: Record<string, number>;
  overall_confidence: number | string;
  validation_status: DocumentValidationStatus;
  validation_warnings: string[];
  created_at: string;
}

export interface DocumentReviewRecord {
  id: UUID;
  document_id: UUID;
  workspace_id: UUID;
  reviewer_id?: UUID | null;
  original_data: Record<string, any>;
  corrected_data: Record<string, any>;
  review_action: string;
  notes?: string | null;
  created_at: string;
}

export interface DocumentTransactionAssociation {
  id: UUID;
  document_id: UUID;
  transaction_id: UUID;
  workspace_id: UUID;
  association_type: string;
  match_score?: number | string | null;
  match_evidence: Record<string, any>;
  created_by_id?: UUID | null;
  created_at: string;
}

export interface FinancialDocument {
  id: UUID;
  workspace_id: UUID;
  uploaded_by_id?: UUID | null;
  original_filename: string;
  file_size: number;
  mime_type: string;
  file_checksum: string;
  document_type: DocumentType;
  status: DocumentStatus;
  preprocessing_metadata: Record<string, any>;
  retention_metadata: Record<string, any>;
  extractions?: DocumentExtractionResult[];
  reviews?: DocumentReviewRecord[];
  transaction_associations?: DocumentTransactionAssociation[];
  created_at: string;
  updated_at: string;
}

export interface DocumentListResponse {
  items: FinancialDocument[];
  total: number;
  limit: number;
  offset: number;
}

export interface DocumentCorrectionRequest {
  corrected_data: Record<string, any>;
  notes?: string;
}

export interface DocumentConfirmRequest {
  account_id: UUID;
  confirmed_data?: Record<string, any>;
  notes?: string;
}

export interface DocumentMatchAssociateRequest {
  transaction_id: UUID;
  match_score?: number | string;
  notes?: string;
}

export interface TransactionMatchCandidate {
  transaction_id: UUID;
  match_status: TransactionMatchStatus;
  match_score: number | string;
  evidence: Record<string, any>;
  transaction_summary: Record<string, any>;
}

// ============================================================================
// Prompt 20: Unified Notifications & Financial Alerts Contracts
// ============================================================================

export type NotificationCategory =
  | 'transaction'
  | 'budget'
  | 'goal'
  | 'recurring'
  | 'forecast'
  | 'anomaly'
  | 'document'
  | 'assistant'
  | 'security'
  | 'system';

export type NotificationSeverity = 'info' | 'success' | 'warning' | 'critical';

export type NotificationChannel = 'in_app' | 'email' | 'web_push' | 'mobile_push';

export type DeliveryStatus =
  | 'pending'
  | 'queued'
  | 'sending'
  | 'delivered'
  | 'failed'
  | 'retry_scheduled'
  | 'cancelled';

export interface NotificationDeliveryResponse {
  id: UUID;
  channel: NotificationChannel | string;
  provider: string;
  status: DeliveryStatus | string;
  attempt_count: number;
  provider_message_reference?: string | null;
  last_attempt_at?: string | null;
  delivered_at?: string | null;
  failure_reason?: string | null;
}

export interface NotificationResponse {
  id: UUID;
  recipient_user_id: UUID;
  workspace_id?: UUID | null;
  category: NotificationCategory | string;
  event_type: string;
  title: string;
  message: string;
  severity: NotificationSeverity | string;
  related_resource_type?: string | null;
  related_resource_id?: string | null;
  action_url?: string | null;
  metadata_json: Record<string, any>;
  event_timestamp: string;
  created_at: string;
  is_read: boolean;
  read_at?: string | null;
  is_archived: boolean;
  deliveries: NotificationDeliveryResponse[];
}

export interface NotificationListResponse {
  items: NotificationResponse[];
  total: number;
  limit: number;
  offset: number;
  unread_count: number;
}

export interface UnreadCountResponse {
  unread_count: number;
}

export interface MarkReadResponse {
  success: boolean;
  affected_count: number;
}

export interface NotificationPreferenceResponse {
  id: UUID;
  user_id: UUID;
  category: string;
  channel: string;
  is_enabled: boolean;
  min_severity: string;
  quiet_hours_enabled: boolean;
  quiet_hours_start?: string | null;
  quiet_hours_end?: string | null;
  timezone: string;
  frequency: string;
  updated_at: string;
}

export interface NotificationPreferenceUpdateRequest {
  category: string;
  channel: string;
  is_enabled: boolean;
  min_severity?: string;
  quiet_hours_enabled?: boolean;
  quiet_hours_start?: string | null;
  quiet_hours_end?: string | null;
  timezone?: string;
  frequency?: string;
}

export interface PushSubscriptionResponse {
  id: UUID;
  endpoint: string;
  is_active: boolean;
  created_at: string;
}

export interface PushSubscriptionCreateRequest {
  endpoint: string;
  p256dh_key: string;
  auth_key: string;
  user_agent?: string | null;
}

// -----------------------------------------------------------------------------
// Family Finance Management & Collaborative Household Budgeting (Prompt 21)
// -----------------------------------------------------------------------------

export type FamilyRole = 'owner' | 'admin' | 'member' | 'restricted' | 'viewer';
export type AllocationMethod = 'equal' | 'fixed' | 'percentage' | 'custom';
export type AllocationStatus = 'active' | 'revised' | 'cancelled';
export type SettlementStatus = 'pending' | 'settled' | 'waived';
export type ContributionType = 'monthly' | 'fixed' | 'percentage' | 'one_time' | 'voluntary';
export type ContributionStatus = 'expected' | 'partially_paid' | 'paid' | 'overdue' | 'waived' | 'cancelled';
export type AccountShareScope = 'balance_only' | 'summary_only' | 'full_visibility';

export interface FamilyProfileDTO {
  id: UUID;
  workspace_id: UUID;
  household_name: string;
  household_currency: string;
  household_timezone: string;
  monthly_budget_start_day: number;
  default_allocation_method: AllocationMethod | string;
  contribution_reminder_day: number;
  enable_shared_budget_alerts: boolean;
  enable_contribution_reminders: boolean;
  settings: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface UpdateFamilyProfileDTO {
  household_name?: string;
  household_currency?: string;
  household_timezone?: string;
  monthly_budget_start_day?: number;
  default_allocation_method?: string;
  contribution_reminder_day?: number;
  enable_shared_budget_alerts?: boolean;
  enable_contribution_reminders?: boolean;
  settings?: Record<string, unknown>;
}

export interface FamilyMemberDTO {
  id: UUID;
  workspace_id: UUID;
  user_id: UUID;
  email: string;
  full_name: string;
  role: FamilyRole | string;
  status: string;
  joined_at: string;
}

export interface AllocationItemDTO {
  id: UUID;
  member_user_id: UUID;
  member_name?: string | null;
  assigned_share_paise: number;
  assigned_share_decimal: number;
  percentage?: number | null;
  is_paid_by: boolean;
  settlement_status: SettlementStatus | string;
  notes?: string | null;
}

export interface FamilyAllocationDTO {
  id: UUID;
  workspace_id: UUID;
  transaction_id: UUID;
  transaction_description?: string | null;
  allocation_method: AllocationMethod | string;
  total_amount_paise: number;
  total_amount_decimal: number;
  currency: string;
  status: AllocationStatus | string;
  version: number;
  notes?: string | null;
  items: AllocationItemDTO[];
  created_at: string;
}

export interface CreateAllocationDTO {
  transaction_id: UUID;
  allocation_method: AllocationMethod | string;
  member_user_ids?: UUID[];
  member_shares_paise?: Record<string, number>;
  member_percentages?: Record<string, number>;
  payer_user_id?: UUID | null;
  notes?: string | null;
}

export interface FamilyContributionDTO {
  id: UUID;
  workspace_id: UUID;
  member_user_id: UUID;
  member_name?: string | null;
  period: string;
  contribution_type: ContributionType | string;
  expected_amount_paise: number;
  expected_amount_decimal: number;
  paid_amount_paise: number;
  paid_amount_decimal: number;
  currency: string;
  due_date?: string | null;
  status: ContributionStatus | string;
  notes?: string | null;
  created_at: string;
}

export interface RecordContributionDTO {
  member_user_id: UUID;
  period: string;
  contribution_type?: ContributionType | string;
  expected_amount_paise?: number;
  paid_amount_paise?: number;
  due_date?: string | null;
  recorded_transaction_id?: UUID | null;
  notes?: string | null;
}

export interface MemberSettlementDTO {
  member_user_id: UUID;
  full_name: string;
  email: string;
  role: string;
  total_expenses_paid_paise: number;
  total_expenses_paid_decimal: number;
  total_contributions_paid_paise: number;
  total_contributions_paid_decimal: number;
  total_allocated_share_paise: number;
  total_allocated_share_decimal: number;
  net_position_paise: number;
  net_position_decimal: number;
  currency: string;
  status: 'surplus' | 'deficit' | 'settled';
}

export interface SettlementRecommendationDTO {
  from_member_id: UUID;
  from_member_name: string;
  to_member_id: UUID;
  to_member_name: string;
  amount_paise: number;
  amount_decimal: number;
  currency: string;
  note: string;
}

export interface FamilySettlementSummaryDTO {
  workspace_id: UUID;
  period?: string | null;
  currency: string;
  total_shared_expenses_paise: number;
  total_shared_expenses_decimal: number;
  total_contributions_paid_paise: number;
  total_contributions_paid_decimal: number;
  total_allocated_paise: number;
  total_allocated_decimal: number;
  member_settlements: MemberSettlementDTO[];
  recommendations: SettlementRecommendationDTO[];
}

export interface SharedAccountDTO {
  id: UUID;
  family_workspace_id: UUID;
  account_id: UUID;
  account_name: string;
  account_type: string;
  masked_identifier?: string | null;
  shared_by_user_id: UUID;
  shared_by_name?: string | null;
  share_scope: AccountShareScope | string;
  current_balance_paise: number;
  current_balance_decimal: number;
  currency: string;
  is_active: boolean;
  created_at: string;
}

export interface FamilyActivityDTO {
  id: UUID;
  workspace_id: UUID;
  actor_user_id?: UUID | null;
  actor_name?: string | null;
  activity_type: string;
  resource_type: string;
  resource_id: string;
  title: string;
  description: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface FamilyOverviewDTO {
  profile: FamilyProfileDTO;
  member_count: number;
  total_household_income_paise: number;
  total_household_income_decimal: number;
  total_household_expense_paise: number;
  total_household_expense_decimal: number;
  net_household_savings_paise: number;
  net_household_savings_decimal: number;
  shared_account_balances_paise: number;
  shared_account_balances_decimal: number;
  budget_utilization_pct: number;
  active_budgets_count: number;
  active_goals_count: number;
  upcoming_commitments_count: number;
  top_expense_categories: Array<{ category: string; amount_paise: number; amount_decimal: number }>;
  recent_shared_transactions: Array<{
    id: string;
    description: string;
    amount_paise: number;
    amount_decimal: number;
    currency: string;
    direction: string;
    transaction_date: string;
    paid_by: string;
  }>;
}













