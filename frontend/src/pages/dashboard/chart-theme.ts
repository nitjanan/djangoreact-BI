import type { ApexOptions } from 'apexcharts'

import { num } from '@/lib/format'

// ชุดสีธีม "ทะเลกับปะการัง" — สีที่อยู่กราฟเดียวกันต่างกันทั้งเฉดและความสว่าง
// (เขียวน้ำทะเล / ปะการัง / น้ำเงิน / เหลืองทอง / ม่วงฟ้า / แดงเข้ม) อ่านแยกได้สำหรับคนตาบอดสี
export const PALETTE = [
  '#0e8a8f', '#ff7a59', '#2a78d6', '#eda100',
  '#6366f1', '#c0392b', '#7a8a94', '#2f9e44',
]  // prettier-ignore

// สีของหมวดหมู่ (ประเภทการซ่อม, ประเภทรถ) ไล่ตามชุดสีธีมให้แต่ละแท่งต่างสีกัน
export const CATEGORY_COLORS = [
  PALETTE[0], PALETTE[1], PALETTE[3], PALETTE[4],
  '#0b4f5a', '#f2a48f', '#8fd3d1', '#a5a8f5',
]  // prettier-ignore

// ApexCharts ใส่สีเป็น attribute ของ SVG ซึ่งใช้ CSS variable ไม่ได้ -> ใช้ค่าสีตรง ๆ
export const TEXT = '#12303a'
export const TEXT_MUTED = '#4b6570'
export const GRID = '#e3eeee'

// ข้อมูลเดียวกันใช้สีเดียวกันทุกกราฟ
export const COLOR = {
  repair: PALETTE[0], // ค่าใช้จ่ายซ่อม - เขียวน้ำทะเล
  line: PALETTE[1], // เส้นอัตรา/เปอร์เซ็นต์ - ปะการัง
  oil: PALETTE[3], // น้ำมัน - เหลืองทอง
  work: PALETTE[4], // ชั่วโมงทำงาน - ม่วงฟ้า
  failure: PALETTE[1], // จำนวนครั้งที่เสีย - ปะการัง (สีเตือนของธีม)
  highlight: PALETTE[1], // จุดเน้น/คันที่เลือก - ปะการัง (เดียวกับ --signal)
}

/** ค่าเริ่มต้นของทุกกราฟ (เดิม: window.Apex) */
export function baseOptions(extra: ApexOptions): ApexOptions {
  return {
    ...extra,
    chart: {
      fontFamily: "'IBM Plex Sans Thai', system-ui, sans-serif",
      foreColor: TEXT_MUTED,
      toolbar: { show: false },
      animations: { speed: 400 },
      ...extra.chart,
    },
    grid: { borderColor: GRID, strokeDashArray: 4, ...extra.grid },
    legend: { fontSize: '13px', ...extra.legend },
    tooltip: { theme: 'light', ...extra.tooltip },
    markers: { size: 4, strokeWidth: 2, strokeColors: '#fff', ...extra.markers },
  }
}

/** ป้ายรถในกราฟ: ทะเบียน (บริษัท) */
export const carLabel = (label: string, company?: string | null) =>
  company ? `${label} (${company})` : label

export const baht = (v: number) => `${num(v, 2)} บาท`
export const kilo = (v: number) => `${(v / 1000).toFixed(1)}K`

/** กราฟแท่ง + เส้น 2 แกน (น้ำมัน, ชั่วโมงทำงาน, ค่าซ่อมเทียบชั่วโมง, ความถี่การเสีย) */
export function comboOptions({
  labels,
  colors,
  leftTitle,
  rightTitle,
  leftFormat,
  rightFormat,
}: {
  labels: string[]
  colors: [string, string]
  leftTitle: string
  rightTitle: string
  leftFormat: (v: number) => string
  rightFormat: (v: number) => string
}): ApexOptions {
  return baseOptions({
    chart: { type: 'line' },
    colors,
    labels,
    // เส้นตรง + จุดขนาดเดียวกับกราฟต้นทุนซ่อมต่อชั่วโมง
    stroke: { width: [0, 3], curve: 'straight' },
    markers: { size: [0, 5] },
    plotOptions: { bar: { borderRadius: 6, columnWidth: '55%' } },
    // แสดงค่าบนเส้นเป็นตัวหนังสือเรียบ ๆ (ไม่มีกล่องสี) เหมือนกราฟอื่น
    // ค่า 0 ไม่แสดงป้าย (เดือนที่ไม่มีข้อมูลระยะทาง/ชั่วโมงมาตรฐาน) ดูค่าได้จาก tooltip
    dataLabels: {
      enabled: true,
      enabledOnSeries: [1],
      formatter: (v) => (typeof v === 'number' && v !== 0 ? rightFormat(v) : ''),
      offsetY: -8,
      background: { enabled: false },
      style: { fontSize: '11px', colors: [TEXT] },
    },
    // จำนวนช่องเท่ากันทั้งสองแกน -> เส้นตารางของสองแกนตรงกัน อ่านค่าข้ามแกนง่ายขึ้น
    yaxis: [
      { tickAmount: 5, forceNiceScale: true, title: { text: leftTitle }, labels: { formatter: (v) => leftFormat(v) } },
      { opposite: true, tickAmount: 5, forceNiceScale: true, title: { text: rightTitle }, labels: { formatter: (v) => rightFormat(v) } },
    ],
    tooltip: {
      shared: true,
      intersect: false,
      y: {
        formatter: (v, opts) =>
          v == null ? '-' : opts?.seriesIndex === 0 ? leftFormat(v) : rightFormat(v),
      },
    },
  })
}
