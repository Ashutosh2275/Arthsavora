import React, { useEffect, useState } from 'react';
import useExpenseStore from '@/store/useExpenseStore';
import api from '@/lib/axios';
import {
  Wallet,
  Calendar,
  Sparkles,
  Utensils,
  Plane,
  ShoppingBag,
  Receipt,
  Camera,
  Trash2,
  Tag,
  Zap,
} from 'lucide-react';
import { formatINR, formatDateINR } from '@arthsavora/utilities';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import type { ExpenseCategory, OcrReceiptResponse } from '@arthsavora/contracts';

export default function Expenses() {
  const { expenses, fetchExpenses, addExpense, deleteExpense, parseSMS } = useExpenseStore();
  const [form, setForm] = useState<{ amount: string; description: string; category: ExpenseCategory }>({
    amount: '',
    description: '',
    category: 'Shopping',
  });
  const [showAI, setShowAI] = useState(false);
  const [smsInput, setSmsInput] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    fetchExpenses();
  }, [fetchExpenses]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.amount || !form.description) return;
    setIsSubmitting(true);

    try {
      const res = await addExpense({
        amount: parseFloat(form.amount),
        description: form.description,
        category: form.category,
      });

      if (res.success) {
        toast.success('Transaction saved');
        setForm({ amount: '', description: '', category: 'Shopping' });
      } else {
        toast.error('Failed to save transaction');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleAIParsing = async () => {
    if (!smsInput.trim()) return;
    setIsProcessing(true);

    try {
      const res = await parseSMS(smsInput);
      if (res.success && res.data) {
        setForm({
          amount: res.data.amount.toString(),
          description: res.data.description,
          category: res.data.category,
        });
        setShowAI(false);
        setSmsInput('');
        toast.success('SMS parsed successfully');
      } else {
        toast.error('Could not extract transaction data from SMS');
      }
    } finally {
      setIsProcessing(false);
    }
  };

  const handleOCRScan = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      toast.error('Please upload an image file (PNG/JPG)');
      return;
    }

    setIsProcessing(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await api.post<OcrReceiptResponse>('/ml/scan-receipt', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setForm({
        amount: res.data.amount.toString(),
        description: res.data.description,
        category: res.data.category,
      });
      setShowAI(false);
      toast.success('Receipt processed successfully');
    } catch {
      toast.error('Receipt scanning failed. Please verify OCR service.');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDelete = async (id: string) => {
    const success = await deleteExpense(id);
    if (success) {
      toast.success('Transaction deleted');
    } else {
      toast.error('Failed to delete transaction');
    }
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'Food':
        return <Utensils size={14} className="text-orange-400" />;
      case 'Travel':
        return <Plane size={14} className="text-blue-400" />;
      case 'Shopping':
        return <ShoppingBag size={14} className="text-emerald-400" />;
      case 'Bills':
        return <Receipt size={14} className="text-rose-400" />;
      default:
        return <Tag size={14} className="text-slate-400" />;
    }
  };

  return (
    <div className="space-y-8">
      <header className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <Wallet className="text-indigo-400" size={24} /> Expense Ledger
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Track transactions, parse bank SMS alerts, and process receipts.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setShowAI(!showAI)}
          className="gap-2 border-indigo-500/30 text-indigo-400 hover:bg-indigo-600/20"
        >
          <Sparkles size={16} />
          <span>{showAI ? 'Close Smart Import' : 'AI Smart Import'}</span>
        </Button>
      </header>

      {/* AI Smart Import Panel */}
      {showAI && (
        <Card className="border-indigo-500/30 bg-slate-900/90 p-6 animate-in zoom-in-95 duration-200">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="space-y-3 md:border-r md:border-slate-800 md:pr-8">
              <div className="flex items-center gap-2 text-indigo-400 text-xs font-bold uppercase tracking-wider">
                <Zap size={14} /> SMS Parser
              </div>
              <textarea
                className="w-full rounded-xl border border-slate-700 bg-slate-950 p-3.5 text-xs text-white outline-none focus:border-indigo-500 placeholder-slate-600"
                placeholder="Paste bank notification SMS... e.g. 'Paid Rs.450.00 to Swiggy on 12-Nov'"
                rows={4}
                value={smsInput}
                onChange={(e) => setSmsInput(e.target.value)}
              />
              <Button
                size="sm"
                className="w-full gap-2"
                onClick={handleAIParsing}
                isLoading={isProcessing}
              >
                <span>Extract Transaction</span>
              </Button>
            </div>

            <div className="flex flex-col items-center justify-center text-center">
              <div className="flex items-center gap-2 text-indigo-400 text-xs font-bold uppercase tracking-wider mb-4">
                <Camera size={14} /> Receipt Vision (OCR)
              </div>
              <label className="flex h-36 w-full cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-700 bg-slate-950 transition-all hover:border-indigo-500/50">
                <Camera size={32} className="text-slate-600 mb-2" />
                <span className="text-xs font-semibold text-slate-400">Upload Receipt Image</span>
                <span className="text-[10px] text-slate-600 mt-1">PNG, JPG up to 5MB</span>
                <input type="file" className="hidden" accept="image/*" onChange={handleOCRScan} />
              </label>
            </div>
          </div>
        </Card>
      )}

      {/* Manual Entry Form */}
      <Card>
        <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
          <Input
            label="Amount (₹)"
            type="number"
            step="0.01"
            placeholder="0.00"
            value={form.amount}
            onChange={(e) => setForm({ ...form, amount: e.target.value })}
            required
          />

          <div className="md:col-span-2">
            <Input
              label="Description / Merchant"
              placeholder="e.g. Starbucks, Electricity Bill"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              required
            />
          </div>

          <Button type="submit" size="md" className="w-full" isLoading={isSubmitting}>
            Save Entry
          </Button>
        </form>
      </Card>

      {/* Transaction List */}
      <div className="space-y-3">
        {expenses.map((expense) => {
          const expenseId = expense.id || (expense as { _id?: string })._id || '';
          return (
            <div
              key={expenseId}
              className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-900/40 p-4 transition-all hover:border-slate-700"
            >
              <div className="flex items-center gap-4">
                <div className="rounded-xl bg-slate-800/80 p-2.5">
                  {getCategoryIcon(expense.category)}
                </div>
                <div>
                  <h4 className="text-sm font-semibold text-white capitalize">{expense.description}</h4>
                  <div className="flex items-center gap-3 text-xs text-slate-500 mt-0.5">
                    <span>
                      <Calendar size={12} className="inline mr-1 text-slate-500" />
                      {formatDateINR(expense.date)}
                    </span>
                    <Badge variant="neutral">{expense.category}</Badge>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-6">
                <span className="font-mono text-base font-bold text-indigo-400">
                  {formatINR(expense.amount)}
                </span>
                <button
                  onClick={() => handleDelete(expenseId)}
                  className="rounded-lg p-1.5 text-slate-500 hover:bg-rose-500/10 hover:text-rose-400 transition-all"
                  aria-label="Delete expense"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          );
        })}

        {expenses.length === 0 && (
          <div className="py-16 text-center text-xs text-slate-500">
            No transactions logged yet. Add your first expense above.
          </div>
        )}
      </div>
    </div>
  );
}
