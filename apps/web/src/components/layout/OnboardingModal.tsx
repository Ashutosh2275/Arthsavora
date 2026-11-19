import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  Building,
  Landmark,
  ArrowRight,
  CheckCircle,
  Sparkles,
  User,
  Users,
  Briefcase,
  X,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import useAuthStore from '@/store/useAuthStore';
import useWorkspaceStore from '@/store/useWorkspaceStore';
import { toast } from 'sonner';

export const OnboardingModal: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [step, setStep] = useState(1);
  const { user } = useAuthStore();
  const { createWorkspace, activeWorkspace } = useWorkspaceStore();

  const [fullName, setFullName] = useState(user?.full_name || '');
  const [workspaceName, setWorkspaceName] = useState('Personal Vault');
  const [workspaceType, setWorkspaceType] = useState<'personal' | 'family' | 'business'>('personal');
  const [preferredCurrency, setPreferredCurrency] = useState('INR');
  const [timezone, setTimezone] = useState('Asia/Kolkata');

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const onboarded = localStorage.getItem('arth_onboarded_completed');
      if (!onboarded) {
        setIsOpen(true);
      }
    }
  }, []);

  const handleFinish = () => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('arth_onboarded_completed', 'true');
    }
    setIsOpen(false);
    toast.success('Onboarding complete! Welcome to ARTHSAVORA.');
  };

  const handleNextStep = async () => {
    if (step === 2) {
      // Create initial workspace if none active
      if (!activeWorkspace) {
        try {
          await createWorkspace({
            name: workspaceName || 'Personal Workspace',
            type: workspaceType,
            currency: preferredCurrency as any,
            timezone,
            country: 'IN',
          });
        } catch {
          // ignore error if workspace already exists
        }
      }
    }
    setStep((prev) => prev + 1);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in">
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Welcome Onboarding"
        className="w-full max-w-lg rounded-3xl bg-slate-900 border border-slate-800 shadow-2xl p-6 sm:p-8 space-y-6 relative overflow-hidden"
      >
        {/* Progress Bar */}
        <div className="flex items-center justify-between gap-2 border-b border-slate-800 pb-4">
          <div className="flex items-center gap-2">
            <div className="rounded-xl bg-indigo-600 p-1.5 text-white">
              <ShieldCheck size={18} />
            </div>
            <span className="text-xs font-black tracking-wider uppercase text-white">ARTHSAVORA ONBOARDING</span>
          </div>
          <div className="flex items-center gap-1.5 text-[11px] font-mono text-slate-400">
            <span>Step {step} of 4</span>
            <button
              onClick={handleFinish}
              className="text-slate-500 hover:text-slate-300 ml-2"
              title="Skip setup"
            >
              <X size={16} />
            </button>
          </div>
        </div>

        {/* Step 1: User Profile */}
        {step === 1 && (
          <div className="space-y-4">
            <div>
              <h3 className="text-xl font-bold text-white">Welcome, Financial Pioneer</h3>
              <p className="text-xs text-slate-400 mt-1">
                Configure your display name and baseline institutional locale parameters.
              </p>
            </div>
            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 font-medium mb-1">Your Full Name</label>
                <Input
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="e.g. Ashutosh Sharma"
                  autoFocus
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Preferred Currency</label>
                  <select
                    value={preferredCurrency}
                    onChange={(e) => setPreferredCurrency(e.target.value)}
                    className="w-full rounded-xl bg-slate-950 border border-slate-800 px-3 py-2 text-xs text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="INR">INR (₹ - Indian Rupee)</option>
                    <option value="USD">USD ($ - US Dollar)</option>
                    <option value="EUR">EUR (€ - Euro)</option>
                    <option value="GBP">GBP (£ - British Pound)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Jurisdiction Timezone</label>
                  <select
                    value={timezone}
                    onChange={(e) => setTimezone(e.target.value)}
                    className="w-full rounded-xl bg-slate-950 border border-slate-800 px-3 py-2 text-xs text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="Asia/Kolkata">Asia/Kolkata (IST)</option>
                    <option value="UTC">UTC (Universal Time)</option>
                    <option value="America/New_York">America/New_York (EST)</option>
                    <option value="Europe/London">Europe/London (GMT)</option>
                  </select>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Step 2: Workspace Setup */}
        {step === 2 && (
          <div className="space-y-4">
            <div>
              <h3 className="text-xl font-bold text-white">Initialize Your Financial Workspace</h3>
              <p className="text-xs text-slate-400 mt-1">
                Establish the tenancy boundary that best matches your immediate financial management goals.
              </p>
            </div>
            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 font-medium mb-1">Workspace Title</label>
                <Input
                  value={workspaceName}
                  onChange={(e) => setWorkspaceName(e.target.value)}
                  placeholder="e.g. Personal Wealth, Family Vault, Apex Consulting"
                />
              </div>
              <div>
                <label className="block text-slate-300 font-medium mb-1.5">Tenancy Type</label>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { id: 'personal', label: 'Personal', desc: 'Private Wealth', icon: <User size={16} /> },
                    { id: 'family', label: 'Family', desc: 'Household Vault', icon: <Users size={16} /> },
                    { id: 'business', label: 'Business', desc: 'Invoicing & GST', icon: <Briefcase size={16} /> },
                  ].map((t) => (
                    <button
                      key={t.id}
                      type="button"
                      onClick={() => setWorkspaceType(t.id as any)}
                      className={`p-3 rounded-2xl border text-left transition-all ${
                        workspaceType === t.id
                          ? 'border-indigo-500 bg-indigo-500/10 text-white font-semibold'
                          : 'border-slate-800 bg-slate-950 text-slate-400 hover:border-slate-700'
                      }`}
                    >
                      <div className="text-indigo-400 mb-1.5">{t.icon}</div>
                      <p className="font-semibold text-white">{t.label}</p>
                      <span className="text-[10px] text-slate-400">{t.desc}</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Step 3: Account Connectivity Overview */}
        {step === 3 && (
          <div className="space-y-4">
            <div>
              <h3 className="text-xl font-bold text-white">Bank Connectivity (Optional)</h3>
              <p className="text-xs text-slate-400 mt-1">
                Link bank accounts via RBI Account Aggregators (Setu, Anumati, OneMoney) or start with manual entry.
              </p>
            </div>
            <div className="space-y-2 text-xs">
              <div className="p-4 rounded-2xl border border-slate-800 bg-slate-950/60 flex items-start gap-3">
                <Landmark size={20} className="text-indigo-400 shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-semibold text-white">Zero Obligation Connectivity</h4>
                  <p className="text-slate-400 text-[11px] mt-0.5 leading-relaxed">
                    You do not need to link a bank account. You can manually record transactions, upload Excel/PDF statements, or scan receipts with OCR.
                  </p>
                </div>
              </div>
              <div className="p-4 rounded-2xl border border-slate-800 bg-slate-950/60 flex items-start gap-3">
                <ShieldCheck size={20} className="text-emerald-400 shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-semibold text-white">End-to-End Cryptographic Privacy</h4>
                  <p className="text-slate-400 text-[11px] mt-0.5 leading-relaxed">
                    Account Aggregator consent tokens are client-approved, time-bound, and never expose login passwords or OTPs.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Step 4: Ready to Launch */}
        {step === 4 && (
          <div className="space-y-4 text-center py-2">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-indigo-600 to-indigo-400 text-white flex items-center justify-center mx-auto shadow-xl shadow-indigo-600/30">
              <Sparkles size={28} />
            </div>
            <div>
              <h3 className="text-2xl font-bold text-white">You Are Ready</h3>
              <p className="text-xs text-slate-400 mt-1.5 max-w-sm mx-auto">
                Your workspace is configured. Leverage real double-entry ledgers, automated anomaly detection, and conversational AI intelligence.
              </p>
            </div>
            <div className="grid grid-cols-2 gap-2 text-left text-xs max-w-md mx-auto pt-2">
              <div className="p-2.5 rounded-xl bg-slate-950 border border-slate-800 flex items-center gap-2">
                <CheckCircle size={14} className="text-emerald-400 shrink-0" />
                <span className="text-slate-300">Double-Entry Ledger</span>
              </div>
              <div className="p-2.5 rounded-xl bg-slate-950 border border-slate-800 flex items-center gap-2">
                <CheckCircle size={14} className="text-emerald-400 shrink-0" />
                <span className="text-slate-300">GST &amp; Tax Readiness</span>
              </div>
              <div className="p-2.5 rounded-xl bg-slate-950 border border-slate-800 flex items-center gap-2">
                <CheckCircle size={14} className="text-emerald-400 shrink-0" />
                <span className="text-slate-300">Predictive Cash Flow</span>
              </div>
              <div className="p-2.5 rounded-xl bg-slate-950 border border-slate-800 flex items-center gap-2">
                <CheckCircle size={14} className="text-emerald-400 shrink-0" />
                <span className="text-slate-300">Autonomous Assistant</span>
              </div>
            </div>
          </div>
        )}

        {/* Actions Footer */}
        <div className="flex items-center justify-between pt-4 border-t border-slate-800">
          {step > 1 ? (
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setStep((prev) => prev - 1)}
            >
              Back
            </Button>
          ) : (
            <button
              type="button"
              onClick={handleFinish}
              className="text-xs text-slate-400 hover:text-slate-200"
            >
              Skip Setup
            </button>
          )}

          {step < 4 ? (
            <Button
              type="button"
              size="sm"
              onClick={handleNextStep}
              className="bg-indigo-600 hover:bg-indigo-500 text-white gap-1.5"
            >
              <span>Continue</span>
              <ArrowRight size={14} />
            </Button>
          ) : (
            <Button
              type="button"
              size="sm"
              onClick={handleFinish}
              className="bg-indigo-600 hover:bg-indigo-500 text-white font-bold px-6"
            >
              Enter Dashboard
            </Button>
          )}
        </div>
      </div>
    </div>
  );
};

export default OnboardingModal;
