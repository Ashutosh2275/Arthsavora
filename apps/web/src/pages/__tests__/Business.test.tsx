import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { Business } from '../Business';
import { useBusinessStore } from '@/store/useBusinessStore';

vi.mock('@/store/useBusinessStore');

const mockProfile = {
  id: 'prof-biz-1',
  workspace_id: 'ws-biz-1',
  business_name: 'Nexus Advisory Services',
  business_type: 'consulting',
  description: 'Enterprise Strategy & Management Advisory',
  contact_email: 'finance@nexusadvisory.in',
  contact_phone: '+91 98765 43210',
  address: 'Level 12, Express Towers, Nariman Point, Mumbai',
  country: 'IN',
  currency: 'INR',
  financial_year_start_month: 4,
  timezone: 'Asia/Kolkata',
  gstin: '27AAAAA0000A1Z5',
  pan: 'AAAAA0000A',
  tax_registered: true,
  invoice_prefix: 'INV',
  invoice_notes_template: 'Thank you for your business. Payment due within agreed terms.',
  terms_template: 'Standard commercial consulting engagement terms apply.',
  created_at: '2026-04-01T00:00:00Z',
  updated_at: '2026-11-14T00:00:00Z',
};

const mockOverview = {
  invoiced_revenue_paise: 50000000,
  invoiced_revenue_decimal: 500000.0,
  collected_revenue_paise: 35000000,
  collected_revenue_decimal: 350000.0,
  total_receivables_paise: 15000000,
  total_receivables_decimal: 150000.0,
  total_bills_paise: 5000000,
  total_bills_decimal: 50000.0,
  total_payables_paise: 5000000,
  total_payables_decimal: 50000.0,
  net_margin_paise: 30000000,
  net_margin_decimal: 300000.0,
  active_clients_count: 5,
  active_vendors_count: 3,
  draft_invoices_count: 1,
  overdue_invoices_count: 1,
  overdue_payables_count: 0,
};

const mockClients = [
  {
    id: 'client-1',
    workspace_id: 'ws-biz-1',
    name: 'Apex Global Corp',
    client_type: 'corporate',
    email: 'billing@apexglobal.com',
    phone: '+91 22 4000 1111',
    address: 'Bandra-Kurla Complex, Mumbai',
    city: 'Mumbai',
    state: 'Maharashtra',
    postal_code: '400051',
    country: 'IN',
    gstin: '27BBBBB1111B1Z2',
    pan: 'BBBBB1111B',
    currency: 'INR',
    payment_terms_days: 30,
    is_active: true,
    created_at: '2026-05-01T00:00:00Z',
    updated_at: '2026-11-14T00:00:00Z',
  },
];

const mockVendors = [
  {
    id: 'vendor-1',
    workspace_id: 'ws-biz-1',
    name: 'Cloud Hosting Services LLC',
    vendor_type: 'contractor',
    email: 'accounts@cloudhost.com',
    phone: '+1 415 555 0199',
    payment_terms_days: 15,
    currency: 'INR',
    is_active: true,
    created_at: '2026-05-01T00:00:00Z',
    updated_at: '2026-11-14T00:00:00Z',
  },
];

const mockInvoices = [
  {
    id: 'inv-1',
    workspace_id: 'ws-biz-1',
    invoice_number: 'INV-2026-0001',
    client_id: 'client-1',
    client_name: 'Apex Global Corp',
    status: 'issued',
    invoice_date: '2026-11-01',
    due_date: '2026-11-30',
    currency: 'INR',
    subtotal_paise: 10000000,
    subtotal_decimal: 100000.0,
    tax_total_paise: 1800000,
    tax_total_decimal: 18000.0,
    total_amount_paise: 11800000,
    total_amount_decimal: 118000.0,
    paid_amount_paise: 0,
    paid_amount_decimal: 0.0,
    is_overdue: false,
    created_at: '2026-11-01T00:00:00Z',
    updated_at: '2026-11-01T00:00:00Z',
  },
];

const mockPayables = [
  {
    id: 'pay-1',
    workspace_id: 'ws-biz-1',
    vendor_id: 'vendor-1',
    vendor_name: 'Cloud Hosting Services LLC',
    bill_number: 'BILL-2026-449',
    bill_date: '2026-11-05',
    due_date: '2026-11-20',
    amount_paise: 5000000,
    amount_decimal: 50000.0,
    tax_amount_paise: 900000,
    tax_amount_decimal: 9000.0,
    total_amount_paise: 5000000,
    total_amount_decimal: 50000.0,
    paid_amount_paise: 0,
    paid_amount_decimal: 0.0,
    currency: 'INR',
    category: 'Cloud Infrastructure',
    status: 'open',
    is_overdue: false,
    created_at: '2026-11-05T00:00:00Z',
    updated_at: '2026-11-05T00:00:00Z',
  },
];

