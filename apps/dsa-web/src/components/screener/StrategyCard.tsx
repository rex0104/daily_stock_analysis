import type React from 'react';
import { cn } from '../../utils/cn';

interface StrategyCardProps {
  id: string;
  name: string;
  description: string;
  icon: string;
  selected: boolean;
  disabled: boolean;
  onSelect: () => void;
}

export const StrategyCard: React.FC<StrategyCardProps> = ({
  name,
  description,
  icon,
  selected,
  disabled,
  onSelect,
}) => (
  <button
    type="button"
    onClick={onSelect}
    disabled={disabled}
    className={cn(
      'relative rounded-xl p-3.5 text-left transition-all',
      'border bg-surface hover:bg-surface-hover',
      selected
        ? 'border-[hsl(var(--primary))] ring-1 ring-[hsl(var(--primary))]'
        : 'border-subtle',
      disabled && 'pointer-events-none opacity-50',
    )}
  >
    {selected && (
      <span className="absolute right-2 top-2 flex h-5 w-5 items-center justify-center rounded-full bg-[hsl(var(--primary))] text-[10px] text-white">
        ✓
      </span>
    )}
    <div className="mb-1.5 text-xl">{icon}</div>
    <div className="text-sm font-semibold text-foreground">{name}</div>
    <div className="mt-1 text-xs leading-relaxed text-secondary-text">{description}</div>
  </button>
);
