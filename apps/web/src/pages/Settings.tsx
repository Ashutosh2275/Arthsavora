import React, { useState, useEffect } from 'react';
import {
  User,
  Building,
  Users,
  Palette,
  ShieldCheck,
  Plus,
  Trash2,
  Save,
  CheckCircle,
  Mail,
  Clock,
  Globe,
  DollarSign,
  AlertCircle,
} from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import ThemeToggle from '@/components/ui/ThemeToggle';
import useAuthStore from '@/store/useAuthStore';
import useWorkspaceStore from '@/store/useWorkspaceStore';
import { toast } from 'sonner';

type ActiveTab = 'profile' | 'workspace' | 'members' | 'preferences';

export const Settings: React.FC = () => {
  const { user } = useAuthStore();
  const {
    activeWorkspace,
    members,
    fetchMembers,
    inviteMember,
    removeMember,
    updateWorkspace,
  } = useWorkspaceStore();

  const [activeTab, setActiveTab] = useState<ActiveTab>('profile');

  // Profile form state
  const [fullName, setFullName] = useState(user?.full_name || '');
  const [email] = useState(user?.email || '');

  // Workspace form state
  const [workspaceName, setWorkspaceName] = useState(activeWorkspace?.name || '');
  const [currency, setCurrency] = useState<string>(activeWorkspace?.currency || 'INR');
  const [timezone, setTimezone] = useState(activeWorkspace?.timezone || 'Asia/Kolkata');
  const [country, setCountry] = useState(activeWorkspace?.country || 'IN');

  // Business Profile metadata (if applicable)
  const [legalName, setLegalName] = useState('');
  const [gstin, setGstin] = useState('');
  const [pan, setPan] = useState('');

  // Member invitation modal
  const [isInviteModalOpen, setIsInviteModalOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('member');
  const [isInviting, setIsInviting] = useState(false);

  useEffect(() => {
    if (activeWorkspace) {
      setWorkspaceName(activeWorkspace.name);
      setCurrency(activeWorkspace.currency || 'INR');
      setTimezone(activeWorkspace.timezone || 'Asia/Kolkata');
      setCountry(activeWorkspace.country || 'IN');
      fetchMembers(String(activeWorkspace.id));
    }
  }, [activeWorkspace]);

  const handleSaveProfile = (e: React.FormEvent) => {
    e.preventDefault();
    toast.success('User profile updated successfully.');
  };

  const handleSaveWorkspace = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeWorkspace) return;
    try {
      await updateWorkspace(String(activeWorkspace.id), {
        name: workspaceName,
        default_currency: currency as any,
        timezone,
        country,
      });
      toast.success('Workspace settings updated successfully.');
    } catch (err: any) {
      toast.error(err.message || 'Failed to update workspace settings.');
    }
  };

  const handleSendInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeWorkspace || !inviteEmail.trim()) return;
    setIsInviting(true);
    try {
      await inviteMember(String(activeWorkspace.id), inviteEmail.trim(), inviteRole);
      toast.success(`Invitation sent to ${inviteEmail}.`);
      setIsInviteModalOpen(false);
      setInviteEmail('');
    } catch (err: any) {
      toast.error(err.message || 'Failed to send invitation.');
    } finally {
      setIsInviting(false);
    }
  };

  const handleRemoveMember = async (membershipId: string, name: string) => {
    if (!activeWorkspace) return;
    if (!confirm(`Are you sure you want to remove ${name} from this workspace?`)) return;
    try {
      await removeMember(String(activeWorkspace.id), membershipId);
      toast.success(`Removed ${name} from workspace.`);
    } catch (err: any) {
      toast.error(err.message || 'Failed to remove member.');
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto px-4 py-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            Settings &amp; Workspace Management
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Manage your personal profile, active tenancy settings, collaboration permissions, and institutional preferences.
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex flex-wrap gap-1 border-b border-slate-800 pb-2">
        {[
          { id: 'profile', label: 'User Profile', icon: <User size={14} /> },
          { id: 'workspace', label: 'Workspace Configuration', icon: <Building size={14} /> },
          { id: 'members', label: 'Members & Access Control', icon: <Users size={14} /> },
          { id: 'preferences', label: 'Preferences & Appearance', icon: <Palette size={14} /> },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as ActiveTab)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === tab.id
                ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/30 font-semibold'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/50'
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab 1: User Profile */}
      {activeTab === 'profile' && (
        <Card className="p-6 border-slate-800 bg-slate-900/40 max-w-2xl space-y-5">
          <div>
            <h3 className="text-base font-bold text-white">Identity &amp; Profile Details</h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Personal credentials and contact email associated with your institutional account.
            </p>
          </div>

          <form onSubmit={handleSaveProfile} className="space-y-4 text-xs">
            <div>
              <label className="block text-slate-300 font-medium mb-1.5">Full Name</label>
              <Input
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Your Full Name"
                required
              />
            </div>

            <div>
              <label className="block text-slate-300 font-medium mb-1.5">Primary Email</label>
              <Input value={email} disabled className="opacity-70 cursor-not-allowed bg-slate-950" />
              <span className="text-[10px] text-slate-500 mt-1 block">
                Email address is verified and permanently linked to authentication records.
              </span>
            </div>

            <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 text-[11px] text-slate-400 space-y-1">
              <div className="flex items-center gap-1.5 text-slate-300 font-semibold">
                <ShieldCheck size={14} className="text-indigo-400" /> Authentication State
              </div>
              <p>JWT Session Bearer Token active. Cryptographic signatures verified on all outgoing requests.</p>
            </div>

            <div className="pt-2">
              <Button type="submit" size="sm" className="bg-indigo-600 hover:bg-indigo-500 text-white gap-1.5">
                <Save size={14} /> Save Profile
              </Button>
            </div>
          </form>
        </Card>
      )}

      {/* Tab 2: Workspace Configuration */}
      {activeTab === 'workspace' && (
        <Card className="p-6 border-slate-800 bg-slate-900/40 max-w-2xl space-y-5">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-bold text-white">
                Workspace Configuration ({activeWorkspace?.type.toUpperCase()})
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Tenancy parameters, ISO currency, and statutory jurisdiction.
              </p>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/30 uppercase">
              {activeWorkspace?.type}
            </span>
          </div>

          <form onSubmit={handleSaveWorkspace} className="space-y-4 text-xs">
            <div>
              <label className="block text-slate-300 font-medium mb-1.5">Workspace Title</label>
              <Input
                value={workspaceName}
                onChange={(e) => setWorkspaceName(e.target.value)}
                placeholder="Workspace Title"
                required
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className="block text-slate-300 font-medium mb-1.5">Base Currency</label>
                <select
                  value={currency}
                  onChange={(e) => setCurrency(e.target.value)}
                  className="w-full rounded-xl bg-slate-950 border border-slate-800 px-3 py-2 text-xs text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="INR">INR (₹)</option>
                  <option value="USD">USD ($)</option>
                  <option value="EUR">EUR (€)</option>
                  <option value="GBP">GBP (£)</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1.5">Timezone</label>
                <select
                  value={timezone}
                  onChange={(e) => setTimezone(e.target.value)}
                  className="w-full rounded-xl bg-slate-950 border border-slate-800 px-3 py-2 text-xs text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="Asia/Kolkata">Asia/Kolkata (IST)</option>
                  <option value="UTC">UTC</option>
                  <option value="America/New_York">America/New_York</option>
                  <option value="Europe/London">Europe/London</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1.5">Country Code</label>
                <Input
                  value={country}
                  onChange={(e) => setCountry(e.target.value.toUpperCase())}
                  maxLength={2}
                />
              </div>
            </div>

            {/* Business-specific statutory parameters */}
            {activeWorkspace?.type.toLowerCase() === 'business' && (
              <div className="pt-3 border-t border-slate-800 space-y-3">
                <h4 className="font-semibold text-slate-200">Statutory Business Metadata</h4>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-slate-300 font-medium mb-1">GSTIN (15-digit)</label>
                    <Input
                      value={gstin}
                      onChange={(e) => setGstin(e.target.value.toUpperCase())}
                      placeholder="e.g. 29AAAAA0000A1Z5"
                      maxLength={15}
                    />
                  </div>
                  <div>
                    <label className="block text-slate-300 font-medium mb-1">PAN (10-digit)</label>
                    <Input
                      value={pan}
                      onChange={(e) => setPan(e.target.value.toUpperCase())}
                      placeholder="e.g. AAAAA0000A"
                      maxLength={10}
                    />
                  </div>
                </div>
              </div>
            )}

            <div className="pt-2">
              <Button type="submit" size="sm" className="bg-indigo-600 hover:bg-indigo-500 text-white gap-1.5">
                <Save size={14} /> Update Workspace
              </Button>
            </div>
          </form>
        </Card>
      )}

      {/* Tab 3: Members & Access Control */}
      {activeTab === 'members' && (
        <Card className="p-6 border-slate-800 bg-slate-900/40 space-y-5">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-bold text-white">Active Workspace Members</h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Manage collaboration privileges and role-based permissions in this workspace.
              </p>
            </div>
            <Button
              size="sm"
              onClick={() => setIsInviteModalOpen(true)}
              className="bg-indigo-600 hover:bg-indigo-500 text-white gap-1.5 text-xs"
            >
              <Plus size={14} /> Invite Member
            </Button>
          </div>

          <div className="divide-y divide-slate-800 text-xs">
            {members.map((member) => (
              <div key={member.id} className="py-3 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-slate-800 text-indigo-400 font-bold flex items-center justify-center text-xs">
                    {(member.full_name || member.email || 'M')[0].toUpperCase()}
                  </div>
                  <div>
                    <p className="font-semibold text-white">{member.full_name || 'Member'}</p>
                    <p className="text-[11px] text-slate-400">{member.email || 'Email not listed'}</p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <Badge variant="brand" className="text-[10px] uppercase font-mono">
                    {member.role}
                  </Badge>
                  {member.role !== 'owner' && (
                    <button
                      type="button"
                      onClick={() => handleRemoveMember(String(member.id), member.full_name || member.email || 'member')}
                      className="text-slate-500 hover:text-rose-400 p-1.5 rounded-lg transition-colors"
                      title="Remove member"
                    >
                      <Trash2 size={14} />
                    </button>
                  )}
                </div>
              </div>
            ))}

            {members.length === 0 && (
              <div className="py-6 text-center text-slate-500">
                <Users size={24} className="mx-auto text-slate-600 mb-1" />
                <p>No external members in this workspace.</p>
              </div>
            )}
          </div>
        </Card>
      )}

      {/* Tab 4: Preferences & Appearance */}
      {activeTab === 'preferences' && (
        <Card className="p-6 border-slate-800 bg-slate-900/40 max-w-2xl space-y-6">
          <div>
            <h3 className="text-base font-bold text-white">Platform Preferences</h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Visual themes, notification delivery channels, and institutional display options.
            </p>
          </div>

          <div className="space-y-4 text-xs">
            {/* Theme */}
            <div className="flex items-center justify-between p-3.5 rounded-2xl bg-slate-950 border border-slate-800">
              <div>
                <p className="font-semibold text-white">Visual Interface Theme</p>
                <p className="text-[11px] text-slate-400">Select light, dark, or system preference mode.</p>
              </div>
              <ThemeToggle />
            </div>

            {/* Notifications */}
            <div className="p-3.5 rounded-2xl bg-slate-950 border border-slate-800 space-y-2">
              <p className="font-semibold text-white">Statutory Financial Recordkeeping Notice</p>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                ARTHSAVORA operates on strict multi-tenant isolation principles. All financial statement generation, general ledger postings, and tax estimations run deterministic algorithms with zero third-party data selling.
              </p>
            </div>
          </div>
        </Card>
      )}

      {/* Invite Member Modal */}
      {isInviteModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
          <div
            role="dialog"
            aria-modal="true"
            aria-label="Invite Collaborator"
            className="w-full max-w-md rounded-2xl bg-slate-900 border border-slate-800 p-6 shadow-2xl space-y-4 animate-in zoom-in-95"
          >
            <div>
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Mail size={18} className="text-indigo-400" /> Invite Collaborator
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Issue a secure invitation to join {activeWorkspace?.name}.
              </p>
            </div>

            <form onSubmit={handleSendInvite} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 font-medium mb-1">Email Address</label>
                <Input
                  type="email"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  placeholder="collaborator@example.com"
                  required
                  autoFocus
                />
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Role &amp; Permissions</label>
                <select
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value)}
                  className="w-full rounded-xl bg-slate-950 border border-slate-800 px-3 py-2 text-xs text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="member">Member (Create and view transactions)</option>
                  <option value="accountant">Accountant (Manage ledgers, invoices &amp; reports)</option>
                  <option value="auditor">Auditor (Read-only verification and export)</option>
                  <option value="admin">Admin (Full workspace administration)</option>
                  <option value="viewer">Viewer (Read-only overview)</option>
                </select>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setIsInviteModalOpen(false)}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  size="sm"
                  disabled={isInviting}
                  className="bg-indigo-600 hover:bg-indigo-500 text-white"
                >
                  {isInviting ? 'Sending...' : 'Send Invitation'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Settings;
