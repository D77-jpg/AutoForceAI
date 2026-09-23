"use client";

/**
 * Apple 风格分段控件（样式见 globals.css .segmented-control）
 */
export interface SegmentOption<T extends string> {
  value: T;
  label: string;
  count?: number;
}

export default function SegmentedControl<T extends string>({
  options,
  value,
  onChange,
  ariaLabel,
}: {
  options: SegmentOption<T>[];
  value: T;
  onChange: (v: T) => void;
  ariaLabel: string;
}) {
  return (
    <div className="segmented-control" role="tablist" aria-label={ariaLabel}>
      {options.map((opt) => (
        <button
          key={opt.value}
          type="button"
          role="tab"
          aria-selected={value === opt.value}
          className="segmented-control__item"
          onClick={() => onChange(opt.value)}
        >
          {opt.label}
          {opt.count !== undefined && (
            <span className="tabular-nums text-[11px] opacity-70">{opt.count}</span>
          )}
        </button>
      ))}
    </div>
  );
}
