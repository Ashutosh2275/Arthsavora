import React, { useEffect, useState } from 'react';
import {
  Briefcase,
  Building2,
  FileText,
  Users,
  Truck,
  CreditCard,
  TrendingUp,
  Download,
  Plus,
  RefreshCw,
  CheckCircle,
  AlertTriangle,
  Clock,
  XCircle,
  DollarSign,
  ArrowUpRight,
  ArrowDownLeft,
  Calendar,
  Layers,
} from 'lucide-react';
import { useBusinessStore } from '../store/useBusinessStore';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Modal } from '../components/ui/modal';
import { Input } from '../components/ui/input';
import { Card } from '../components/ui/card';
import { EmptyState } from '@/components/feedback/EmptyState';

export const Business: React.FC = () => {
  const {
    profile,
    overview,
    clients,
    vendors,
    invoices,
    payables,
    arAging,
    apAging,
    analytics,
    activities,
    isLoading,
    error,
    fetchProfile,
    fetchOverview,
    fetchClients,
    createClient,
    fetchVendors,
    createVendor,
    fetchInvoices,
    createInvoice,
    issueInvoice,
    cancelInvoice,
    recordInvoicePayment,
    fetchPayables,
    createPayable,
    recordPayablePayment,
    fetchAnalytics,
    fetchActivities,
    exportInvoicesCsv,
  } = useBusinessStore();

  const [activeTab, setActiveTab] = useState<
    'overview' | 'invoices' | 'clients' | 'vendors' | 'payables' | 'analytics' | 'activity'
  >('overview');

  // Modals
  const [isInvoiceModalOpen, setIsInvoiceModalOpen] = useState(false);
  const [isPaymentModalOpen, setIsPaymentModalOpen] = useState(false);
  const [isClientModalOpen, setIsClientModalOpen] = useState(false);
  const [isVendorModalOpen, setIsVendorModalOpen] = useState(false);
  const [isPayableModalOpen, setIsPayableModalOpen] = useState(false);
  const [selectedInvoice, setSelectedInvoice] = useState<any>(null);
  const [selectedPayable, setSelectedPayable] = useState<any>(null);

  // Invoice Form State
  const [invoiceForm, setInvoiceForm] = useState({
    clientId: '',
    invoiceDate: new Date().toISOString().split('T')[0],
    dueDate: new Date(Date.now() + 30 * 86400000).toISOString().split('T')[0],
    overallDiscount: '0',
    isInterstate: false,
    notes: 'Thank you for your business.',
    paymentInstructions: 'Bank Transfer: HDFC Bank / UPI: payments@arthsavora',
    lineItems: [
      {
        description: 'Professional Services',
        hsnSacCode: '998311',
        quantity: 1,
        unitPrice: 25000,
        taxRatePercent: 18,
      },
    ],
  });

  // Payment Form State
  const [paymentForm, setPaymentForm] = useState({
    paymentDate: new Date().toISOString().split('T')[0],
    amount: '',
    paymentMethod: 'bank_transfer',
    referenceNumber: '',
    notes: '',
  });

  // Client Form State
  const [clientForm, setClientForm] = useState({
    name: '',
    clientType: 'business',
    email: '',
    phone: '',
    gstin: '',
    pan: '',
    paymentTermsDays: 30,
    notes: '',
  });

  // Vendor Form State
  const [vendorForm, setVendorForm] = useState({
    name: '',
    vendorType: 'service_provider',
    email: '',
    phone: '',
    gstin: '',
    pan: '',
    paymentTermsDays: 30,
    notes: '',
  });

  // Payable Form State
  const [payableForm, setPayableForm] = useState({
    vendorId: '',
    billNumber: '',
    billDate: new Date().toISOString().split('T')[0],
    dueDate: new Date(Date.now() + 15 * 86400000).toISOString().split('T')[0],
    subtotal: '',
    tax: '0',
    notes: '',
  });

  const workspaceId = typeof window !== 'undefined' ? localStorage.getItem('active_workspace_id') || undefined : undefined;

  useEffect(() => {
    fetchProfile(workspaceId);
    fetchOverview(workspaceId);
    fetchClients(workspaceId);
    fetchVendors(workspaceId);
    fetchInvoices(workspaceId);
    fetchPayables(workspaceId);
    fetchAnalytics(workspaceId);
    fetchActivities(workspaceId);
  }, [workspaceId]);

  const handleRefresh = () => {
    fetchProfile(workspaceId);
    fetchOverview(workspaceId);
    fetchClients(workspaceId);
    fetchVendors(workspaceId);
    fetchInvoices(workspaceId);
    fetchPayables(workspaceId);
    fetchAnalytics(workspaceId);
    fetchActivities(workspaceId);
  };

  const handleAddLineItem = () => {
    setInvoiceForm((prev) => ({
      ...prev,
      lineItems: [
        ...prev.lineItems,
        {
          description: '',
          hsnSacCode: '',
          quantity: 1,
          unitPrice: 0,
          taxRatePercent: 18,
        },
      ],
    }));
  };

  const handleRemoveLineItem = (index: number) => {
    if (invoiceForm.lineItems.length <= 1) return;
    setInvoiceForm((prev) => ({
      ...prev,
      lineItems: prev.lineItems.filter((_, idx) => idx !== index),
    }));
  };

  const handleLineItemChange = (index: number, field: string, value: any) => {
    setInvoiceForm((prev) => {
      const items = [...prev.lineItems];
      items[index] = { ...items[index], [field]: value };
      return { ...prev, lineItems: items };
    });
  };

  const handleCreateInvoiceSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!invoiceForm.clientId) {
      alert('Please select a client.');
      return;
    }
    try {
      await createInvoice(
        {
          client_id: invoiceForm.clientId,
          invoice_date: invoiceForm.invoiceDate,
          due_date: invoiceForm.dueDate,
          line_items: invoiceForm.lineItems.map((li) => ({
            description: li.description,
            hsn_sac_code: li.hsnSacCode || null,
            quantity: Number(li.quantity),
            unit_price: Number(li.unitPrice),
            tax_rate_percent: Number(li.taxRatePercent),
          })),
          overall_discount: Number(invoiceForm.overallDiscount || 0),
          is_interstate: invoiceForm.isInterstate,
          notes: invoiceForm.notes,
          payment_instructions: invoiceForm.paymentInstructions,
        },
        workspaceId
      );
      setIsInvoiceModalOpen(false);
      fetchInvoices(workspaceId);
    } catch (err: any) {
      alert(err.message || 'Error creating invoice');
    }
  };

  const handleRecordPaymentSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedInvoice) return;
    try {
      await recordInvoicePayment(
        selectedInvoice.id,
        {
          payment_date: paymentForm.paymentDate,
          amount: Number(paymentForm.amount),
          payment_method: paymentForm.paymentMethod,
          reference_number: paymentForm.referenceNumber || null,
          notes: paymentForm.notes || null,
        },
        workspaceId
      );
      setIsPaymentModalOpen(false);
      setSelectedInvoice(null);
    } catch (err: any) {
      alert(err.message || 'Error recording payment');
    }
  };

  const handleCreateClientSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createClient(
        {
          name: clientForm.name,
          client_type: clientForm.clientType,
          email: clientForm.email || null,
          phone: clientForm.phone || null,
          gstin: clientForm.gstin || null,
          pan: clientForm.pan || null,
          payment_terms_days: Number(clientForm.paymentTermsDays || 30),
          notes: clientForm.notes || null,
        },
        workspaceId
      );
      setIsClientModalOpen(false);
      setClientForm({
        name: '',
        clientType: 'business',
        email: '',
        phone: '',
        gstin: '',
        pan: '',
        paymentTermsDays: 30,
        notes: '',
      });
    } catch (err: any) {
      alert(err.message || 'Error adding client');
    }
  };

  const handleCreateVendorSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createVendor(
        {
          name: vendorForm.name,
          vendor_type: vendorForm.vendorType,
          email: vendorForm.email || null,
          phone: vendorForm.phone || null,
          gstin: vendorForm.gstin || null,
          pan: vendorForm.pan || null,
          payment_terms_days: Number(vendorForm.paymentTermsDays || 30),
          notes: vendorForm.notes || null,
        },
        workspaceId
      );
      setIsVendorModalOpen(false);
      setVendorForm({
        name: '',
        vendorType: 'service_provider',
        email: '',
        phone: '',
        gstin: '',
        pan: '',
        paymentTermsDays: 30,
        notes: '',
      });
    } catch (err: any) {
      alert(err.message || 'Error adding vendor');
    }
  };

  const handleCreatePayableSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!payableForm.vendorId) {
      alert('Please select a vendor.');
      return;
    }
    try {
      await createPayable(
        {
          vendor_id: payableForm.vendorId,
          bill_number: payableForm.billNumber || null,
          bill_date: payableForm.billDate,
          due_date: payableForm.dueDate,
          subtotal_amount: Number(payableForm.subtotal),
          tax_amount: Number(payableForm.tax || 0),
          notes: payableForm.notes || null,
        },
        workspaceId
      );
      setIsPayableModalOpen(false);
      setPayableForm({
        vendorId: '',
        billNumber: '',
        billDate: new Date().toISOString().split('T')[0],
        dueDate: new Date(Date.now() + 15 * 86400000).toISOString().split('T')[0],
        subtotal: '',
        tax: '0',
        notes: '',
      });
    } catch (err: any) {
      alert(err.message || 'Error creating bill');
    }
  };

  const handleExportCsv = async () => {
    try {
      const csvData = await exportInvoicesCsv(workspaceId);
      const blob = new Blob([csvData], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.setAttribute('href', url);
      link.setAttribute('download', `invoices_${new Date().toISOString().split('T')[0]}.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err) {
      alert('Error exporting CSV');
    }
  };

  const getStatusBadgeVariant = (status: string): 'brand' | 'income' | 'warning' | 'neutral' | 'expense' | 'info' => {
    switch (status.toLowerCase()) {
      case 'paid':
        return 'income';
      case 'issued':
      case 'due':
        return 'info';
      case 'partially_paid':
        return 'warning';
      case 'overdue':
        return 'expense';
      case 'cancelled':
        return 'neutral';
      default:
        return 'neutral';
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-gray-200 dark:border-gray-800 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-gray-900 dark:text-white flex items-center gap-2">
              <Briefcase className="h-6 w-6 text-brand-600" />
              {profile?.business_name || 'Small Business Finance'}
            </h1>
            <Badge variant="brand" className="uppercase font-semibold">
              {profile?.business_type || 'Service Business'}
            </Badge>
          </div>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Commercial operations, invoicing, double-entry accounts receivable & payable, cash flow, and tax reporting.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleRefresh} isLoading={isLoading}>
            <RefreshCw className="h-4 w-4 mr-1" /> Refresh
          </Button>
          <Button variant="outline" size="sm" onClick={handleExportCsv}>
            <Download className="h-4 w-4 mr-1" /> Export CSV
          </Button>
          <Button variant="primary" size="sm" onClick={() => setIsInvoiceModalOpen(true)}>
            <Plus className="h-4 w-4 mr-1" /> New Invoice
          </Button>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex border-b border-gray-200 dark:border-gray-800 overflow-x-auto space-x-1">
        {[
          { key: 'overview', label: 'Overview', icon: TrendingUp },
          { key: 'invoices', label: `Invoices (${invoices.length})`, icon: FileText },
          { key: 'clients', label: `Clients (${clients.length})`, icon: Users },
          { key: 'vendors', label: `Vendors (${vendors.length})`, icon: Truck },
          { key: 'payables', label: `Payables (${payables.length})`, icon: CreditCard },
          { key: 'analytics', label: 'Analytics & Aging', icon: Layers },
          { key: 'activity', label: 'Activity Log', icon: Clock },
        ].map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key as any)}
            className={`flex items-center gap-2 py-3 px-4 text-sm font-medium border-b-2 whitespace-nowrap transition-colors ${
              activeTab === key
                ? 'border-brand-600 text-brand-600 dark:text-brand-400'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
            }`}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </div>

      {/* TAB 1: OVERVIEW */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Top Metric Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <Card className="p-5">
              <div className="flex justify-between items-start">
                <span className="text-xs font-semibold uppercase tracking-wider text-gray-500">Invoiced Revenue</span>
                <span className="p-2 bg-blue-50 dark:bg-blue-900/30 text-blue-600 rounded-lg">
                  <ArrowUpRight className="h-5 w-5" />
                </span>
              </div>
              <div className="text-2xl font-bold mt-2 text-gray-900 dark:text-white">
                ₹{((overview?.invoiced_revenue_paise || 0) / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </div>
              <div className="text-xs text-gray-500 mt-1">Accrual sales across all issued invoices</div>
            </Card>

            <Card className="p-5">
              <div className="flex justify-between items-start">
                <span className="text-xs font-semibold uppercase tracking-wider text-gray-500">Collected Cash</span>
                <span className="p-2 bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600 rounded-lg">
                  <CheckCircle className="h-5 w-5" />
                </span>
              </div>
              <div className="text-2xl font-bold mt-2 text-emerald-600 dark:text-emerald-400">
                ₹{((overview?.collected_revenue_paise || 0) / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </div>
              <div className="text-xs text-gray-500 mt-1">Actual cash realized in operating accounts</div>
            </Card>

            <Card className="p-5">
              <div className="flex justify-between items-start">
                <span className="text-xs font-semibold uppercase tracking-wider text-gray-500">Accounts Receivable (AR)</span>
                <span className="p-2 bg-amber-50 dark:bg-amber-900/30 text-amber-600 rounded-lg">
                  <AlertTriangle className="h-5 w-5" />
                </span>
              </div>
              <div className="text-2xl font-bold mt-2 text-amber-600 dark:text-amber-400">
                ₹{((overview?.total_receivables_paise || 0) / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </div>
              <div className="text-xs text-gray-500 mt-1">
                {overview?.overdue_invoices_count || 0} invoices currently overdue
              </div>
            </Card>

            <Card className="p-5">
              <div className="flex justify-between items-start">
                <span className="text-xs font-semibold uppercase tracking-wider text-gray-500">Operating Expenses</span>
                <span className="p-2 bg-rose-50 dark:bg-rose-900/30 text-rose-600 rounded-lg">
                  <ArrowDownLeft className="h-5 w-5" />
                </span>
              </div>
              <div className="text-2xl font-bold mt-2 text-gray-900 dark:text-white">
                ₹{((overview?.total_bills_paise || 0) / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </div>
              <div className="text-xs text-gray-500 mt-1">Total vendor bills & operating costs logged</div>
            </Card>

            <Card className="p-5">
              <div className="flex justify-between items-start">
                <span className="text-xs font-semibold uppercase tracking-wider text-gray-500">Accounts Payable (AP)</span>
                <span className="p-2 bg-purple-50 dark:bg-purple-900/30 text-purple-600 rounded-lg">
                  <Truck className="h-5 w-5" />
                </span>
              </div>
              <div className="text-2xl font-bold mt-2 text-purple-600 dark:text-purple-400">
                ₹{((overview?.total_payables_paise || 0) / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </div>
              <div className="text-xs text-gray-500 mt-1">Outstanding liabilities owed to vendors</div>
            </Card>

            <Card className="p-5">
              <div className="flex justify-between items-start">
                <span className="text-xs font-semibold uppercase tracking-wider text-gray-500">Net Operating Result</span>
                <span className="p-2 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 rounded-lg">
                  <TrendingUp className="h-5 w-5" />
                </span>
              </div>
              <div className="text-2xl font-bold mt-2 text-indigo-600 dark:text-indigo-400">
                ₹{((overview?.net_operating_result_paise || 0) / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </div>
              <div className="text-xs text-gray-500 mt-1">Invoiced Revenue minus Vendor Operating Costs</div>
            </Card>
          </div>

          {/* Quick Tables: Recent Invoices & Aging Preview */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card className="p-5">
              <div className="flex justify-between items-center mb-4">
                <h3 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                  <FileText className="h-5 w-5 text-brand-600" /> Recent Invoices
                </h3>
                <Button variant="ghost" size="sm" onClick={() => setActiveTab('invoices')}>
                  View All &rarr;
                </Button>
              </div>
              {invoices.length === 0 ? (
                <EmptyState
                  title="No Invoices Issued"
                  description="Create your first client invoice to begin tracking receivables."
                  icon={<FileText className="h-8 w-8 text-gray-400" />}
                />
              ) : (
                <div className="space-y-3">
                  {invoices.slice(0, 4).map((inv) => (
                    <div
                      key={inv.id}
                      className="flex items-center justify-between p-3 rounded-lg bg-gray-50 dark:bg-gray-800/50 border border-gray-100 dark:border-gray-800"
                    >
                      <div>
                        <div className="font-semibold text-sm text-gray-900 dark:text-white">
                          {inv.invoice_number} &bull; {inv.client_name || 'Client'}
                        </div>
                        <div className="text-xs text-gray-500">Due: {inv.due_date}</div>
                      </div>
                      <div className="text-right">
                        <div className="font-semibold text-sm">₹{(inv.total_amount_paise / 100).toLocaleString('en-IN')}</div>
                        <Badge variant={getStatusBadgeVariant(inv.status)} className="text-[10px] uppercase font-bold">
                          {inv.status}
                        </Badge>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Card>

            <Card className="p-5">
              <div className="flex justify-between items-center mb-4">
                <h3 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                  <Layers className="h-5 w-5 text-brand-600" /> Receivables (AR) Aging
                </h3>
                <Button variant="ghost" size="sm" onClick={() => setActiveTab('analytics')}>
                  Detailed Aging &rarr;
                </Button>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 bg-gray-50 dark:bg-gray-800/40 rounded-lg text-center">
                  <div className="text-xs text-gray-500">Current (Not Due)</div>
                  <div className="text-lg font-bold text-emerald-600 mt-1">
                    ₹{((arAging?.current_paise || 0) / 100).toLocaleString('en-IN')}
                  </div>
                </div>
                <div className="p-3 bg-gray-50 dark:bg-gray-800/40 rounded-lg text-center">
                  <div className="text-xs text-gray-500">1–30 Days</div>
                  <div className="text-lg font-bold text-amber-600 mt-1">
                    ₹{((arAging?.days_1_30_paise || 0) / 100).toLocaleString('en-IN')}
                  </div>
                </div>
                <div className="p-3 bg-gray-50 dark:bg-gray-800/40 rounded-lg text-center">
                  <div className="text-xs text-gray-500">31–60 Days</div>
                  <div className="text-lg font-bold text-orange-600 mt-1">
                    ₹{((arAging?.days_31_60_paise || 0) / 100).toLocaleString('en-IN')}
                  </div>
                </div>
                <div className="p-3 bg-gray-50 dark:bg-gray-800/40 rounded-lg text-center">
                  <div className="text-xs text-gray-500">60+ Days</div>
                  <div className="text-lg font-bold text-rose-600 mt-1">
                    ₹{(((arAging?.days_61_90_paise || 0) + (arAging?.days_91_plus_paise || 0)) / 100).toLocaleString('en-IN')}
                  </div>
                </div>
              </div>
              <div className="mt-4 p-3 bg-blue-50/60 dark:bg-blue-900/20 rounded-lg text-xs text-blue-700 dark:text-blue-300">
                <strong>Statutory Accounting Standard:</strong> Revenue is recognized on invoice issuance under accrual accounting. Cash receipts debit the designated bank ledger and credit Accounts Receivable without double-counting revenue.
              </div>
            </Card>
          </div>
        </div>
      )}

      {/* TAB 2: INVOICES */}
      {activeTab === 'invoices' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Commercial Invoices</h3>
            <Button variant="primary" size="sm" onClick={() => setIsInvoiceModalOpen(true)}>
              <Plus className="h-4 w-4 mr-1" /> New Invoice
            </Button>
          </div>

          {invoices.length === 0 ? (
            <EmptyState
              title="No Invoices Yet"
              description="Issue a new invoice to track client receivables and revenue."
              icon={<FileText className="h-10 w-10 text-gray-400" />}
              action={
                <Button variant="primary" size="sm" onClick={() => setIsInvoiceModalOpen(true)}>
                  Create Invoice
                </Button>
              }
            />
          ) : (
            <div className="overflow-x-auto border border-gray-200 dark:border-gray-800 rounded-lg">
              <table className="w-full text-left text-sm text-gray-600 dark:text-gray-300">
                <thead className="bg-gray-50 dark:bg-gray-800/60 text-xs uppercase text-gray-500 font-semibold border-b border-gray-200 dark:border-gray-800">
                  <tr>
                    <th className="py-3 px-4">Invoice #</th>
                    <th className="py-3 px-4">Date</th>
                    <th className="py-3 px-4">Due Date</th>
                    <th className="py-3 px-4">Client</th>
                    <th className="py-3 px-4 text-right">Total</th>
                    <th className="py-3 px-4 text-right">Paid</th>
                    <th className="py-3 px-4 text-right">Balance</th>
                    <th className="py-3 px-4 text-center">Status</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                  {invoices.map((inv) => {
                    const balance = Math.max(0, inv.total_amount_paise - inv.paid_amount_paise);
                    return (
                      <tr key={inv.id} className="hover:bg-gray-50/50 dark:hover:bg-gray-800/40">
                        <td className="py-3 px-4 font-mono font-medium text-gray-900 dark:text-white">
                          {inv.invoice_number}
                        </td>
                        <td className="py-3 px-4">{inv.invoice_date}</td>
                        <td className="py-3 px-4">{inv.due_date}</td>
                        <td className="py-3 px-4 font-medium text-gray-900 dark:text-white">{inv.client_name || 'Client'}</td>
                        <td className="py-3 px-4 text-right font-semibold">
                          ₹{(inv.total_amount_paise / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                        </td>
                        <td className="py-3 px-4 text-right text-emerald-600">
                          ₹{(inv.paid_amount_paise / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                        </td>
                        <td className="py-3 px-4 text-right font-semibold text-rose-600">
                          ₹{(balance / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                        </td>
                        <td className="py-3 px-4 text-center">
                          <Badge variant={getStatusBadgeVariant(inv.status)} className="uppercase text-[11px] font-bold">
                            {inv.status}
                          </Badge>
                        </td>
                        <td className="py-3 px-4 text-right space-x-1">
                          {inv.status === 'draft' && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={async () => {
                                if (confirm(`Issue invoice ${inv.invoice_number}? This locks the invoice snapshot.`)) {
                                  await issueInvoice(inv.id, workspaceId);
                                }
                              }}
                            >
                              Issue
                            </Button>
                          )}
                          {(inv.status === 'issued' || inv.status === 'partially_paid') && (
                            <Button
                              variant="primary"
                              size="sm"
                              onClick={() => {
                                setSelectedInvoice(inv);
                                setPaymentForm((p) => ({
                                  ...p,
                                  amount: (balance / 100).toString(),
                                }));
                                setIsPaymentModalOpen(true);
                              }}
                            >
                              Pay
                            </Button>
                          )}
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              window.open(`/api/v1/business/invoices/${inv.id}/pdf`, '_blank');
                            }}
                          >
                            PDF
                          </Button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* TAB 3: CLIENTS */}
      {activeTab === 'clients' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Clients & Customers</h3>
            <Button variant="primary" size="sm" onClick={() => setIsClientModalOpen(true)}>
              <Plus className="h-4 w-4 mr-1" /> Add Client
            </Button>
          </div>

          {clients.length === 0 ? (
            <EmptyState
              title="No Clients Found"
              description="Add clients to issue professional invoices and track receivables."
              icon={<Users className="h-10 w-10 text-gray-400" />}
              action={
                <Button variant="primary" size="sm" onClick={() => setIsClientModalOpen(true)}>
                  Add Client
                </Button>
              }
            />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {clients.map((c) => (
                <Card key={c.id} className="p-4 space-y-2">
                  <div className="flex justify-between items-start">
                    <div>
                      <div className="font-bold text-gray-900 dark:text-white">{c.name}</div>
                      <div className="text-xs text-gray-500 capitalize">{c.client_type}</div>
                    </div>
                    <Badge variant="neutral" className="text-[10px] uppercase">
                      {c.payment_terms_days} Days Terms
                    </Badge>
                  </div>
                  <div className="text-xs text-gray-600 dark:text-gray-400 space-y-1 pt-2 border-t border-gray-100 dark:border-gray-800">
                    {c.email && <div>Email: {c.email}</div>}
                    {c.phone && <div>Phone: {c.phone}</div>}
                    {c.gstin && <div>GSTIN: <span className="font-mono">{c.gstin}</span></div>}
                    {c.pan && <div>PAN: <span className="font-mono">{c.pan}</span></div>}
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 4: VENDORS */}
      {activeTab === 'vendors' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Vendors & Suppliers</h3>
            <Button variant="primary" size="sm" onClick={() => setIsVendorModalOpen(true)}>
              <Plus className="h-4 w-4 mr-1" /> Add Vendor
            </Button>
          </div>

          {vendors.length === 0 ? (
            <EmptyState
              title="No Vendors Registered"
              description="Add suppliers and contractors to log bills and manage payables."
              icon={<Truck className="h-10 w-10 text-gray-400" />}
              action={
                <Button variant="primary" size="sm" onClick={() => setIsVendorModalOpen(true)}>
                  Add Vendor
                </Button>
              }
            />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {vendors.map((v) => (
                <Card key={v.id} className="p-4 space-y-2">
                  <div className="flex justify-between items-start">
                    <div>
                      <div className="font-bold text-gray-900 dark:text-white">{v.name}</div>
                      <div className="text-xs text-gray-500 capitalize">{v.vendor_type.replace('_', ' ')}</div>
                    </div>
                    <Badge variant="neutral" className="text-[10px] uppercase">
                      {v.payment_terms_days} Days Terms
                    </Badge>
                  </div>
                  <div className="text-xs text-gray-600 dark:text-gray-400 space-y-1 pt-2 border-t border-gray-100 dark:border-gray-800">
                    {v.email && <div>Email: {v.email}</div>}
                    {v.phone && <div>Phone: {v.phone}</div>}
                    {v.gstin && <div>GSTIN: <span className="font-mono">{v.gstin}</span></div>}
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 5: PAYABLES */}
      {activeTab === 'payables' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Vendor Bills & Accounts Payable</h3>
            <Button variant="primary" size="sm" onClick={() => setIsPayableModalOpen(true)}>
              <Plus className="h-4 w-4 mr-1" /> Record Bill
            </Button>
          </div>

          {payables.length === 0 ? (
            <EmptyState
              title="No Vendor Bills Recorded"
              description="Record bills from contractors, SaaS providers, and suppliers."
              icon={<CreditCard className="h-10 w-10 text-gray-400" />}
              action={
                <Button variant="primary" size="sm" onClick={() => setIsPayableModalOpen(true)}>
                  Record Bill
                </Button>
              }
            />
          ) : (
            <div className="overflow-x-auto border border-gray-200 dark:border-gray-800 rounded-lg">
              <table className="w-full text-left text-sm text-gray-600 dark:text-gray-300">
                <thead className="bg-gray-50 dark:bg-gray-800/60 text-xs uppercase text-gray-500 font-semibold border-b border-gray-200 dark:border-gray-800">
                  <tr>
                    <th className="py-3 px-4">Bill #</th>
                    <th className="py-3 px-4">Date</th>
                    <th className="py-3 px-4">Due Date</th>
                    <th className="py-3 px-4">Vendor</th>
                    <th className="py-3 px-4 text-right">Total</th>
                    <th className="py-3 px-4 text-right">Paid</th>
                    <th className="py-3 px-4 text-right">Balance</th>
                    <th className="py-3 px-4 text-center">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                  {payables.map((p) => {
                    const balance = Math.max(0, p.total_amount_paise - p.paid_amount_paise);
                    return (
                      <tr key={p.id} className="hover:bg-gray-50/50 dark:hover:bg-gray-800/40">
                        <td className="py-3 px-4 font-mono font-medium">{p.bill_number || '-'}</td>
                        <td className="py-3 px-4">{p.bill_date}</td>
                        <td className="py-3 px-4">{p.due_date}</td>
                        <td className="py-3 px-4 font-medium text-gray-900 dark:text-white">{p.vendor_name || 'Vendor'}</td>
                        <td className="py-3 px-4 text-right font-semibold">
                          ₹{(p.total_amount_paise / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                        </td>
                        <td className="py-3 px-4 text-right text-emerald-600">
                          ₹{(p.paid_amount_paise / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                        </td>
                        <td className="py-3 px-4 text-right font-semibold text-rose-600">
                          ₹{(balance / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                        </td>
                        <td className="py-3 px-4 text-center">
                          <Badge variant={getStatusBadgeVariant(p.status)} className="uppercase text-[11px] font-bold">
                            {p.status}
                          </Badge>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* TAB 6: ANALYTICS & AGING */}
      {activeTab === 'analytics' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card className="p-5">
              <h3 className="font-semibold text-gray-900 dark:text-white mb-4">Accounts Receivable Aging Schedule</h3>
              <div className="space-y-3">
                {[
                  { label: 'Current (Not Overdue)', amount: arAging?.current_paise || 0, color: 'text-emerald-600' },
                  { label: '1–30 Days Past Due', amount: arAging?.days_1_30_paise || 0, color: 'text-amber-600' },
                  { label: '31–60 Days Past Due', amount: arAging?.days_31_60_paise || 0, color: 'text-orange-600' },
                  { label: '61–90 Days Past Due', amount: arAging?.days_61_90_paise || 0, color: 'text-rose-600' },
                  { label: '91+ Days Past Due', amount: arAging?.days_91_plus_paise || 0, color: 'text-red-700 font-bold' },
                ].map(({ label, amount, color }) => (
                  <div key={label} className="flex justify-between items-center py-2 border-b border-gray-100 dark:border-gray-800 text-sm">
                    <span className="text-gray-600 dark:text-gray-400">{label}</span>
                    <span className={`font-semibold ${color}`}>₹{(amount / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                  </div>
                ))}
                <div className="flex justify-between items-center pt-2 font-bold text-gray-900 dark:text-white">
                  <span>Total Outstanding AR</span>
                  <span>₹{((arAging?.total_outstanding_paise || 0) / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                </div>
              </div>
            </Card>

            <Card className="p-5">
              <h3 className="font-semibold text-gray-900 dark:text-white mb-4">Accounts Payable Aging Schedule</h3>
              <div className="space-y-3">
                {[
                  { label: 'Current (Not Due)', amount: apAging?.current_paise || 0, color: 'text-emerald-600' },
                  { label: '1–30 Days Past Due', amount: apAging?.days_1_30_paise || 0, color: 'text-amber-600' },
                  { label: '31–60 Days Past Due', amount: apAging?.days_31_60_paise || 0, color: 'text-orange-600' },
                  { label: '61–90 Days Past Due', amount: apAging?.days_61_90_paise || 0, color: 'text-rose-600' },
                  { label: '91+ Days Past Due', amount: apAging?.days_91_plus_paise || 0, color: 'text-red-700 font-bold' },
                ].map(({ label, amount, color }) => (
                  <div key={label} className="flex justify-between items-center py-2 border-b border-gray-100 dark:border-gray-800 text-sm">
                    <span className="text-gray-600 dark:text-gray-400">{label}</span>
                    <span className={`font-semibold ${color}`}>₹{(amount / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                  </div>
                ))}
                <div className="flex justify-between items-center pt-2 font-bold text-gray-900 dark:text-white">
                  <span>Total Outstanding AP</span>
                  <span>₹{((apAging?.total_outstanding_paise || 0) / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                </div>
              </div>
            </Card>
          </div>
        </div>
      )}

      {/* TAB 7: ACTIVITY LOG */}
      {activeTab === 'activity' && (
        <Card className="p-5">
          <h3 className="font-semibold text-gray-900 dark:text-white mb-4">Commercial Operations Audit Trail</h3>
          {activities.length === 0 ? (
            <div className="text-center py-8 text-sm text-gray-500">No activity recorded yet.</div>
          ) : (
            <div className="space-y-4">
              {activities.map((a) => (
                <div key={a.id} className="flex items-start gap-3 pb-3 border-b border-gray-100 dark:border-gray-800 last:border-0">
                  <div className="p-2 bg-gray-100 dark:bg-gray-800 rounded-full mt-0.5">
                    <Clock className="h-4 w-4 text-gray-500" />
                  </div>
                  <div className="flex-1">
                    <div className="text-sm font-medium text-gray-900 dark:text-white">{a.description}</div>
                    <div className="text-xs text-gray-500 flex items-center gap-2 mt-0.5">
                      <span className="font-mono uppercase text-[10px] bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded">
                        {a.activity_type}
                      </span>
                      <span>{new Date(a.created_at).toLocaleString('en-IN')}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {/* MODAL 1: CREATE INVOICE */}
      <Modal isOpen={isInvoiceModalOpen} onClose={() => setIsInvoiceModalOpen(false)} title="Create Commercial Tax Invoice">
        <form onSubmit={handleCreateInvoiceSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase mb-1">Select Client *</label>
            <select
              value={invoiceForm.clientId}
              onChange={(e) => setInvoiceForm({ ...invoiceForm, clientId: e.target.value })}
              className="w-full text-sm border border-gray-300 dark:border-gray-700 rounded-lg p-2 dark:bg-gray-800"
              required
            >
              <option value="">-- Choose a Client --</option>
              {clients.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} {c.gstin ? `(${c.gstin})` : ''}
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase mb-1">Invoice Date</label>
              <Input
                type="date"
                value={invoiceForm.invoiceDate}
                onChange={(e) => setInvoiceForm({ ...invoiceForm, invoiceDate: e.target.value })}
                required
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase mb-1">Due Date</label>
              <Input
                type="date"
                value={invoiceForm.dueDate}
                onChange={(e) => setInvoiceForm({ ...invoiceForm, dueDate: e.target.value })}
                required
              />
            </div>
          </div>

          <div className="flex items-center gap-2 pt-1">
            <input
              type="checkbox"
              id="interstate"
              checked={invoiceForm.isInterstate}
              onChange={(e) => setInvoiceForm({ ...invoiceForm, isInterstate: e.target.checked })}
              className="rounded text-brand-600"
            />
            <label htmlFor="interstate" className="text-xs text-gray-700 dark:text-gray-300">
              Inter-state supply (IGST instead of CGST + SGST)
            </label>
          </div>

          {/* Line Items */}
          <div className="space-y-3 pt-2 border-t border-gray-200 dark:border-gray-700">
            <div className="flex justify-between items-center">
              <span className="text-xs font-bold uppercase text-gray-700 dark:text-gray-300">Line Items</span>
              <Button type="button" variant="outline" size="sm" onClick={handleAddLineItem}>
                + Add Line
              </Button>
            </div>

            {invoiceForm.lineItems.map((item, idx) => (
              <div key={idx} className="p-3 bg-gray-50 dark:bg-gray-800/40 rounded-lg space-y-2 border border-gray-200 dark:border-gray-700">
                <div className="flex justify-between items-center">
                  <span className="text-xs font-semibold">Item #{idx + 1}</span>
                  {invoiceForm.lineItems.length > 1 && (
                    <button
                      type="button"
                      onClick={() => handleRemoveLineItem(idx)}
                      className="text-xs text-rose-600 hover:underline"
                    >
                      Remove
                    </button>
                  )}
                </div>
                <Input
                  placeholder="Service description"
                  value={item.description}
                  onChange={(e) => handleLineItemChange(idx, 'description', e.target.value)}
                  required
                />
                <div className="grid grid-cols-4 gap-2">
                  <div>
                    <label className="text-[10px] uppercase text-gray-500">HSN/SAC</label>
                    <Input
                      placeholder="998311"
                      value={item.hsnSacCode}
                      onChange={(e) => handleLineItemChange(idx, 'hsnSacCode', e.target.value)}
                    />
                  </div>
                  <div>
                    <label className="text-[10px] uppercase text-gray-500">Qty</label>
                    <Input
                      type="number"
                      step="0.01"
                      value={item.quantity}
                      onChange={(e) => handleLineItemChange(idx, 'quantity', e.target.value)}
                      required
                    />
                  </div>
                  <div>
                    <label className="text-[10px] uppercase text-gray-500">Price (₹)</label>
                    <Input
                      type="number"
                      step="0.01"
                      value={item.unitPrice}
                      onChange={(e) => handleLineItemChange(idx, 'unitPrice', e.target.value)}
                      required
                    />
                  </div>
                  <div>
                    <label className="text-[10px] uppercase text-gray-500">GST %</label>
                    <select
                      value={item.taxRatePercent}
                      onChange={(e) => handleLineItemChange(idx, 'taxRatePercent', e.target.value)}
                      className="w-full text-xs border border-gray-300 dark:border-gray-700 rounded-lg p-2 dark:bg-gray-800"
                    >
                      <option value="0">0%</option>
                      <option value="5">5%</option>
                      <option value="12">12%</option>
                      <option value="18">18%</option>
                      <option value="28">28%</option>
                    </select>
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="flex justify-end gap-2 pt-4 border-t border-gray-200 dark:border-gray-700">
            <Button type="button" variant="outline" onClick={() => setIsInvoiceModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              Save Draft Invoice
            </Button>
          </div>
        </form>
      </Modal>

      {/* MODAL 2: RECORD PAYMENT */}
      <Modal isOpen={isPaymentModalOpen} onClose={() => setIsPaymentModalOpen(false)} title="Record Invoice Payment">
        <form onSubmit={handleRecordPaymentSubmit} className="space-y-4">
          <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg text-sm">
            Invoice: <strong>{selectedInvoice?.invoice_number}</strong> &bull; Total:{' '}
            <strong>₹{((selectedInvoice?.total_amount_paise || 0) / 100).toLocaleString('en-IN')}</strong>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase mb-1">Amount Received (₹) *</label>
            <Input
              type="number"
              step="0.01"
              value={paymentForm.amount}
              onChange={(e) => setPaymentForm({ ...paymentForm, amount: e.target.value })}
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase mb-1">Payment Date</label>
              <Input
                type="date"
                value={paymentForm.paymentDate}
                onChange={(e) => setPaymentForm({ ...paymentForm, paymentDate: e.target.value })}
                required
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase mb-1">Payment Method</label>
              <select
                value={paymentForm.paymentMethod}
                onChange={(e) => setPaymentForm({ ...paymentForm, paymentMethod: e.target.value })}
                className="w-full text-sm border border-gray-300 dark:border-gray-700 rounded-lg p-2 dark:bg-gray-800"
              >
                <option value="bank_transfer">Bank Transfer (NEFT/RTGS/IMPS)</option>
                <option value="upi">UPI / QR Code</option>
                <option value="cheque">Cheque</option>
                <option value="card">Credit/Debit Card</option>
                <option value="cash">Cash</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase mb-1">Reference / UTR Number</label>
            <Input
              placeholder="e.g. UTR-20261114-12345"
              value={paymentForm.referenceNumber}
              onChange={(e) => setPaymentForm({ ...paymentForm, referenceNumber: e.target.value })}
            />
          </div>

          <div className="flex justify-end gap-2 pt-4 border-t border-gray-200 dark:border-gray-700">
            <Button type="button" variant="outline" onClick={() => setIsPaymentModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              Confirm Payment
            </Button>
          </div>
        </form>
      </Modal>

      {/* MODAL 3: ADD CLIENT */}
      <Modal isOpen={isClientModalOpen} onClose={() => setIsClientModalOpen(false)} title="Add Client Profile">
        <form onSubmit={handleCreateClientSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase mb-1">Client Name *</label>
            <Input
              placeholder="Acme Corp / John Doe"
              value={clientForm.name}
              onChange={(e) => setClientForm({ ...clientForm, name: e.target.value })}
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase mb-1">Client Type</label>
              <select
                value={clientForm.clientType}
                onChange={(e) => setClientForm({ ...clientForm, clientType: e.target.value })}
                className="w-full text-sm border border-gray-300 dark:border-gray-700 rounded-lg p-2 dark:bg-gray-800"
              >
                <option value="business">Business / Corporate</option>
                <option value="individual">Individual</option>
                <option value="organization">Non-Profit / Organization</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase mb-1">Credit Terms (Days)</label>
              <Input
                type="number"
                value={clientForm.paymentTermsDays}
                onChange={(e) => setClientForm({ ...clientForm, paymentTermsDays: Number(e.target.value) })}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase mb-1">Email</label>
              <Input
                type="email"
                placeholder="billing@client.com"
                value={clientForm.email}
                onChange={(e) => setClientForm({ ...clientForm, email: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase mb-1">Phone</label>
              <Input
                placeholder="+91 98765 43210"
                value={clientForm.phone}
                onChange={(e) => setClientForm({ ...clientForm, phone: e.target.value })}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase mb-1">GSTIN (Optional)</label>
              <Input
                placeholder="27AAPFU0939F1ZV"
                value={clientForm.gstin}
                onChange={(e) => setClientForm({ ...clientForm, gstin: e.target.value.toUpperCase() })}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase mb-1">PAN (Optional)</label>
              <Input
                placeholder="ABCDE1234F"
                value={clientForm.pan}
                onChange={(e) => setClientForm({ ...clientForm, pan: e.target.value.toUpperCase() })}
              />
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-4 border-t border-gray-200 dark:border-gray-700">
            <Button type="button" variant="outline" onClick={() => setIsClientModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              Save Client
            </Button>
          </div>
        </form>
      </Modal>

      {/* MODAL 4: ADD VENDOR */}
      <Modal isOpen={isVendorModalOpen} onClose={() => setIsVendorModalOpen(false)} title="Register Business Vendor">
        <form onSubmit={handleCreateVendorSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase mb-1">Vendor Name *</label>
            <Input
              placeholder="Cloud Hosting / Freelance Dev"
              value={vendorForm.name}
              onChange={(e) => setVendorForm({ ...vendorForm, name: e.target.value })}
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase mb-1">Vendor Type</label>
              <select
                value={vendorForm.vendorType}
                onChange={(e) => setVendorForm({ ...vendorForm, vendorType: e.target.value })}
                className="w-full text-sm border border-gray-300 dark:border-gray-700 rounded-lg p-2 dark:bg-gray-800"
              >
                <option value="service_provider">Service Provider</option>
                <option value="software_saas">Software & SaaS</option>
                <option value="contractor">Subcontractor</option>
                <option value="utility">Utility / Broadband</option>
                <option value="landlord">Landlord / Rent</option>
                <option value="other">Other</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase mb-1">Credit Terms (Days)</label>
              <Input
                type="number"
                value={vendorForm.paymentTermsDays}
                onChange={(e) => setVendorForm({ ...vendorForm, paymentTermsDays: Number(e.target.value) })}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase mb-1">Email</label>
              <Input
                type="email"
                placeholder="accounts@vendor.com"
                value={vendorForm.email}
                onChange={(e) => setVendorForm({ ...vendorForm, email: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase mb-1">GSTIN</label>
              <Input
                placeholder="27AAPFU0939F1ZV"
                value={vendorForm.gstin}
                onChange={(e) => setVendorForm({ ...vendorForm, gstin: e.target.value.toUpperCase() })}
              />
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-4 border-t border-gray-200 dark:border-gray-700">
            <Button type="button" variant="outline" onClick={() => setIsVendorModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              Register Vendor
            </Button>
          </div>
        </form>
      </Modal>

      {/* MODAL 5: RECORD PAYABLE */}
      <Modal isOpen={isPayableModalOpen} onClose={() => setIsPayableModalOpen(false)} title="Record Vendor Bill">
        <form onSubmit={handleCreatePayableSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase mb-1">Select Vendor *</label>
            <select
              value={payableForm.vendorId}
              onChange={(e) => setPayableForm({ ...payableForm, vendorId: e.target.value })}
              className="w-full text-sm border border-gray-300 dark:border-gray-700 rounded-lg p-2 dark:bg-gray-800"
              required
            >
              <option value="">-- Choose a Vendor --</option>
              {vendors.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.name}
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase mb-1">Bill / Invoice Number</label>
              <Input
                placeholder="BILL-987"
                value={payableForm.billNumber}
                onChange={(e) => setPayableForm({ ...payableForm, billNumber: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase mb-1">Due Date</label>
              <Input
                type="date"
                value={payableForm.dueDate}
                onChange={(e) => setPayableForm({ ...payableForm, dueDate: e.target.value })}
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase mb-1">Subtotal (₹) *</label>
              <Input
                type="number"
                step="0.01"
                placeholder="10000"
                value={payableForm.subtotal}
                onChange={(e) => setPayableForm({ ...payableForm, subtotal: e.target.value })}
                required
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase mb-1">Tax / GST (₹)</label>
              <Input
                type="number"
                step="0.01"
                placeholder="1800"
                value={payableForm.tax}
                onChange={(e) => setPayableForm({ ...payableForm, tax: e.target.value })}
              />
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-4 border-t border-gray-200 dark:border-gray-700">
            <Button type="button" variant="outline" onClick={() => setIsPayableModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              Record Bill
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

export default Business;
