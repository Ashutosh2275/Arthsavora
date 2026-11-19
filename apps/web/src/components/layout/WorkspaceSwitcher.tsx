import React, { useState, useEffect, useRef } from 'react';
import {
  Briefcase,
  Users,
  User,
  Check,
  ChevronDown,
  Plus,
  Building,
  Shield,
} from 'lucide-react';
import useWorkspaceStore from '@/store/useWorkspaceStore';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';

export const WorkspaceSwitcher: React.FC = () => {
  const {
    workspaces,
    activeWorkspace,
    fetchWorkspaces,
    switchWorkspace,
    createWorkspace,
  } = useWorkspaceStore();

  const [isOpen, setIsOpen] = useState(false);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [newWorkspaceName, setNewWorkspaceName] = useState('');
  const [newWorkspaceType, setNewWorkspaceType] = useState<'personal' | 'family' | 'business'>('personal');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchWorkspaces();
  }, []);

  // Close dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const getWorkspaceIcon = (type: string) => {
    const lower = (type || '').toLowerCase();
    if (lower === 'family') return <Users size={15} className="text-emerald-400" />;
    if (lower === 'business') return <Briefcase size={15} className="text-amber-400" />;
    return <User size={15} className="text-indigo-400" />;
  };

  const getWorkspaceBadgeColor = (type: string) => {
    const lower = (type || '').toLowerCase();
    if (lower === 'family') return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
    if (lower === 'business') return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
    return 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30';
  };

  const handleSelect = async (workspaceId: string) => {
    try {
      await switchWorkspace(workspaceId);
      setIsOpen(false);
      toast.success('Switched workspace context');
    } catch {
      toast.error('Failed to switch workspace');
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newWorkspaceName.trim()) {
      toast.error('Please enter a workspace name');
      return;
    }
    setIsSubmitting(true);
    try {
      await createWorkspace({
        name: newWorkspaceName.trim(),
        type: newWorkspaceType,
        currency: 'INR',
        timezone: 'Asia/Kolkata',
        country: 'IN',
      });
      toast.success(`Created ${newWorkspaceType} workspace "${newWorkspaceName}"`);
      setIsCreateModalOpen(false);
      setNewWorkspaceName('');
      setIsOpen(false);
    } catch (err: any) {
      toast.error(err.message || 'Failed to create workspace');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Trigger Button */}
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        aria-expanded={isOpen}
        aria-haspopup="listbox"
        aria-label="Select workspace"
        className="flex items-center gap-2.5 px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 transition-all text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 max-w-[220px]"
      >
        <div className="p-1 rounded-lg bg-slate-800/80 shrink-0">
          {getWorkspaceIcon(activeWorkspace?.type || 'personal')}
        </div>
        <div className="overflow-hidden min-w-0 flex-1">
          <p className="text-xs font-semibold text-white truncate leading-tight">
            {activeWorkspace?.name || 'Personal Workspace'}
          </p>
          <span className="text-[10px] text-slate-400 uppercase tracking-wider block font-mono">
            {activeWorkspace?.type || 'personal'}
          </span>
        </div>
        <ChevronDown size={14} className={`text-slate-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div
          role="listbox"
          aria-label="Workspaces"
          className="absolute left-0 mt-2 w-72 rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl p-2 z-50 backdrop-blur-xl animate-in fade-in zoom-in-95 duration-100"
        >
          <div className="px-2.5 py-1.5 border-b border-slate-800 mb-1 flex items-center justify-between">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              Your Workspaces
            </span>
            <span className="text-[10px] text-slate-500 font-mono">
              {workspaces.length} Total
            </span>
          </div>

          <div className="max-h-60 overflow-y-auto space-y-1 py-1">
            {workspaces.map((ws) => {
              const isCurrent = String(ws.id) === String(activeWorkspace?.id);
              return (
                <button
                  key={ws.id}
                  role="option"
                  aria-selected={isCurrent}
                  onClick={() => handleSelect(String(ws.id))}
                  className={`w-full flex items-center justify-between px-2.5 py-2 rounded-xl text-left text-xs transition-colors ${
                    isCurrent
                      ? 'bg-indigo-600/15 text-white font-medium border border-indigo-500/30'
                      : 'text-slate-300 hover:bg-slate-800/80 hover:text-white'
                  }`}
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <div className="p-1 rounded-lg bg-slate-800 shrink-0">
                      {getWorkspaceIcon(ws.type)}
                    </div>
                    <div className="truncate">
                      <p className="font-semibold truncate">{ws.name}</p>
                      <span className={`inline-block text-[9px] px-1.5 py-0.2 rounded border font-mono mt-0.5 ${getWorkspaceBadgeColor(ws.type)}`}>
                        {ws.type}
                      </span>
                    </div>
                  </div>
                  {isCurrent && <Check size={14} className="text-indigo-400 shrink-0 ml-2" />}
                </button>
              );
            })}

            {workspaces.length === 0 && (
              <p className="text-xs text-slate-500 text-center py-3">No workspaces found</p>
            )}
          </div>

          <div className="border-t border-slate-800 pt-1 mt-1">
            <button
              onClick={() => {
                setIsOpen(false);
                setIsCreateModalOpen(true);
              }}
              className="w-full flex items-center gap-2 px-2.5 py-2 rounded-xl text-xs font-medium text-indigo-400 hover:bg-indigo-600/10 transition-colors"
            >
              <Plus size={14} />
              <span>Create New Workspace</span>
            </button>
          </div>
        </div>
      )}

      {/* Create Workspace Modal */}
      {isCreateModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div
            role="dialog"
            aria-labelledby="modal-title"
            aria-modal="true"
            className="w-full max-w-md rounded-2xl bg-slate-900 border border-slate-800 p-6 shadow-2xl space-y-5 animate-in fade-in zoom-in-95"
          >
            <div>
              <h3 id="modal-title" className="text-lg font-bold text-white flex items-center gap-2">
                <Building size={20} className="text-indigo-400" /> Create Workspace
              </h3>
              <p className="text-xs text-slate-400 mt-1">
                Establish an isolated financial workspace for personal, household, or commercial accounting.
              </p>
            </div>

            <form onSubmit={handleCreate} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-300 font-medium mb-1.5">Workspace Title</label>
                <Input
                  value={newWorkspaceName}
                  onChange={(e) => setNewWorkspaceName(e.target.value)}
                  placeholder="e.g. Apex Studio LLP, Sharma Household"
                  required
                  autoFocus
                />
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1.5">Tenancy Type</label>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { id: 'personal', label: 'Personal', icon: <User size={14} /> },
                    { id: 'family', label: 'Family', icon: <Users size={14} /> },
                    { id: 'business', label: 'Business', icon: <Briefcase size={14} /> },
                  ].map((t) => (
                    <button
                      key={t.id}
                      type="button"
                      onClick={() => setNewWorkspaceType(t.id as any)}
                      className={`flex flex-col items-center gap-1.5 p-3 rounded-xl border transition-all text-xs ${
                        newWorkspaceType === t.id
                          ? 'border-indigo-500 bg-indigo-500/10 text-white font-semibold'
                          : 'border-slate-800 bg-slate-950 text-slate-400 hover:border-slate-700'
                      }`}
                    >
                      {t.icon}
                      <span>{t.label}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-[11px] text-slate-400 space-y-1">
                <div className="flex items-center gap-1.5 text-slate-300 font-medium">
                  <Shield size={12} className="text-indigo-400" /> Architectural Boundary
                </div>
                <p>
                  Workspaces provide complete tenant isolation. Bank accounts, transactions, and tax records are strictly segregated.
                </p>
              </div>

              <div className="flex justify-end gap-2.5 pt-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setIsCreateModalOpen(false)}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  size="sm"
                  disabled={isSubmitting}
                  className="bg-indigo-600 hover:bg-indigo-500 text-white"
                >
                  {isSubmitting ? 'Creating...' : 'Create Workspace'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default WorkspaceSwitcher;
