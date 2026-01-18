import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldCheck, TrendingUp, Zap, ArrowRight } from 'lucide-react';
import useAuthStore from '../store/useAuthStore';

export default function Auth() {
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({ email: '', password: '', full_name: '' });
  const [error, setError] = useState('');
  const { login, signup } = useAuthStore();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    const res = isLogin 
      ? await login(formData.email, formData.password)
      : await signup(formData.full_name, formData.email, formData.password);
    
    if (res.success) {
      if (isLogin) navigate('/dashboard');
      else { setIsLogin(true); alert("Account created! Please login."); }
    } else {
      setError(res.error);
    }
  };

  return (
    <div className="min-h-screen w-screen flex flex-col md:flex-row bg-[#0b0f1a] text-white">
      {/* Left Side: Branding & Features */}
      <div className="hidden md:flex md:w-1/2 bg-gradient-to-br from-indigo-900 via-slate-900 to-black p-12 flex-col justify-between relative overflow-hidden">
        <div className="relative z-10">
          <div className="flex items-center gap-2 mb-8">
            <div className="bg-indigo-500 p-2 rounded-lg">
              <ShieldCheck size={28} />
            </div>
            <h1 className="text-2xl font-bold tracking-tight">ARTHSAVORA</h1>
          </div>
          
          <h2 className="text-5xl font-extrabold leading-tight mb-6">
            Smart Finance <br /> 
            <span className="text-indigo-400">Powered by AI.</span>
          </h2>
          
          <div className="space-y-6 max-w-sm">
            <div className="flex gap-4">
              <Zap className="text-indigo-400 shrink-0" />
              <p className="text-slate-300">Automated UPI SMS parsing and instant expense categorization.</p>
            </div>
            <div className="flex gap-4">
              <TrendingUp className="text-indigo-400 shrink-0" />
              <p className="text-slate-300">Predictive budgeting using ARIMA models to stay ahead of bills.</p>
            </div>
          </div>
        </div>
        
        <div className="relative z-10 text-slate-500 text-sm">
          © 2026 ARTHSAVORA. Production-Ready FinTech Solutions.
        </div>

        {/* Decorative Blobs */}
        <div className="absolute top-[-10%] right-[-10%] w-96 h-96 bg-indigo-600/20 blur-[120px] rounded-full"></div>
      </div>

      {/* Right Side: Auth Form */}
      <div className="flex-1 flex items-center justify-center p-6 md:p-12 bg-[#0b0f1a]">
        <div className="w-full max-w-md space-y-8 bg-slate-900/50 p-8 rounded-3xl border border-slate-800 backdrop-blur-sm">
          <div className="text-center">
            <h3 className="text-3xl font-bold">{isLogin ? "Welcome Back" : "Get Started"}</h3>
            <p className="text-slate-400 mt-2">Enter your details to access your dashboard</p>
          </div>

          {error && (
            <div className="bg-red-500/10 border border-red-500/50 text-red-400 p-3 rounded-xl text-sm text-center">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            {!isLogin && (
              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Full Name</label>
                <input
                  type="text"
                  className="w-full bg-slate-800/50 border border-slate-700 p-3 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none transition-all placeholder:text-slate-600"
                  placeholder="John Doe"
                  onChange={(e) => setFormData({...formData, full_name: e.target.value})}
                  required
                />
              </div>
            )}
            
            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Email Address</label>
              <input
                type="email"
                className="w-full bg-slate-800/50 border border-slate-700 p-3 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none transition-all placeholder:text-slate-600"
                placeholder="name@company.com"
                onChange={(e) => setFormData({...formData, email: e.target.value})}
                required
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Password</label>
              <input
                type="password"
                className="w-full bg-slate-800/50 border border-slate-700 p-3 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none transition-all placeholder:text-slate-600"
                placeholder="••••••••"
                onChange={(e) => setFormData({...formData, password: e.target.value})}
                required
              />
            </div>

            <button className="w-flex group w-full bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-4 rounded-xl transition-all flex items-center justify-center gap-2 shadow-lg shadow-indigo-600/20">
              {isLogin ? "Sign In" : "Create Free Account"}
              <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" />
            </button>
          </form>

          <div className="text-center">
            <button 
              onClick={() => setIsLogin(!isLogin)}
              className="text-slate-400 text-sm hover:text-white transition-colors"
            >
              {isLogin ? "Don't have an account? " : "Already have an account? "}
              <span className="text-indigo-400 font-bold">{isLogin ? "Sign Up" : "Log In"}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}