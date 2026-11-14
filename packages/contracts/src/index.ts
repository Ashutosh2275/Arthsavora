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






