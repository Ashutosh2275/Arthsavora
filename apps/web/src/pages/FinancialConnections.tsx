import React, { useEffect, useState } from 'react';
import {
  Link2,
  Building2,
  ShieldCheck,
  RefreshCw,
  CheckCircle,
  AlertTriangle,
  Clock,
  XCircle,
  Plus,
  ExternalLink,
  Lock,
  Layers,
  History,
  Scale,
  Unlink,
  Check,
  ChevronRight,
  ShieldAlert,
} from 'lucide-react';
import { useFinancialConnectionStore } from '../store/useFinancialConnectionStore';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Modal } from '../components/ui/modal';
import { Input } from '../components/ui/input';
import { Card } from '../components/ui/card';
import { EmptyState } from '@/components/feedback/EmptyState';
import type {
  DiscoveredAccountDTO,
  FinancialConnectionDTO,
  FinancialProviderDTO,
} from '@arthsavora/contracts';

export const FinancialConnections: React.FC = () => {
  const {
    providers,
    connections,
    selectedConnection,
    syncHistory,
    reconciliations,
    isLoading,
    error,
    fetchProviders,
    fetchConnections,
    setSelectedConnection,
    initiateConnection,
    authorizeConnection,
    triggerSync,
    revokeConsent,
    disconnectConnection,
    linkAccount,
    unlinkAccount,
    fetchSyncHistory,
    fetchReconciliations,
    resolveReconciliation,
  } = useFinancialConnectionStore();

  const [activeTab, setActiveTab] = useState<'accounts' | 'providers' | 'details' | 'history' | 'reconciliation'>('accounts');

  // Modals state
  const [isConnectModalOpen, setIsConnectModalOpen] = useState(false);
  const [selectedProviderCode, setSelectedProviderCode] = useState('MOCK_SANDBOX_AA');
  const [selectedInstitutionId, setSelectedInstitutionId] = useState('HDFC');
  const [connectStep, setConnectStep] = useState<1 | 2>(1);
  const [consentPurpose, setConsentPurpose] = useState('Personal Financial Management & Automated Reconciliation');
  const [validDays, setValidDays] = useState(180);

  const [isLinkModalOpen, setIsLinkModalOpen] = useState(false);
  const [accountToLink, setAccountToLink] = useState<DiscoveredAccountDTO | null>(null);
  const [newAccountName, setNewAccountName] = useState('');

  const [isResolveModalOpen, setIsResolveModalOpen] = useState(false);
  const [resolveRecId, setResolveRecId] = useState<string | null>(null);
  const [resolveExplanation, setResolveExplanation] = useState('');

  const [isDisconnectModalOpen, setIsDisconnectModalOpen] = useState(false);

  useEffect(() => {
    fetchProviders();
    fetchConnections();
  }, [fetchProviders, fetchConnections]);

  useEffect(() => {
    if (selectedConnection) {
      fetchSyncHistory(selectedConnection.id);
      fetchReconciliations(selectedConnection.id);
    }
  }, [selectedConnection, fetchSyncHistory, fetchReconciliations]);

  const formatPaise = (paise?: number | null) => {
    if (paise === null || paise === undefined) return 'N/A';
    return `₹${(paise / 100).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const getHealthBadge = (health: string) => {
    switch (health) {
      case 'healthy':
        return <Badge variant="income" className="gap-1"><CheckCircle className="w-3 h-3" /> Healthy</Badge>;
      case 'needs_authorization':
        return <Badge variant="warning" className="gap-1"><Clock className="w-3 h-3" /> Needs Auth</Badge>;
      case 'sync_delayed':
        return <Badge variant="warning" className="gap-1"><AlertTriangle className="w-3 h-3" /> Delayed</Badge>;
      case 'connection_expired':
      case 'provider_unavailable':
        return <Badge variant="expense" className="gap-1"><XCircle className="w-3 h-3" /> Expired / Error</Badge>;
      case 'disconnected':
        return <Badge variant="neutral" className="gap-1"><Unlink className="w-3 h-3" /> Disconnected</Badge>;
      default:
        return <Badge variant="neutral">{health}</Badge>;
    }
  };

  const handleInitiateConnect = async () => {
    try {
      const conn = await initiateConnection({
        provider_code: selectedProviderCode,
        institution_id: selectedInstitutionId,
        purpose: consentPurpose,
        valid_days: validDays,
      });
      // In sandbox mode, confirm authorization automatically or via handoff
      await authorizeConnection(conn.id);
      setIsConnectModalOpen(false);
      setConnectStep(1);
    } catch (err) {
      // Error handled in store
    }
  };

  const handleOpenLinkModal = (acc: DiscoveredAccountDTO) => {
    setAccountToLink(acc);
    setNewAccountName(`${acc.institution_name} ${acc.account_type.toUpperCase()} (${acc.masked_account_number})`);
    setIsLinkModalOpen(true);
  };

  const handleConfirmLink = async () => {
    if (!selectedConnection || !accountToLink) return;
    try {
      await linkAccount(selectedConnection.id, accountToLink.id, {
        create_new: true,
        account_name: newAccountName,
      });
      setIsLinkModalOpen(false);
      setAccountToLink(null);
    } catch (err) {
      // Handled
    }
  };

  const handleConfirmResolve = async () => {
    if (!selectedConnection || !resolveRecId) return;
    try {
      await resolveReconciliation(selectedConnection.id, resolveRecId, resolveExplanation);
      setIsResolveModalOpen(false);
      setResolveRecId(null);
      setResolveExplanation('');
    } catch (err) {
      // Handled
    }
  };

  const activeConnection = selectedConnection || connections[0];
  const allLinkedAccounts = connections.flatMap((c) =>
    (c.account_references || []).map((ref) => ({ ...ref, connection: c }))
  );

  return (
    <div className="space-y-6 max-w-7xl mx-auto px-4 sm:px-6 py-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-gray-900 dark:text-white flex items-center gap-2">
            <Link2 className="w-7 h-7 text-indigo-600 dark:text-indigo-400" />
            Financial Connections & Account Aggregation
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Consent-driven Open Banking connectivity and RBI ReBIT Account Aggregator integration.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            onClick={() => {
              fetchProviders();
              fetchConnections();
            }}
            isLoading={isLoading}
            className="gap-2"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh Feeds
          </Button>
          <Button
            onClick={() => {
              setConnectStep(1);
              setIsConnectModalOpen(true);
            }}
            className="gap-2"
          >
            <Plus className="w-4 h-4" />
            Connect Institution
          </Button>
        </div>
      </div>

      {/* KPI Overview Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-gray-500">Connected Institutions</span>
            <Building2 className="w-4 h-4 text-indigo-500" />
          </div>
          <p className="text-2xl font-bold text-gray-900 dark:text-white mt-2">
            {connections.filter((c) => c.status === 'active').length}
          </p>
          <span className="text-xs text-gray-500 mt-1">Authorized Provider Feeds</span>
        </Card>

        <Card className="p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-gray-500">Synchronized Accounts</span>
            <Layers className="w-4 h-4 text-emerald-500" />
          </div>
          <p className="text-2xl font-bold text-gray-900 dark:text-white mt-2">
            {allLinkedAccounts.filter((a) => a.status === 'linked').length}
          </p>
          <span className="text-xs text-gray-500 mt-1">Discovered & Linked Accounts</span>
        </Card>

        <Card className="p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-gray-500">Consent Integrity</span>
            <ShieldCheck className="w-4 h-4 text-blue-500" />
          </div>
          <p className="text-2xl font-bold text-gray-900 dark:text-white mt-2">
            {connections.filter((c) => c.health_status === 'healthy').length} / {connections.length || 0}
          </p>
          <span className="text-xs text-emerald-600 dark:text-emerald-400 mt-1">ReBIT AA Compliant</span>
        </Card>

        <Card className="p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-gray-500">Reconciliation Health</span>
            <Scale className="w-4 h-4 text-amber-500" />
          </div>
          <p className="text-2xl font-bold text-gray-900 dark:text-white mt-2">
            {Object.values(reconciliations).flat().filter((r) => r.status === 'matched').length} Matched
          </p>
          <span className="text-xs text-amber-600 dark:text-amber-400 mt-1">Book vs Bank Variance</span>
        </Card>
      </div>

      {/* Navigation Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-800">
        <nav className="flex space-x-8" aria-label="Tabs">
          {[
            { id: 'accounts', name: 'Connected Accounts', count: allLinkedAccounts.length },
            { id: 'providers', name: 'Providers & Banks', count: providers.length },
            { id: 'details', name: 'Connection Details', count: connections.length },
            { id: 'history', name: 'Sync History' },
            { id: 'reconciliation', name: 'Balance Reconciliation' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`py-3 px-1 border-b-2 font-medium text-sm transition-colors flex items-center gap-2 ${
                activeTab === tab.id
                  ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400 dark:border-indigo-400'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
              }`}
            >
              {tab.name}
              {tab.count !== undefined && (
                <span className="ml-1 px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400">
                  {tab.count}
                </span>
              )}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab 1: Connected Accounts */}
      {activeTab === 'accounts' && (
        <div className="space-y-4">
          {allLinkedAccounts.length === 0 ? (
            <EmptyState
              icon={<Link2 className="w-12 h-12 text-gray-400" />}
              title="No Connected Financial Accounts"
              description="Connect your Indian bank accounts via our Account Aggregator simulator or authorized gateway to automatically sync transactions and balances."
              action={
                <Button onClick={() => setIsConnectModalOpen(true)} className="gap-2">
                  <Plus className="w-4 h-4" />
                  Connect First Account
                </Button>
              }
            />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {allLinkedAccounts.map((acc) => (
                <Card key={acc.id} className="p-5 flex flex-col justify-between border-l-4 border-l-indigo-600">
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-gray-500 uppercase">{acc.institution_name}</span>
                      {getHealthBadge(acc.connection.health_status)}
                    </div>
                    <div className="flex items-center justify-between">
                      <h3 className="text-lg font-bold text-gray-900 dark:text-white">
                        {acc.masked_account_number}
                      </h3>
                      <Badge variant="neutral" className="uppercase text-xs font-mono">
                        {acc.account_type}
                      </Badge>
                    </div>
                    <div className="pt-2">
                      <span className="text-xs text-gray-500">Reported Bank Balance</span>
                      <p className="text-xl font-bold text-emerald-600 dark:text-emerald-400">
                        {formatPaise(acc.current_balance_paise)}
                      </p>
                    </div>
                    {acc.account_holder_name && (
                      <p className="text-xs text-gray-500">Holder: {acc.account_holder_name}</p>
                    )}
                  </div>

                  <div className="pt-4 border-t border-gray-100 dark:border-gray-800 mt-4 flex items-center justify-between gap-2">
                    {acc.status === 'linked' ? (
                      <>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => triggerSync(acc.connection_id)}
                          isLoading={isLoading}
                          className="gap-1 text-xs"
                        >
                          <RefreshCw className="w-3.5 h-3.5" /> Sync Now
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => unlinkAccount(acc.connection_id, acc.id)}
                          className="text-xs text-rose-600 hover:text-rose-700 dark:text-rose-400"
                        >
                          <Unlink className="w-3.5 h-3.5" /> Unlink
                        </Button>
                      </>
                    ) : (
                      <Button
                        size="sm"
                        onClick={() => handleOpenLinkModal(acc)}
                        className="w-full text-xs gap-1"
                      >
                        <Link2 className="w-3.5 h-3.5" /> Link to Arthsavora
                      </Button>
                    )}
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Providers & Banks */}
      {activeTab === 'providers' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {providers.map((p) => (
              <Card key={p.id} className="p-5 space-y-4">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="text-base font-bold text-gray-900 dark:text-white flex items-center gap-2">
                      <Building2 className="w-4 h-4 text-indigo-500" />
                      {p.name}
                    </h3>
                    <p className="text-xs text-gray-500 mt-1 font-mono uppercase">{p.provider_code} • {p.country}</p>
                  </div>
                  <Badge variant={p.status === 'available' ? 'income' : 'neutral'} className="text-xs">
                    {p.status.toUpperCase()}
                  </Badge>
                </div>

                <div className="space-y-1 text-xs text-gray-600 dark:text-gray-300">
                  <p><strong>Category:</strong> {p.category}</p>
                  <p><strong>Auth Standard:</strong> {p.auth_method} (ReBIT)</p>
                  <p><strong>Supported Institutions:</strong> {p.supported_institutions.map((i) => i.name).join(', ')}</p>
                </div>

                <div className="pt-2 flex items-center justify-between border-t border-gray-100 dark:border-gray-800">
                  <span className="text-xs text-gray-500">
                    {p.is_sandbox ? 'Sandbox Integration Active' : 'Production Regulated'}
                  </span>
                  <Button
                    size="sm"
                    onClick={() => {
                      setSelectedProviderCode(p.provider_code);
                      setSelectedInstitutionId(p.supported_institutions[0]?.id || 'HDFC');
                      setIsConnectModalOpen(true);
                    }}
                    className="text-xs gap-1"
                  >
                    Connect via this Provider <ChevronRight className="w-3 h-3" />
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Tab 3: Connection Details */}
      {activeTab === 'details' && (
        <div className="space-y-4">
          {connections.length === 0 ? (
            <EmptyState
              icon={<ShieldAlert className="w-12 h-12 text-gray-400" />}
              title="No Connections Established"
              description="You have not connected any banking institutions to this workspace."
            />
          ) : (
            connections.map((c) => (
              <Card key={c.id} className="p-5 space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-gray-100 dark:border-gray-800 pb-3">
                  <div>
                    <h3 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
                      <Building2 className="w-5 h-5 text-indigo-600" />
                      {c.institution_name}
                    </h3>
                    <p className="text-xs text-gray-500 font-mono">Provider: {c.provider_name || c.provider_code}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    {getHealthBadge(c.health_status)}
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => triggerSync(c.id)}
                      isLoading={isLoading}
                      className="gap-1 text-xs"
                    >
                      <RefreshCw className="w-3.5 h-3.5" /> Sync
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        setSelectedConnection(c);
                        setIsDisconnectModalOpen(true);
                      }}
                      className="text-xs text-rose-600 dark:text-rose-400"
                    >
                      Disconnect
                    </Button>
                  </div>
                </div>

                {/* Consent metadata */}
                {c.active_consent && (
                  <div className="bg-gray-50 dark:bg-gray-800/50 p-4 rounded-lg space-y-2 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-gray-700 dark:text-gray-300 flex items-center gap-1">
                        <Lock className="w-3.5 h-3.5 text-blue-500" /> ReBIT Consent Artefact
                      </span>
                      <Badge variant="neutral" className="font-mono text-xs">
                        {c.active_consent.status.toUpperCase()}
                      </Badge>
                    </div>
                    <p className="text-gray-600 dark:text-gray-400">
                      <strong>Purpose:</strong> {c.active_consent.purpose}
                    </p>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-gray-500 pt-1">
                      <div>
                        <strong>Valid From:</strong> {new Date(c.active_consent.valid_from).toLocaleDateString('en-IN')}
                      </div>
                      <div>
                        <strong>Valid To:</strong> {new Date(c.active_consent.valid_to).toLocaleDateString('en-IN')}
                      </div>
                      <div>
                        <strong>Frequency:</strong> {c.active_consent.fetch_frequency}
                      </div>
                      <div>
                        <strong>Handle:</strong> {c.active_consent.provider_consent_handle?.substring(0, 16)}...
                      </div>
                    </div>
                    {c.active_consent.status === 'active' && (
                      <div className="pt-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => revokeConsent(c.id)}
                          className="text-xs text-amber-600 dark:text-amber-400"
                        >
                          Revoke User Consent
                        </Button>
                      </div>
                    )}
                  </div>
                )}

                {/* Discovered accounts table */}
                <div className="space-y-2">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Accounts Discovered under Consent ({c.account_references?.length || 0})
                  </h4>
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs text-left">
                      <thead className="bg-gray-50 dark:bg-gray-800/50 text-gray-500 font-semibold uppercase">
                        <tr>
                          <th className="py-2 px-3">Account Number</th>
                          <th className="py-2 px-3">Type</th>
                          <th className="py-2 px-3">Reported Balance</th>
                          <th className="py-2 px-3">Status</th>
                          <th className="py-2 px-3 text-right">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                        {(c.account_references || []).map((ref) => (
                          <tr key={ref.id}>
                            <td className="py-2 px-3 font-mono font-medium">{ref.masked_account_number}</td>
                            <td className="py-2 px-3 uppercase">{ref.account_type}</td>
                            <td className="py-2 px-3 font-semibold text-emerald-600">
                              {formatPaise(ref.current_balance_paise)}
                            </td>
                            <td className="py-2 px-3">
                              <Badge variant={ref.status === 'linked' ? 'income' : 'neutral'} className="text-xs">
                                {ref.status}
                              </Badge>
                            </td>
                            <td className="py-2 px-3 text-right">
                              {ref.status === 'linked' ? (
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => unlinkAccount(c.id, ref.id)}
                                  className="text-xs text-rose-600"
                                >
                                  Unlink
                                </Button>
                              ) : (
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => {
                                    setSelectedConnection(c);
                                    handleOpenLinkModal(ref);
                                  }}
                                  className="text-xs"
                                >
                                  Link
                                </Button>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </Card>
            ))
          )}
        </div>
      )}

      {/* Tab 4: Sync History */}
      {activeTab === 'history' && (
        <div className="space-y-4">
          <Card className="p-4">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-500 mb-4 flex items-center gap-2">
              <History className="w-4 h-4" /> Synchronization Batches
            </h3>
            {activeConnection && syncHistory[activeConnection.id]?.length ? (
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead className="bg-gray-50 dark:bg-gray-800/50 text-gray-500 uppercase">
                    <tr>
                      <th className="py-2 px-3">Date & Time</th>
                      <th className="py-2 px-3">Type</th>
                      <th className="py-2 px-3">Status</th>
                      <th className="py-2 px-3">Retrieved</th>
                      <th className="py-2 px-3">Imported</th>
                      <th className="py-2 px-3">Duplicates</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                    {syncHistory[activeConnection.id].map((job) => (
                      <tr key={job.id}>
                        <td className="py-2 px-3 text-gray-500">
                          {job.started_at ? new Date(job.started_at).toLocaleString('en-IN') : 'N/A'}
                        </td>
                        <td className="py-2 px-3 font-mono">{job.job_type}</td>
                        <td className="py-2 px-3">
                          <Badge variant={job.status === 'completed' ? 'income' : 'expense'}>
                            {job.status.toUpperCase()}
                          </Badge>
                        </td>
                        <td className="py-2 px-3">{job.records_retrieved}</td>
                        <td className="py-2 px-3 font-bold text-emerald-600">{job.records_imported}</td>
                        <td className="py-2 px-3 text-gray-400">{job.duplicates_detected}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-xs text-gray-500 py-4 text-center">No synchronization logs available for this connection.</p>
            )}
          </Card>
        </div>
      )}

      {/* Tab 5: Balance Reconciliation */}
      {activeTab === 'reconciliation' && (
        <div className="space-y-4">
          <Card className="p-4">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-500 mb-4 flex items-center gap-2">
              <Scale className="w-4 h-4" /> Provider Reported vs Internal Book Balances
            </h3>
            {activeConnection && reconciliations[activeConnection.id]?.length ? (
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead className="bg-gray-50 dark:bg-gray-800/50 text-gray-500 uppercase">
                    <tr>
                      <th className="py-2 px-3">Audit Date</th>
                      <th className="py-2 px-3">Bank Reported</th>
                      <th className="py-2 px-3">Book Balance</th>
                      <th className="py-2 px-3">Variance</th>
                      <th className="py-2 px-3">Status</th>
                      <th className="py-2 px-3">Explanation</th>
                      <th className="py-2 px-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                    {reconciliations[activeConnection.id].map((rec) => (
                      <tr key={rec.id}>
                        <td className="py-2 px-3 text-gray-500">{rec.reconciliation_date}</td>
                        <td className="py-2 px-3 font-semibold text-emerald-600">
                          {formatPaise(rec.provider_reported_balance_paise)}
                        </td>
                        <td className="py-2 px-3 font-semibold text-blue-600">
                          {formatPaise(rec.calculated_book_balance_paise)}
                        </td>
                        <td className="py-2 px-3 font-mono font-bold">
                          {rec.difference_paise === 0 ? '₹0.00' : formatPaise(Math.abs(rec.difference_paise))}
                        </td>
                        <td className="py-2 px-3">
                          <Badge
                            variant={
                              rec.status === 'matched'
                                ? 'income'
                                : rec.status === 'resolved'
                                ? 'neutral'
                                : 'warning'
                            }
                          >
                            {rec.status.toUpperCase()}
                          </Badge>
                        </td>
                        <td className="py-2 px-3 text-gray-600 dark:text-gray-300 max-w-xs truncate">
                          {rec.explanation || 'Perfect reconciliation.'}
                        </td>
                        <td className="py-2 px-3 text-right">
                          {rec.status !== 'matched' && rec.status !== 'resolved' && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => {
                                setResolveRecId(rec.id);
                                setIsResolveModalOpen(true);
                              }}
                              className="text-xs"
                            >
                              Resolve
                            </Button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-xs text-gray-500 py-4 text-center">No reconciliation records found.</p>
            )}
          </Card>
        </div>
      )}

      {/* Modal 1: Connect Institution */}
      <Modal
        isOpen={isConnectModalOpen}
        onClose={() => setIsConnectModalOpen(false)}
        title="Connect Financial Institution via Account Aggregator"
      >
        <div className="space-y-4 text-sm">
          {connectStep === 1 ? (
            <>
              <div>
                <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Select Provider Gateway
                </label>
                <select
                  value={selectedProviderCode}
                  onChange={(e) => setSelectedProviderCode(e.target.value)}
                  className="w-full border border-gray-300 dark:border-gray-700 rounded-md p-2 text-sm bg-white dark:bg-gray-800"
                >
                  {providers.map((p) => (
                    <option key={p.id} value={p.provider_code}>
                      {p.name} ({p.status.toUpperCase()})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Select Target Banking Institution
                </label>
                <select
                  value={selectedInstitutionId}
                  onChange={(e) => setSelectedInstitutionId(e.target.value)}
                  className="w-full border border-gray-300 dark:border-gray-700 rounded-md p-2 text-sm bg-white dark:bg-gray-800"
                >
                  <option value="HDFC">HDFC Bank Ltd</option>
                  <option value="SBI">State Bank of India</option>
                  <option value="ICICI">ICICI Bank Ltd</option>
                  <option value="AXIS">Axis Bank Ltd</option>
                  <option value="KOTAK">Kotak Mahindra Bank</option>
                </select>
              </div>

              <div className="bg-indigo-50 dark:bg-indigo-950/40 p-3 rounded-md text-xs text-indigo-700 dark:text-indigo-300 space-y-1">
                <p className="font-semibold flex items-center gap-1">
                  <ShieldCheck className="w-4 h-4" /> RBI ReBIT AA Security Guarantee
                </p>
                <p>
                  Arthsavora never collects net banking passwords or OTPs. All data sharing is conducted
                  exclusively with encrypted digital consent tokens.
                </p>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <Button variant="outline" onClick={() => setIsConnectModalOpen(false)}>
                  Cancel
                </Button>
                <Button onClick={() => setConnectStep(2)} className="gap-1">
                  Continue to Consent <ChevronRight className="w-4 h-4" />
                </Button>
              </div>
            </>
          ) : (
            <>
              <div>
                <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Consent Purpose
                </label>
                <Input
                  value={consentPurpose}
                  onChange={(e) => setConsentPurpose(e.target.value)}
                  placeholder="Consent Purpose"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Authorized Data Duration (Days)
                </label>
                <Input
                  type="number"
                  value={validDays}
                  onChange={(e) => setValidDays(Number(e.target.value))}
                  min={30}
                  max={365}
                />
              </div>

              <div className="text-xs text-gray-500 space-y-1">
                <p><strong>Permitted Categories:</strong> Transactions, Account Profile, Balance Feeds</p>
                <p><strong>Frequency:</strong> Periodic Daily Sync</p>
              </div>

              <div className="flex justify-between pt-2">
                <Button variant="outline" onClick={() => setConnectStep(1)}>
                  Back
                </Button>
                <Button onClick={handleInitiateConnect} isLoading={isLoading} className="gap-1">
                  <Check className="w-4 h-4" /> Authorize & Discover Accounts
                </Button>
              </div>
            </>
          )}
        </div>
      </Modal>

      {/* Modal 2: Link Account */}
      <Modal
        isOpen={isLinkModalOpen}
        onClose={() => setIsLinkModalOpen(false)}
        title="Link Account to Arthsavora Workspace"
      >
        <div className="space-y-4 text-sm">
          {accountToLink && (
            <>
              <div className="bg-gray-50 dark:bg-gray-800 p-3 rounded-md space-y-1 text-xs">
                <p><strong>Institution:</strong> {accountToLink.institution_name}</p>
                <p><strong>Account Number:</strong> {accountToLink.masked_account_number}</p>
                <p><strong>Reported Balance:</strong> {formatPaise(accountToLink.current_balance_paise)}</p>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Internal Account Name
                </label>
                <Input
                  value={newAccountName}
                  onChange={(e) => setNewAccountName(e.target.value)}
                  placeholder="e.g. Primary HDFC Savings"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <Button variant="outline" onClick={() => setIsLinkModalOpen(false)}>
                  Cancel
                </Button>
                <Button onClick={handleConfirmLink} isLoading={isLoading}>
                  Confirm & Link Account
                </Button>
              </div>
            </>
          )}
        </div>
      </Modal>

      {/* Modal 3: Resolve Reconciliation */}
      <Modal
        isOpen={isResolveModalOpen}
        onClose={() => setIsResolveModalOpen(false)}
        title="Resolve Balance Reconciliation Variance"
      >
        <div className="space-y-4 text-sm">
          <p className="text-xs text-gray-500">
            Provide a financial explanation for the variance between the bank-reported balance and the Arthsavora book balance (e.g. uncleared cheque, pending merchant settlement).
          </p>

          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
              Explanation & Review Note
            </label>
            <textarea
              value={resolveExplanation}
              onChange={(e) => setResolveExplanation(e.target.value)}
              rows={3}
              className="w-full border border-gray-300 dark:border-gray-700 rounded-md p-2 text-sm bg-white dark:bg-gray-800"
              placeholder="e.g. ₹5,000 variance caused by cheque deposit in clearing."
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" onClick={() => setIsResolveModalOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleConfirmResolve} isLoading={isLoading}>
              Save & Resolve
            </Button>
          </div>
        </div>
      </Modal>

      {/* Modal 4: Disconnect Connection */}
      <Modal
        isOpen={isDisconnectModalOpen}
        onClose={() => setIsDisconnectModalOpen(false)}
        title="Disconnect Financial Connection"
      >
        <div className="space-y-4 text-sm">
          <p className="text-gray-600 dark:text-gray-300 text-xs">
            Are you sure you want to disconnect <strong>{selectedConnection?.institution_name}</strong>?
            All synchronized accounts will be unlinked, and active ReBIT consent tokens will be immediately revoked.
          </p>

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" onClick={() => setIsDisconnectModalOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              onClick={async () => {
                if (selectedConnection) {
                  await disconnectConnection(selectedConnection.id);
                  setIsDisconnectModalOpen(false);
                }
              }}
              isLoading={isLoading}
            >
              Disconnect & Revoke
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