const mockArAging = {
  current_paise: 11800000,
  current_decimal: 118000.0,
  days_1_30_paise: 3200000,
  days_1_30_decimal: 32000.0,
  days_31_60_paise: 0,
  days_31_60_decimal: 0.0,
  days_61_90_paise: 0,
  days_61_90_decimal: 0.0,
  days_91_plus_paise: 0,
  days_91_plus_decimal: 0.0,
  total_outstanding_paise: 15000000,
  total_outstanding_decimal: 150000.0,
  as_of_date: '2026-11-14',
};

const mockApAging = {
  current_paise: 5000000,
  current_decimal: 50000.0,
  days_1_30_paise: 0,
  days_1_30_decimal: 0.0,
  days_31_60_paise: 0,
  days_31_60_decimal: 0.0,
  days_61_90_paise: 0,
  days_61_90_decimal: 0.0,
  days_91_plus_paise: 0,
  days_91_plus_decimal: 0.0,
  total_outstanding_paise: 5000000,
  total_outstanding_decimal: 50000.0,
  as_of_date: '2026-11-14',
};

const mockAnalytics = {
  top_clients: [
    { client_name: 'Apex Global Corp', revenue_paise: 50000000, revenue_decimal: 500000.0, invoice_count: 5 },
  ],
  top_vendors: [
    { vendor_name: 'Cloud Hosting Services LLC', bill_volume_paise: 5000000, bill_volume_decimal: 50000.0, bill_count: 2 },
  ],
  cash_flow_summary: {
    cash_inflow_paise: 35000000,
    cash_inflow_decimal: 350000.0,
    cash_outflow_paise: 5000000,
    cash_outflow_decimal: 50000.0,
    net_cash_flow_paise: 30000000,
    net_cash_flow_decimal: 300000.0,
    period_start: '2026-11-01',
    period_end: '2026-11-30',
  },
};

const mockActivities = [
  {
    id: 'act-1',
    workspace_id: 'ws-biz-1',
    activity_type: 'invoice_issued',
    description: 'Invoice INV-2026-0001 issued to Apex Global Corp for ₹118,000.00',
    entity_id: 'inv-1',
    entity_type: 'invoice',
    actor_id: 'user-1',
    created_at: '2026-11-01T10:00:00Z',
  },
];

