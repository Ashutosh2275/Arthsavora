import React, { useEffect, useState } from 'react';
import {
  Bell,
  Check,
  CheckCheck,
  Archive,
  Trash2,
  Settings,
  AlertTriangle,
  ShieldAlert,
  CreditCard,
  PieChart,
  Target,
  Clock,
  Sparkles,
  FileText,
  Mail,
  Smartphone,
  ExternalLink,
  Moon,
  RefreshCw,
  Plus,
} from 'lucide-react';
import { useNotificationStore } from '@/store/useNotificationStore';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';

export const Notifications: React.FC = () => {
  const {
    notifications,
    total,
    unreadCount,
    isLoading,
    error,
    activeCategory,
    preferences,
    setActiveCategory,
    fetchNotifications,
    fetchUnreadCount,
    markAsRead,
    markAllAsRead,
    archiveNotification,
    deleteNotification,
    fetchPreferences,
    updatePreference,
    triggerTestNotification,
    clearError,
  } = useNotificationStore();

  const [quietHoursStart, setQuietHoursStart] = useState('22:00');
  const [quietHoursEnd, setQuietHoursEnd] = useState('08:00');
  const [timezone, setTimezone] = useState('Asia/Kolkata');
  const [quietEnabled, setQuietEnabled] = useState(false);

  useEffect(() => {
    fetchNotifications();
    fetchUnreadCount();
    fetchPreferences();
  }, []);

  const categories = [
    { id: 'all', label: 'All', icon: Bell },
    { id: 'unread', label: `Unread (${unreadCount})`, icon: Check },
    { id: 'transaction', label: 'Transactions', icon: CreditCard },
    { id: 'budget', label: 'Budgets', icon: PieChart },
    { id: 'goal', label: 'Goals', icon: Target },
    { id: 'recurring', label: 'Recurring', icon: Clock },
    { id: 'anomaly', label: 'Anomalies', icon: AlertTriangle },
    { id: 'security', label: 'Security', icon: ShieldAlert },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'transaction':
        return <CreditCard className="h-5 w-5 text-indigo-400" />;
      case 'budget':
        return <PieChart className="h-5 w-5 text-amber-400" />;
      case 'goal':
        return <Target className="h-5 w-5 text-emerald-400" />;
      case 'recurring':
        return <Clock className="h-5 w-5 text-purple-400" />;
      case 'anomaly':
        return <AlertTriangle className="h-5 w-5 text-rose-400" />;
      case 'security':
        return <ShieldAlert className="h-5 w-5 text-red-500" />;
      case 'document':
        return <FileText className="h-5 w-5 text-teal-400" />;
      case 'assistant':
        return <Sparkles className="h-5 w-5 text-cyan-400" />;
      default:
        return <Bell className="h-5 w-5 text-slate-400" />;
    }
  };

  const getSeverityBadgeVariant = (severity: string): 'neutral' | 'income' | 'expense' | 'warning' | 'info' => {
    switch (severity) {
      case 'critical':
        return 'expense';
      case 'warning':
        return 'warning';
      case 'success':
        return 'income';
      case 'info':
        return 'info';
      default:
        return 'neutral';
    }
  };

  const handleSaveQuietHours = () => {
    updatePreference({
      category: '*',
      channel: 'email',
      is_enabled: true,
      quiet_hours_enabled: quietEnabled,
      quiet_hours_start: quietHoursStart,
      quiet_hours_end: quietHoursEnd,
      timezone,
    });
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <Bell className="h-7 w-7 text-indigo-400" />
            Notification Center
          </h1>
          <p className="text-sm text-slate-400">
            Unified financial alerts, budget warnings, upcoming commitments, and security updates.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => triggerTestNotification('transaction', 'info')}
            className="flex items-center gap-1.5 text-xs text-slate-300 border-slate-700 hover:bg-slate-800"
          >
            <Plus className="h-3.5 w-3.5" />
            Test Alert
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => markAllAsRead()}
            disabled={unreadCount === 0}
            className="flex items-center gap-1.5 text-xs text-indigo-300 border-indigo-500/30 hover:bg-indigo-500/10"
          >
            <CheckCheck className="h-3.5 w-3.5" />
            Mark all read
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => fetchNotifications()}
            className="p-2 text-slate-400 hover:text-white border-slate-700"
          >
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-xs text-rose-300 flex items-center justify-between">
          <span>{error}</span>
          <button onClick={clearError} className="underline text-slate-400 hover:text-white">
            Dismiss
          </button>
        </div>
      )}

      {/* Tabs */}
      <div className="flex items-center gap-1 overflow-x-auto border-b border-slate-800/80 pb-2">
        {categories.map((cat) => {
          const Icon = cat.icon;
          const isActive = activeCategory === cat.id;
          return (
            <button
              key={cat.id}
              onClick={() => setActiveCategory(cat.id)}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-medium whitespace-nowrap transition-all ${
                isActive
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <Icon className="h-4 w-4" />
              {cat.label}
            </button>
          );
        })}
      </div>

      {/* Content */}
      {activeCategory === 'settings' ? (
        /* Settings Tab */
        <div className="space-y-6 max-w-4xl">
          <Card className="p-5 bg-slate-900/90 border-slate-800 space-y-4">
            <h2 className="text-base font-semibold text-white flex items-center gap-2">
              <Moon className="h-5 w-5 text-indigo-400" />
              Quiet Hours & Timezone Configuration
            </h2>
            <p className="text-xs text-slate-400">
              Suppress noisy outbound emails and push alerts during your rest hours. Critical security notifications always bypass quiet hours.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 pt-2">
              <div className="flex items-center gap-3 md:col-span-4">
                <input
                  type="checkbox"
                  id="quietEnabled"
                  checked={quietEnabled}
                  onChange={(e) => setQuietEnabled(e.target.checked)}
                  className="rounded border-slate-700 bg-slate-950 text-indigo-600 focus:ring-indigo-500"
                />
                <label htmlFor="quietEnabled" className="text-sm font-medium text-slate-200 cursor-pointer">
                  Enable Quiet Hours
                </label>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Start Time</label>
                <input
                  type="time"
                  value={quietHoursStart}
                  onChange={(e) => setQuietHoursStart(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">End Time</label>
                <input
                  type="time"
                  value={quietHoursEnd}
                  onChange={(e) => setQuietHoursEnd(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Timezone</label>
                <select
                  value={timezone}
                  onChange={(e) => setTimezone(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="Asia/Kolkata">Asia/Kolkata (IST)</option>
                  <option value="UTC">UTC</option>
                  <option value="America/New_York">America/New_York (EST)</option>
                  <option value="Europe/London">Europe/London (GMT)</option>
                </select>
              </div>

              <div className="flex items-end">
                <Button variant="primary" size="sm" onClick={handleSaveQuietHours} className="w-full text-xs">
                  Save Quiet Hours
                </Button>
              </div>
            </div>
          </Card>

          <Card className="p-5 bg-slate-900/90 border-slate-800 space-y-4">
            <h2 className="text-base font-semibold text-white flex items-center gap-2">
              <Smartphone className="h-5 w-5 text-indigo-400" />
              Delivery Channels & Categories
            </h2>
            <div className="divide-y divide-slate-800">
              {[
                { cat: 'transaction', title: 'Transaction Activity', desc: 'Alerts when funds are recorded or confirmed' },
                { cat: 'budget', title: 'Budget Limits & Thresholds', desc: 'Alerts when category spending hits 80%, 90%, 100%' },
                { cat: 'goal', title: 'Goal Milestones', desc: 'Celebrations when reaching 25%, 50%, 100% of targets' },
                { cat: 'recurring', title: 'Recurring Bills & Subscriptions', desc: 'Advance reminders 7, 3, and 1 day before due dates' },
                { cat: 'anomaly', title: 'Spending Anomalies & Risk', desc: 'Deviations from typical patterns and balance alerts' },
                { cat: 'security', title: 'Account Security', desc: 'Critical login and authentication events (mandatory)' },
              ].map((item) => (
                <div key={item.cat} className="py-3 flex items-center justify-between">
                  <div>
                    <div className="text-sm font-medium text-white">{item.title}</div>
                    <div className="text-xs text-slate-400">{item.desc}</div>
                  </div>
                  <div className="flex items-center gap-3">
                    <label className="text-xs text-slate-300 flex items-center gap-1.5 cursor-pointer">
                      <input
                        type="checkbox"
                        defaultChecked
                        className="rounded border-slate-700 bg-slate-950 text-indigo-600 focus:ring-indigo-500"
                      />
                      In-App
                    </label>
                    <label className="text-xs text-slate-300 flex items-center gap-1.5 cursor-pointer">
                      <input
                        type="checkbox"
                        defaultChecked
                        className="rounded border-slate-700 bg-slate-950 text-indigo-600 focus:ring-indigo-500"
                      />
                      Email
                    </label>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      ) : (
        /* Notifications List */
        <div className="space-y-3">
          {isLoading && notifications.length === 0 ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <Card key={i} className="p-4 bg-slate-900/60 border-slate-800 animate-pulse">
                  <div className="h-4 bg-slate-800 rounded w-1/4 mb-2" />
                  <div className="h-3 bg-slate-800/60 rounded w-3/4" />
                </Card>
              ))}
            </div>
          ) : notifications.length === 0 ? (
            <Card className="p-12 text-center bg-slate-900/40 border-slate-800 rounded-2xl">
              <Bell className="h-10 w-10 text-slate-600 mx-auto mb-3" />
              <h3 className="text-base font-semibold text-slate-300 mb-1">No notifications</h3>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                You're all caught up! Relevant budget alerts, transaction confirmations, and commitments will appear here.
              </p>
            </Card>
          ) : (
            notifications.map((notif) => {
              const isUnread = !notif.is_read;
              return (
                <Card
                  key={notif.id}
                  className={`p-4 transition-all rounded-xl border ${
                    isUnread
                      ? 'bg-slate-900/90 border-indigo-500/40 shadow-sm'
                      : 'bg-slate-950/60 border-slate-800/80 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-3">
                      <div className="p-2 rounded-xl bg-slate-800/80 border border-slate-700/60 shrink-0">
                        {getCategoryIcon(notif.category)}
                      </div>
                      <div className="space-y-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          {isUnread && <span className="h-2 w-2 rounded-full bg-indigo-500 shrink-0" />}
                          <h4 className="text-sm font-semibold text-white">{notif.title}</h4>
                          <Badge variant={getSeverityBadgeVariant(notif.severity)} size="sm">
                            {notif.severity}
                          </Badge>
                          <span className="text-[11px] text-slate-500 font-mono">
                            {new Date(notif.created_at).toLocaleDateString('en-IN', {
                              day: 'numeric',
                              month: 'short',
                              hour: '2-digit',
                              minute: '2-digit',
                            })}
                          </span>
                        </div>
                        <p className="text-xs text-slate-300 leading-relaxed">{notif.message}</p>

                        {/* Metadata / Action Links */}
                        <div className="flex items-center gap-3 pt-2">
                          {notif.action_url && (
                            <a
                              href={notif.action_url}
                              className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-medium"
                            >
                              View details <ExternalLink className="h-3 w-3" />
                            </a>
                          )}
                          <div className="flex items-center gap-1.5 text-[11px] text-slate-500">
                            {notif.deliveries?.map((d) => (
                              <span key={d.id} className="flex items-center gap-1">
                                {d.channel === 'email' && (
                                  <span title="Email sent">
                                    <Mail className="h-3 w-3 text-slate-400" />
                                  </span>
                                )}
                                {d.channel === 'web_push' && (
                                  <span title="Push sent">
                                    <Smartphone className="h-3 w-3 text-slate-400" />
                                  </span>
                                )}
                              </span>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-1 shrink-0">
                      {isUnread && (
                        <button
                          onClick={() => markAsRead(notif.id)}
                          className="p-1.5 text-slate-400 hover:text-indigo-400 rounded-lg hover:bg-slate-800"
                          title="Mark as read"
                        >
                          <Check className="h-4 w-4" />
                        </button>
                      )}
                      <button
                        onClick={() => archiveNotification(notif.id)}
                        className="p-1.5 text-slate-400 hover:text-amber-400 rounded-lg hover:bg-slate-800"
                        title="Archive"
                      >
                        <Archive className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => deleteNotification(notif.id)}
                        className="p-1.5 text-slate-400 hover:text-rose-400 rounded-lg hover:bg-slate-800"
                        title="Delete"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                </Card>
              );
            })
          )}
        </div>
      )}
    </div>
  );
};
