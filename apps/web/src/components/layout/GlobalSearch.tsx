import React, { useState, useEffect, useRef, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  X,
  Receipt,
  Landmark,
  Target,
  Trophy,
  FileText,
  Briefcase,
  Users,
  Repeat,
  TrendingUp,
  ShieldAlert,
  ArrowRight,
  BookOpen,
} from 'lucide-react';
import useAccountStore from '@/store/useAccountStore';
import useTransactionStore from '@/store/useTransactionStore';
import { useBudgetStore } from '@/store/useBudgetStore';
import { useGoalStore } from '@/store/useGoalStore';
import { useBusinessStore } from '@/store/useBusinessStore';
import { useDocumentStore } from '@/store/useDocumentStore';

interface SearchResultItem {
  id: string;
  title: string;
  subtitle: string;
  category: 'Pages' | 'Accounts' | 'Transactions' | 'Budgets' | 'Goals' | 'Invoices' | 'Documents';
  icon: React.ReactNode;
  path: string;
}

const STATIC_PAGES: SearchResultItem[] = [
  { id: 'p-dash', title: 'Analytics & Financial Overview', subtitle: 'View income, spending, and cash flow', category: 'Pages', icon: <TrendingUp size={14} />, path: '/dashboard' },
  { id: 'p-acc', title: 'Financial Accounts & Institutions', subtitle: 'Manage bank accounts, cards, and balances', category: 'Pages', icon: <Landmark size={14} />, path: '/accounts' },
  { id: 'p-tx', title: 'Transaction Ledger & History', subtitle: 'Search, filter, and review verified transactions', category: 'Pages', icon: <Receipt size={14} />, path: '/transactions' },
  { id: 'p-ledger', title: 'Double-Entry General Ledger', subtitle: 'Journal entries and balanced ledger accounts', category: 'Pages', icon: <BookOpen size={14} />, path: '/ledger' },
  { id: 'p-bud', title: 'Monthly Spending Budgets', subtitle: 'Track category allocations and thresholds', category: 'Pages', icon: <Target size={14} />, path: '/budgets' },
  { id: 'p-goal', title: 'Financial Goals & Milestones', subtitle: 'Savings velocity and goal tracking', category: 'Pages', icon: <Trophy size={14} />, path: '/goals' },
  { id: 'p-rec', title: 'Recurring Commitments & Subscriptions', subtitle: 'Predictive bills and subscription renewals', category: 'Pages', icon: <Repeat size={14} />, path: '/recurring' },
  { id: 'p-fore', title: 'Cash-Flow Forecasting & Scenarios', subtitle: 'Time-series predictions and projections', category: 'Pages', icon: <TrendingUp size={14} />, path: '/forecast' },
  { id: 'p-anom', title: 'Anomaly Detection & Risk Intelligence', subtitle: 'Flagged spending anomalies and fraud signals', category: 'Pages', icon: <ShieldAlert size={14} />, path: '/anomalies' },
  { id: 'p-doc', title: 'Receipt Intelligence & OCR', subtitle: 'Scan receipts and extract structured lines', category: 'Pages', icon: <FileText size={14} />, path: '/documents' },
  { id: 'p-fam', title: 'Family Household Finance', subtitle: 'Shared budgets, expenses, and contributions', category: 'Pages', icon: <Users size={14} />, path: '/family' },
  { id: 'p-biz', title: 'Small Business Commercial Hub', subtitle: 'Invoices, clients, vendors, and payables', category: 'Pages', icon: <Briefcase size={14} />, path: '/business' },
  { id: 'p-rep', title: 'Financial Reporting & Tax Intelligence', subtitle: 'P&L, Balance Sheet, GST readiness, and Indian tax estimation', category: 'Pages', icon: <FileText size={14} />, path: '/reports' },
];

