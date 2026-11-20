/** ช่วงเวลาของ dashboard: ปี + ช่วงเดือน และการเทียบกับช่วงเดียวกันของปีก่อน */

export const MONTHS_SHORT = [
  "ม.ค.",
  "ก.พ.",
  "มี.ค.",
  "เม.ย.",
  "พ.ค.",
  "มิ.ย.",
  "ก.ค.",
  "ส.ค.",
  "ก.ย.",
  "ต.ค.",
  "พ.ย.",
  "ธ.ค.",
];
const MONTHS_LONG = [
  "มกราคม",
  "กุมภาพันธ์",
  "มีนาคม",
  "เมษายน",
  "พฤษภาคม",
  "มิถุนายน",
  "กรกฎาคม",
  "สิงหาคม",
  "กันยายน",
  "ตุลาคม",
  "พฤศจิกายน",
  "ธันวาคม",
];

export type MonthRange = { from: number; to: number };

export type PeriodOption = MonthRange & {
  key: string;
  label: string;
  group: string;
};

/** ตัวเลือกช่วงเดือนสำเร็จรูป (ทั้งปีใช้ key "all" = ไม่ส่งเดือนไป backend) */
export const PERIOD_OPTIONS: PeriodOption[] = [
  { key: "all", label: "ทั้งปี", group: "", from: 1, to: 12 },
  { key: "h1", label: "ครึ่งปีแรก (ม.ค.–มิ.ย.)", group: "ครึ่งปี", from: 1, to: 6 },
  { key: "h2", label: "ครึ่งปีหลัง (ก.ค.–ธ.ค.)", group: "ครึ่งปี", from: 7, to: 12 },
  ...[1, 2, 3, 4].map((q) => ({
    key: `q${q}`,
    label: `ไตรมาส ${q} (${MONTHS_SHORT[q * 3 - 3]}–${MONTHS_SHORT[q * 3 - 1]})`,
    group: "ไตรมาส",
    from: q * 3 - 2,
    to: q * 3,
  })),
  ...MONTHS_LONG.map((name, i) => ({
    key: `m${i + 1}`,
    label: name,
    group: "เดือน",
    from: i + 1,
    to: i + 1,
  })),
];

/** ช่วงที่ backend ใช้จริง -> key ของตัวเลือก (ทั้งปี = ตั้งแต่ ม.ค. ถึงเดือนล่าสุดของปี) */
export function periodKey(
  range: MonthRange,
  lastMonth: number,
  isWholeYear: boolean,
) {
  if (isWholeYear) return "all";
  const hit = PERIOD_OPTIONS.find(
    (o) =>
      o.key !== "all" &&
      o.from === range.from &&
      Math.min(o.to, lastMonth) === range.to,
  );
  return hit?.key ?? "custom";
}

/** "ม.ค.–มี.ค. 2026" / "มี.ค. 2026" / "ปี 2026" */
export function periodLabel(
  year: number,
  range: MonthRange,
  wholeYear: boolean,
) {
  if (wholeYear) return `ปี ${year}`;
  const months =
    range.from === range.to
      ? MONTHS_SHORT[range.from - 1]
      : `${MONTHS_SHORT[range.from - 1]}–${MONTHS_SHORT[range.to - 1]}`;
  return `${months} ${year}`;
}

/** เปลี่ยนไปกี่ % (null = เทียบไม่ได้ เช่นปีก่อนเป็น 0) */
export function pctChange(
  now: number | null | undefined,
  before: number | null | undefined,
) {
  if (now == null || before == null || before === 0) return null;
  return ((now - before) / Math.abs(before)) * 100;
}

/** ช่วงของปีก่อนที่ใช้เทียบ: ครบ 12 เดือน = "ปี 2025" ไม่ครบ = "ม.ค.–พ.ย. 2025" */
export function compareLabel(c: {
  year: number;
  month_from: number;
  month_to: number;
}) {
  const range = { from: c.month_from, to: c.month_to };
  return periodLabel(c.year, range, c.month_from === 1 && c.month_to === 12);
}
