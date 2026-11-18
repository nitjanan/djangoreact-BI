import type { ApexOptions } from 'apexcharts'

import { num } from '@/lib/format'

// ชุดสีหลักจากหน้าเดิม — ลำดับนี้ผ่านการตรวจแยกสีสำหรับคนตาบอดสีแล้ว ห้ามสลับลำดับ
export const PALETTE = [
  '#2a78d6', '#eb6834', '#1baf7a', '#eda100',
  '#e87ba4', '#008300', '#4a3aa7', '#e34948',
]  // prettier-ignore

// ApexCharts ใส่สีเป็น attribute ของ SVG ซึ่งใช้ CSS variable ไม่ได้ -> ใช้ค่าสีตรง ๆ
export const TEXT = '#172033'
export const TEXT_MUTED = '#5B6577'
export const GRID = '#EBEEF2'

// ข้อมูลเดียวกันใช้สีเดียวกันทุกกราฟ
export const COLOR = {
  repair: PALETTE[0], // ค่าใช้จ่ายซ่อม - น้ำเงิน
  line: PALETTE[1], // เส้นอัตรา/เปอร์เซ็นต์ - ส้ม
  oil: PALETTE[2], // น้ำมัน - เขียวน้ำทะเล
  work: PALETTE[6], // ชั่วโมงทำงาน - ม่วง
  failure: PALETTE[7], // จำนวนครั้งที่เสีย - แดง
}

/** ค่าเริ่มต้นของทุกกราฟ (เดิม: window.Apex) */
export function baseOptions(extra: ApexOptions): ApexOptions {
  return {
    ...extra,
    chart: {
      fontFamily: 'inherit',
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
    stroke: { width: [0, 3], curve: 'smooth' },
    plotOptions: { bar: { borderRadius: 6, columnWidth: '55%' } },
    // แสดงค่าบนเส้น ส่วนแท่งดูได้จาก tooltip (เหมือนหน้าเดิม)
    dataLabels: {
      enabled: true,
      enabledOnSeries: [1],
      formatter: (v) => (typeof v === 'number' ? rightFormat(v) : ''),
      offsetY: -8,
      style: { fontSize: '11px' },
    },
    yaxis: [
      { title: { text: leftTitle }, labels: { formatter: (v) => leftFormat(v) } },
      { opposite: true, title: { text: rightTitle }, labels: { formatter: (v) => rightFormat(v) } },
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