export const GlobalSearch: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);

  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);

  // Store data hooks for workspace-scoped search
  const { accounts } = useAccountStore();
  const { transactions } = useTransactionStore();
  const { budgets } = useBudgetStore();
  const { goals } = useGoalStore();
  const { invoices } = useBusinessStore();
  const { documents } = useDocumentStore();

  // Keyboard shortcut listener (Ctrl+K or Cmd+K)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setIsOpen((prev) => !prev);
      } else if (e.key === 'Escape' && isOpen) {
        setIsOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen]);

  // Focus input on open
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
      setSelectedIndex(0);
    } else {
      setQuery('');
    }
  }, [isOpen]);

  // Dynamic search aggregation
  const results: SearchResultItem[] = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) {
      // Suggest top navigation pages when query is empty
      return STATIC_PAGES.slice(0, 6);
    }

    const matched: SearchResultItem[] = [];

    // 1. Pages
    STATIC_PAGES.forEach((page) => {
      if (page.title.toLowerCase().includes(q) || page.subtitle.toLowerCase().includes(q)) {
        matched.push(page);
      }
    });

    // 2. Accounts
    accounts.forEach((acc) => {
      if (acc.name.toLowerCase().includes(q) || acc.institution_name?.toLowerCase().includes(q)) {
        matched.push({
          id: `acc-${acc.id}`,
          title: acc.name,
          subtitle: `${acc.institution_name || 'Bank'} • ₹${((acc.current_book_balance_paise || 0) / 100).toLocaleString('en-IN')}`,
          category: 'Accounts',
          icon: <Landmark size={14} />,
          path: '/accounts',
        });
      }
    });

    // 3. Transactions
    transactions.slice(0, 50).forEach((tx) => {
      if (
        tx.description?.toLowerCase().includes(q) ||
        tx.merchant_name?.toLowerCase().includes(q)
      ) {
        matched.push({
          id: `tx-${tx.id}`,
          title: tx.merchant_name || tx.description || 'Transaction',
          subtitle: `Transaction • ₹${((tx.amount_paise || 0) / 100).toLocaleString('en-IN')}`,
          category: 'Transactions',
          icon: <Receipt size={14} />,
          path: '/transactions',
        });
      }
    });

    // 4. Budgets
    budgets.forEach((b: any) => {
      if (b.name?.toLowerCase().includes(q) || b.category?.toLowerCase().includes(q)) {
        matched.push({
          id: `bud-${b.id}`,
          title: b.name || `${b.category} Budget`,
          subtitle: `Limit: ₹${((b.limit_paise || 0) / 100).toLocaleString('en-IN')}`,
          category: 'Budgets',
          icon: <Target size={14} />,
          path: '/budgets',
        });
      }
    });

    // 5. Goals
    goals.forEach((g: any) => {
      if (g.name?.toLowerCase().includes(q)) {
        matched.push({
          id: `goal-${g.id}`,
          title: g.name,
          subtitle: `Target: ₹${((g.target_paise || 0) / 100).toLocaleString('en-IN')}`,
          category: 'Goals',
          icon: <Trophy size={14} />,
          path: '/goals',
        });
      }
    });

    // 6. Invoices
    (invoices || []).forEach((inv: any) => {
      if (inv.invoice_number?.toLowerCase().includes(q) || inv.client_name?.toLowerCase().includes(q)) {
        matched.push({
          id: `inv-${inv.id}`,
          title: `Invoice #${inv.invoice_number}`,
          subtitle: `${inv.client_name || 'Client'} • ₹${((inv.total_amount_paise || 0) / 100).toLocaleString('en-IN')}`,
          category: 'Invoices',
          icon: <Briefcase size={14} />,
          path: '/business',
        });
      }
    });

    // 7. Documents
    (documents || []).forEach((doc: any) => {
      if (doc.filename?.toLowerCase().includes(q) || doc.extracted_merchant?.toLowerCase().includes(q)) {
        matched.push({
          id: `doc-${doc.id}`,
          title: doc.extracted_merchant || doc.filename,
          subtitle: `Document OCR • Status: ${doc.status}`,
          category: 'Documents',
          icon: <FileText size={14} />,
          path: '/documents',
        });
      }
    });

    return matched.slice(0, 15);
  }, [query, accounts, transactions, budgets, goals, invoices, documents]);

  // Keyboard navigation inside results list
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev < results.length - 1 ? prev + 1 : 0));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev > 0 ? prev - 1 : results.length - 1));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (results[selectedIndex]) {
        navigate(results[selectedIndex].path);
        setIsOpen(false);
      }
    }
  };

  const handleSelect = (item: SearchResultItem) => {
    navigate(item.path);
    setIsOpen(false);
  };

  return (
    <>
      {/* Top Bar Trigger Button */}
      <button
        type="button"
        onClick={() => setIsOpen(true)}
        aria-label="Search financial records (Ctrl+K)"
        className="flex items-center gap-2.5 px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-400 hover:text-white transition-all text-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 w-44 sm:w-64"
      >
        <Search size={14} className="text-slate-500 shrink-0" />
        <span className="truncate flex-1 text-left">Search records...</span>
        <kbd className="hidden sm:inline-flex items-center gap-0.5 rounded border border-slate-800 bg-slate-950 px-1.5 py-0.5 text-[10px] font-mono text-slate-500">
          <span className="text-[9px]">Ctrl</span>K
        </kbd>
      </button>

      {/* Global Search Modal */}
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-start justify-center pt-16 sm:pt-24 p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-150">
          <div
            role="dialog"
            aria-modal="true"
            aria-label="Global Financial Search"
            className="w-full max-w-xl rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl overflow-hidden animate-in zoom-in-95 duration-150 flex flex-col max-h-[80vh]"
          >
            {/* Input Bar */}
            <div className="flex items-center gap-3 px-4 py-3.5 border-b border-slate-800">
              <Search size={18} className="text-indigo-400 shrink-0" />
              <input
                ref={inputRef}
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  setSelectedIndex(0);
                }}
                onKeyDown={handleKeyDown}
                placeholder="Search transactions, accounts, invoices, budgets..."
                className="w-full bg-transparent text-sm text-white placeholder:text-slate-500 focus:outline-none"
              />
              {query && (
                <button
                  type="button"
                  onClick={() => setQuery('')}
                  className="text-slate-500 hover:text-white p-1 rounded-md"
                >
                  <X size={16} />
                </button>
              )}
              <kbd className="text-[10px] font-mono bg-slate-950 px-2 py-1 rounded border border-slate-800 text-slate-400">
                ESC
              </kbd>
            </div>

            {/* Results List */}
            <div className="overflow-y-auto p-2 divide-y divide-slate-800/50 flex-1">
              {results.length > 0 ? (
                results.map((item, idx) => {
                  const isSelected = idx === selectedIndex;
                  return (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => handleSelect(item)}
                      onMouseEnter={() => setSelectedIndex(idx)}
                      className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-left text-xs transition-colors ${
                        isSelected
                          ? 'bg-indigo-600 text-white shadow-sm'
                          : 'text-slate-300 hover:bg-slate-800/60 hover:text-white'
                      }`}
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <div
                          className={`p-1.5 rounded-lg shrink-0 ${
                            isSelected ? 'bg-indigo-700 text-white' : 'bg-slate-800 text-slate-400'
                          }`}
                        >
                          {item.icon}
                        </div>
                        <div className="truncate">
                          <p className="font-semibold truncate leading-tight">{item.title}</p>
                          <p className={`text-[11px] truncate mt-0.5 ${isSelected ? 'text-indigo-200' : 'text-slate-400'}`}>
                            {item.subtitle}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 shrink-0 ml-3">
                        <span
                          className={`text-[9px] font-mono uppercase px-1.5 py-0.5 rounded border ${
                            isSelected
                              ? 'bg-indigo-500/30 border-indigo-300/40 text-white'
                              : 'bg-slate-800 border-slate-700 text-slate-400'
                          }`}
                        >
                          {item.category}
                        </span>
                        <ArrowRight size={12} className={isSelected ? 'text-white' : 'text-slate-600'} />
                      </div>
                    </button>
                  );
                })
              ) : (
                <div className="py-8 text-center text-xs text-slate-500">
                  <Search size={24} className="mx-auto text-slate-600 mb-2" />
                  <p className="font-medium text-slate-400">No financial records match &quot;{query}&quot;</p>
                  <p className="text-[11px] text-slate-500 mt-1">Try searching by merchant name, account title, or invoice number.</p>
                </div>
              )}
            </div>

            {/* Footer Navigation Hints */}
            <div className="px-4 py-2 border-t border-slate-800 bg-slate-950/60 flex items-center justify-between text-[11px] text-slate-500 font-mono">
              <div className="flex items-center gap-3">
                <span>↑↓ Navigate</span>
                <span>↵ Open</span>
              </div>
              <span>Workspace-Scoped</span>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default GlobalSearch;