describe('Business Finance Hub Page Component', () => {
  const fetchProfileMock = vi.fn();
  const fetchOverviewMock = vi.fn();
  const fetchClientsMock = vi.fn();
  const fetchVendorsMock = vi.fn();
  const fetchInvoicesMock = vi.fn();
  const fetchPayablesMock = vi.fn();
  const fetchAnalyticsMock = vi.fn();
  const fetchActivitiesMock = vi.fn();
  const fetchReceivablesAgingMock = vi.fn();
  const fetchPayablesSummaryMock = vi.fn();
  const createInvoiceMock = vi.fn().mockResolvedValue({ id: 'inv-2' });
  const issueInvoiceMock = vi.fn().mockResolvedValue(undefined);
  const cancelInvoiceMock = vi.fn().mockResolvedValue(undefined);
  const recordInvoicePaymentMock = vi.fn().mockResolvedValue(undefined);
  const createClientMock = vi.fn().mockResolvedValue({ id: 'client-2' });
  const createVendorMock = vi.fn().mockResolvedValue({ id: 'vendor-2' });
  const createPayableMock = vi.fn().mockResolvedValue({ id: 'pay-2' });
  const recordPayablePaymentMock = vi.fn().mockResolvedValue(undefined);
  const exportInvoicesCsvMock = vi.fn().mockResolvedValue('Invoice Number,Client,Date\nINV-001,Test,2026-11-01');

  beforeEach(() => {
    vi.clearAllMocks();
    (useBusinessStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      profile: mockProfile,
      overview: mockOverview,
      clients: mockClients,
      vendors: mockVendors,
      invoices: mockInvoices,
      payables: mockPayables,
      arAging: mockArAging,
      apAging: mockApAging,
      analytics: mockAnalytics,
      activities: mockActivities,
      isLoading: false,
      error: null,
      fetchProfile: fetchProfileMock,
      fetchOverview: fetchOverviewMock,
      fetchClients: fetchClientsMock,
      fetchVendors: fetchVendorsMock,
      fetchInvoices: fetchInvoicesMock,
      fetchPayables: fetchPayablesMock,
      fetchAnalytics: fetchAnalyticsMock,
      fetchActivities: fetchActivitiesMock,
      fetchReceivablesAging: fetchReceivablesAgingMock,
      fetchPayablesSummary: fetchPayablesSummaryMock,
      createInvoice: createInvoiceMock,
      issueInvoice: issueInvoiceMock,
      cancelInvoice: cancelInvoiceMock,
      recordInvoicePayment: recordInvoicePaymentMock,
      createClient: createClientMock,
      createVendor: createVendorMock,
      createPayable: createPayableMock,
      recordPayablePayment: recordPayablePaymentMock,
      exportInvoicesCsv: exportInvoicesCsvMock,
    });
  });

  it('renders business header, company name, and key operational summary cards', () => {
    render(<Business />);

    expect(screen.getByText('Nexus Advisory Services')).toBeInTheDocument();
    expect(screen.getByText('consulting')).toBeInTheDocument();
    expect(screen.getByText('Invoiced Revenue')).toBeInTheDocument();
    expect(screen.getByText('Collected Cash')).toBeInTheDocument();
    expect(screen.getByText('Accounts Receivable (AR)')).toBeInTheDocument();
    expect(screen.getByText('Operating Expenses')).toBeInTheDocument();
    expect(screen.getByText('Accounts Payable (AP)')).toBeInTheDocument();
    expect(screen.getByText('Net Operating Result')).toBeInTheDocument();
    expect(screen.getByText('₹5,00,000.00')).toBeInTheDocument();
  });

  it('navigates to Invoices tab and renders the invoice register with actions', () => {
    render(<Business />);

    const invoicesTab = screen.getByRole('button', { name: /Invoices/i });
    fireEvent.click(invoicesTab);

    expect(screen.getByText('Commercial Invoices')).toBeInTheDocument();
    expect(screen.getByText('INV-2026-0001')).toBeInTheDocument();
    expect(screen.getByText('Apex Global Corp')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^Pay$/i })).toBeInTheDocument();
  });

  it('navigates to Clients tab and renders client profiles', () => {
    render(<Business />);

    const clientsTab = screen.getByRole('button', { name: /Clients/i });
    fireEvent.click(clientsTab);

    expect(screen.getByText('Clients & Customers')).toBeInTheDocument();
    expect(screen.getByText('Apex Global Corp')).toBeInTheDocument();
    expect(screen.getByText(/billing@apexglobal\.com/i)).toBeInTheDocument();
    expect(screen.getByText(/30 Days Terms/i)).toBeInTheDocument();
  });

  it('navigates to Vendors tab and renders vendor directory', () => {
    render(<Business />);

    const vendorsTab = screen.getByRole('button', { name: /Vendors/i });
    fireEvent.click(vendorsTab);

    expect(screen.getByText('Vendors & Suppliers')).toBeInTheDocument();
    expect(screen.getByText('Cloud Hosting Services LLC')).toBeInTheDocument();
    expect(screen.getByText(/accounts@cloudhost.com/i)).toBeInTheDocument();
    expect(screen.getByText(/15 Days Terms/i)).toBeInTheDocument();
  });

  it('navigates to Payables tab and renders vendor bills', () => {
    render(<Business />);

    const payablesTab = screen.getByRole('button', { name: /Payables/i });
    fireEvent.click(payablesTab);

    expect(screen.getByText('Vendor Bills & Accounts Payable')).toBeInTheDocument();
    expect(screen.getByText('BILL-2026-449')).toBeInTheDocument();
    expect(screen.getByText('Cloud Hosting Services LLC')).toBeInTheDocument();
    expect(screen.getByText('Record Bill')).toBeInTheDocument();
  });

  it('navigates to Analytics & Aging tab and renders AR/AP aging buckets', () => {
    render(<Business />);

    const agingTab = screen.getByRole('button', { name: /Analytics & Aging/i });
    fireEvent.click(agingTab);

    expect(screen.getByText('Accounts Receivable Aging Schedule')).toBeInTheDocument();
    expect(screen.getByText('Accounts Payable Aging Schedule')).toBeInTheDocument();
    expect(screen.getByText('Current (Not Overdue)')).toBeInTheDocument();
    expect(screen.getByText('Current (Not Due)')).toBeInTheDocument();
    expect(screen.getByText('Total Outstanding AR')).toBeInTheDocument();
    expect(screen.getByText('Total Outstanding AP')).toBeInTheDocument();
  });

  it('navigates to Activity Log tab and displays audit events', () => {
    render(<Business />);

    const activityTab = screen.getByRole('button', { name: /Activity Log/i });
    fireEvent.click(activityTab);

    expect(screen.getByText('Commercial Operations Audit Trail')).toBeInTheDocument();
    expect(screen.getByText(/Invoice INV-2026-0001 issued to Apex Global Corp/)).toBeInTheDocument();
  });

  it('opens and closes the Create Invoice modal', async () => {
    render(<Business />);

    const newInvoiceBtn = screen.getByRole('button', { name: /New Invoice/i });
    fireEvent.click(newInvoiceBtn);

    expect(screen.getByText('Create Commercial Tax Invoice')).toBeInTheDocument();
    expect(screen.getByText('Select Client *')).toBeInTheDocument();
    expect(screen.getByText('Line Items')).toBeInTheDocument();

    const cancelBtn = screen.getByRole('button', { name: /Cancel/i });
    fireEvent.click(cancelBtn);

    await waitFor(() => {
      expect(screen.queryByText('Create Commercial Tax Invoice')).not.toBeInTheDocument();
    });
  });

  it('triggers CSV export when Export CSV is clicked', async () => {
    render(<Business />);

    const exportBtn = screen.getByRole('button', { name: /Export CSV/i });
    fireEvent.click(exportBtn);

    expect(exportInvoicesCsvMock).toHaveBeenCalled();
  });
});
