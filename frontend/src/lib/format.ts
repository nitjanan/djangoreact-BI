const formatters = new Map<number, Intl.NumberFormat>()

/** 1234.5 -> "1,234.50" (แบบเดียวกับ floatformat + intcomma ของหน้าเดิม) */
export function num(value: number | null | undefined, digits = 2, empty = '-') {
  if (value === null || value === undefined || Number.isNaN(value)) return empty
  let f = formatters.get(digits)
  if (!f) {
    f = new Intl.NumberFormat('en-US', {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    })
    formatters.set(digits, f)
  }
  return f.format(value)
}

export function clampPercent(value: number | null | undefined) {
  return Math.max(0, Math.min(100, value ?? 0))
}
