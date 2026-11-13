import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldCheck, TrendingUp, Zap, ArrowRight } from 'lucide-react';
import useAuthStore from '@/store/useAuthStore';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';

export default function Auth() {
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({ email: '', password: '', full_name: '' });
  const [loading, setLoading] = useState(false);
  const { login, signup } = useAuthStore();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const res = isLogin
        ? await login(formData.email, formData.password)
        : await signup(formData.full_name, formData.email, formData.password);

      if (res.success) {
        if (isLogin) {
          toast.success('Welcome back to Arthsavora');
          navigate('/dashboard');
        } else {
          toast.success('Account created successfully. Please sign in.');
          setIsLogin(true);
        }
      } else {
        toast.error(res.error || 'Authentication failed');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen w-full flex-col md:flex-row bg-[#0b0f1a] text-white">
      {/* Left Column: Institutional Value Proposition */}
      <div className="relative hidden w-1/2 flex-col justify-between overflow-hidden bg-slate-900 p-12 md:flex border-r border-slate-800">
        <div className="relative z-10">
          <div className="mb-10 flex items-center gap-3">
            <div className="rounded-xl bg-indigo-600 p-2 text-white shadow-lg shadow-indigo-600/30">
              <ShieldCheck size={28} />
            </div>
            <h1 className="text-xl font-black tracking-tight uppercase">ARTHSAVORA</h1>
          </div>

          <h2 className="text-4xl font-extrabold leading-tight text-white mb-6">
            Institutional Financial Management <br />
            <span className="text-indigo-400">Engineered for India.</span>
          </h2>

          <div className="max-w-md space-y-6 text-sm text-slate-300">
            <div className="flex gap-4">
              <div className="rounded-lg bg-indigo-500/10 p-2 text-indigo-400 shrink-0">
                <Zap size={20} />
              </div>
              <div>
                <h4 className="font-bold text-white">Automated UPI Ingestion</h4>
                <p className="text-slate-400 text-xs mt-1">
                  Deterministic regex parsing and machine-learned merchant categorization.
                </p>
              </div>
            </div>

            <div className="flex gap-4">
              <div className="rounded-lg bg-indigo-500/10 p-2 text-indigo-400 shrink-0">
                <TrendingUp size={20} />
              </div>
              <div>
                <h4 className="font-bold text-white">Predictive Budget Intelligence</h4>
                <p className="text-slate-400 text-xs mt-1">
                  Time-series spending forecasting and anomaly detection.
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="relative z-10 text-xs text-slate-500">
          © {new Date().getFullYear()} ARTHSAVORA. Commercial-grade financial platform.
        </div>
      </div>

      {/* Right Column: Sign In / Sign Up Form */}
      <div className="flex flex-1 items-center justify-center p-6 md:p-12">
        <div className="w-full max-w-md space-y-8 rounded-2xl border border-slate-800 bg-slate-900/60 p-8 backdrop-blur-sm">
          <div>
            <h3 className="text-2xl font-bold tracking-tight text-white">
              {isLogin ? 'Sign In to Your Workspace' : 'Create Your Account'}
            </h3>
            <p className="mt-1.5 text-xs text-slate-400">
              {isLogin
                ? 'Enter your credentials to access your financial dashboard'
                : 'Get started with intelligent personal and business finance'}
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {!isLogin && (
              <Input
                label="Full Name"
                placeholder="Ashutosh Mishra"
                value={formData.full_name}
                onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                required
              />
            )}

            <Input
              label="Email Address"
              type="email"
              placeholder="name@example.com"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              required
            />

            <Input
              label="Password"
              type="password"
              placeholder="••••••••"
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              required
            />

            <Button
              type="submit"
              className="w-full mt-2 gap-2"
              size="md"
              isLoading={loading}
            >
              <span>{isLogin ? 'Sign In' : 'Create Free Account'}</span>
              <ArrowRight size={16} />
            </Button>
          </form>

          <div className="text-center">
            <button
              type="button"
              onClick={() => setIsLogin(!isLogin)}
              className="text-xs text-slate-400 hover:text-white transition-colors"
            >
              {isLogin ? "Don't have an account? " : 'Already have an account? '}
              <span className="font-bold text-indigo-400 hover:underline">
                {isLogin ? 'Sign Up' : 'Sign In'}
              </span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
