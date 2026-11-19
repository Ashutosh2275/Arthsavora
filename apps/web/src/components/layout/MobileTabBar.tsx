import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { LayoutDashboard, Wallet, Plus, Camera, Bell } from 'lucide-react';
import { useNotificationStore } from '@/store/useNotificationStore';

export const MobileTabBar: React.FC = () => {
  const location = useLocation();
  const unreadCount = useNotificationStore((state) => state.unreadCount);

  const navItems = [
    {
      to: '/',
      label: 'Home',
      icon: LayoutDashboard,
      exact: true,
    },
    {
      to: '/accounts',
      label: 'Accounts',
      icon: Wallet,
    },
    {
      to: '/transactions?action=new',
      label: 'Add Tx',
      icon: Plus,
      isAction: true,
    },
    {
      to: '/documents?action=scan',
      label: 'Scan',
      icon: Camera,
    },
    {
      to: '/notifications',
      label: 'Alerts',
      icon: Bell,
      badge: unreadCount > 0 ? unreadCount : undefined,
    },
  ];

  return (
    <nav
      aria-label="Mobile Bottom Navigation"
      className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-slate-950/95 border-t border-slate-800/80 backdrop-blur-lg px-2 py-1 safe-area-pb"
    >
      <div className="flex items-center justify-around h-14 max-w-md mx-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive =
            item.exact
              ? location.pathname === item.to
              : location.pathname === item.to.split('?')[0];

          if (item.isAction) {
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className="flex flex-col items-center justify-center -mt-5"
                aria-label="Record New Transaction"
              >
                <div className="w-12 h-12 rounded-full bg-gradient-to-tr from-indigo-600 to-indigo-500 text-white flex items-center justify-center shadow-lg shadow-indigo-500/30 active:scale-95 transition-transform border-2 border-slate-950">
                  <Plus size={22} strokeWidth={2.5} />
                </div>
                <span className="text-[10px] font-medium text-indigo-400 mt-1">{item.label}</span>
              </NavLink>
            );
          }

          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={`flex flex-col items-center justify-center py-1 px-2.5 rounded-lg transition-colors relative min-w-[56px] ${
                isActive ? 'text-indigo-400' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <div className="relative">
                <Icon size={20} strokeWidth={isActive ? 2.2 : 1.8} />
                {item.badge !== undefined && (
                  <span className="absolute -top-1 -right-2 bg-rose-500 text-white text-[9px] font-bold px-1.5 py-0.2 rounded-full min-w-[14px] text-center leading-tight">
                    {item.badge > 99 ? '99+' : item.badge}
                  </span>
                )}
              </div>
              <span className={`text-[10px] mt-1 ${isActive ? 'font-semibold text-white' : 'font-medium'}`}>
                {item.label}
              </span>
            </NavLink>
          );
        })}
      </div>
    </nav>
  );
};

export default MobileTabBar;
