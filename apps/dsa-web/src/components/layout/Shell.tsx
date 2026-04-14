import type React from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { SidebarNav, NAV_ITEMS } from './SidebarNav';
import { cn } from '../../utils/cn';
import { ThemeToggle } from '../theme/ThemeToggle';
import { useAgentChatStore } from '../../stores/agentChatStore';
import { StatusDot } from '../common/StatusDot';

type ShellProps = {
  children?: React.ReactNode;
};

export const Shell: React.FC<ShellProps> = ({ children }) => {
  const completionBadge = useAgentChatStore((state) => state.completionBadge);

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Mobile: top-right ThemeToggle (hamburger replaced by bottom tab bar) */}
      <div className="pointer-events-none fixed inset-x-0 top-3 z-40 flex items-start justify-end px-3 lg:hidden">
        <div className="pointer-events-auto">
          <ThemeToggle />
        </div>
      </div>

      <div className="mx-auto flex min-h-screen w-full max-w-[1680px] px-3 py-3 sm:px-4 sm:py-4 lg:px-5">
        <aside
          className={cn(
            'sticky top-3 z-40 hidden shrink-0 overflow-visible rounded-[1.5rem] border border-[var(--shell-sidebar-border)] bg-card/72 p-2 shadow-soft-card backdrop-blur-sm transition-[width] duration-200 lg:flex',
            'max-h-[calc(100vh-1.5rem)] self-start sm:top-4 sm:max-h-[calc(100vh-2rem)]',
            'w-[116px]'
          )}
          aria-label="桌面侧边导航"
        >
          <SidebarNav collapsed={false} />
        </aside>

        {/* pt-14 leaves room for the floating ThemeToggle on mobile; pb-[4.5rem] leaves room for bottom tab bar */}
        <main className="relative min-h-0 min-w-0 flex-1 pb-[4.5rem] pt-14 lg:pb-0 lg:pl-3 lg:pt-0 touch-pan-y">
          <div className="pointer-events-auto absolute right-2 top-2 z-30 hidden lg:block">
            <ThemeToggle />
          </div>
          {children ?? <Outlet />}
        </main>
      </div>

      {/* Mobile bottom tab bar — replaces hamburger/drawer */}
      <nav
        className="fixed bottom-0 inset-x-0 z-40 flex border-t border-border/60 bg-card/90 backdrop-blur-md safe-area-bottom lg:hidden"
        aria-label="底部导航"
      >
        {NAV_ITEMS.map(({ key, label, to, icon: Icon, exact, badge }) => (
          <NavLink
            key={key}
            to={to}
            end={exact}
            aria-label={label}
            className={({ isActive }) =>
              cn(
                'relative flex flex-1 flex-col items-center justify-center gap-0.5 py-2 text-[10px] leading-none transition-colors',
                isActive
                  ? 'text-[hsl(var(--primary))]'
                  : 'text-muted-text'
              )
            }
          >
            {({ isActive }) => (
              <>
                <div className="relative">
                  <Icon className={cn('h-5 w-5', isActive && 'text-[var(--nav-icon-active)]')} />
                  {badge === 'completion' && completionBadge && (
                    <StatusDot
                      tone="info"
                      className="absolute -right-1 -top-1 border border-card"
                      aria-label="问股有新消息"
                    />
                  )}
                </div>
                <span>{label}</span>
              </>
            )}
          </NavLink>
        ))}
      </nav>
    </div>
  );
};
