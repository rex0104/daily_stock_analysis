import React, { useEffect, useRef, useState } from 'react';
import { KeyRound, LogOut } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { cn } from '../../utils/cn';
import { ConfirmDialog } from './ConfirmDialog';

type UserMenuProps = {
  collapsed?: boolean;
  /** Called after navigation so parent can close the mobile drawer */
  onNavigate?: () => void;
};

export const UserMenu: React.FC<UserMenuProps> = ({ collapsed = false, onNavigate }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    if (!open) return undefined;

    const handlePointerDown = (e: PointerEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };

    document.addEventListener('pointerdown', handlePointerDown);
    return () => {
      document.removeEventListener('pointerdown', handlePointerDown);
    };
  }, [open]);

  if (!user) return null;

  const initials = user.nickname ? user.nickname[0].toUpperCase() : user.email[0].toUpperCase();

  const handleChangePassword = () => {
    setOpen(false);
    onNavigate?.();
    void navigate('/settings');
  };

  const handleLogoutClick = () => {
    setOpen(false);
    setShowLogoutConfirm(true);
  };

  const handleLogoutConfirm = () => {
    setShowLogoutConfirm(false);
    onNavigate?.();
    void logout();
  };

  return (
    <>
      <div ref={menuRef} className="relative border-t border-border/40 pt-2">
        {/* Trigger button — matches nav item sizing */}
        <button
          type="button"
          onClick={() => setOpen((prev) => !prev)}
          aria-haspopup="menu"
          aria-expanded={open}
          className={cn(
            'flex w-full cursor-pointer select-none items-center gap-3 text-sm text-secondary-text transition-all',
            'h-[var(--nav-item-height)]',
            collapsed ? 'justify-center px-0' : 'px-[var(--nav-item-padding-x)]',
            'hover:bg-[var(--nav-hover-bg)] hover:text-foreground rounded-lg',
          )}
        >
          {/* Avatar circle */}
          <span className="ml-1 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary-gradient text-[hsl(var(--primary-foreground))] text-[10px] font-semibold">
            {initials}
          </span>
          {!collapsed && (
            <span className="min-w-0 truncate">{user.nickname || user.email}</span>
          )}
        </button>

        {/* Dropdown panel */}
        {open && (
          <div
            role="menu"
            className={cn(
              'absolute z-50 min-w-[160px] rounded-xl border border-border/70 bg-card/85 py-1 shadow-soft-card backdrop-blur-md',
              // Place above the trigger in the sidebar
              'bottom-full mb-2',
              collapsed ? 'left-0' : 'left-0 right-0'
            )}
          >
            {/* Nickname display */}
            <div className="px-3 py-2 border-b border-border/40">
              <p className="text-xs text-secondary-text truncate">{user.nickname || user.email}</p>
              {user.nickname && (
                <p className="text-[11px] text-muted-text truncate">{user.email}</p>
              )}
            </div>

            {/* Change password */}
            <button
              type="button"
              role="menuitem"
              onClick={handleChangePassword}
              className="flex w-full items-center gap-2 px-3 py-2 text-sm text-foreground hover:bg-[var(--nav-hover-bg)] transition-colors"
            >
              <KeyRound className="h-4 w-4 shrink-0 text-secondary-text" />
              <span>修改密码</span>
            </button>

            {/* Logout */}
            <button
              type="button"
              role="menuitem"
              onClick={handleLogoutClick}
              className="flex w-full items-center gap-2 px-3 py-2 text-sm text-destructive hover:bg-[var(--nav-hover-bg)] transition-colors"
            >
              <LogOut className="h-4 w-4 shrink-0" />
              <span>退出登录</span>
            </button>
          </div>
        )}
      </div>

      <ConfirmDialog
        isOpen={showLogoutConfirm}
        title="退出登录"
        message="确认退出当前登录状态吗？退出后需要重新输入密码。"
        confirmText="确认退出"
        cancelText="取消"
        isDanger
        onConfirm={handleLogoutConfirm}
        onCancel={() => setShowLogoutConfirm(false)}
      />
    </>
  );
};
