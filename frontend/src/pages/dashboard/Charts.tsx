import Chart from 'react-apexcharts'

import type { Schemas } from '@/api/client'
import { pieRows, seriesRows } from '@/lib/export-excel'
import { num } from '@/lib/format'

import { ChartCard } from './ChartCard'
import { COLOR, PALETTE, TEXT, baht, baseOptions, comboOptions, kilo } from './chart-theme'

type Charts = Schemas['Charts']

const pieColors = (n: number) => Array.from({ length: n }, (_, i) => PALETTE[i % PALETTE.length])

function PieCard({
  title,
  type,
  chart,
}: {
  title: string
  type: 'pie' | 'donut'
  chart: Schemas['SeriesTotalChart']
}) {
  return (
    <ChartCard
      title={title}
      unit="บาท"
      empty={chart.series.length === 0}
      rows={pieRows(chart.labels, chart.series)}
    >
      <Chart
        type={type}
        height={320}
        series={chart.series}
        options={baseOptions({
          labels: chart.labels,
          colors: pieColors(chart.labels.length),
          stroke: { width: 2, colors: ['#fff'] },
          legend: { position: 'bottom' },
          plotOptions: {
            pie: {
              donut: {
                size: '62%',
                labels: {
                  show: true,
                  total: { show: true, label: 'รวม', formatter: () => num(chart.total, 0) },
                },
              },
            },
          },
          tooltip: { y: { formatter: baht } },
        })}
      />
    </ChartCard>
  )
}

export function RepairByMonthChart({ chart }: { chart: Charts['repair_by_month'] }) {
  const name = 'ค่าใช้จ่ายซ่อมบำรุง'
  return (
    <ChartCard
      title="ค่าใช้จ่ายซ่อมบำรุงรวม"
      unit="บาท"
      empty={chart.series.length === 0}
      rows={seriesRows(chart.labels, [{ name, data: chart.series }])}
    >
      <Chart
        type="bar"
        height={280}
        series={[{ name, data: chart.series }]}
        options={baseOptions({
          colors: [COLOR.repair],
          xaxis: { categories: chart.labels },
          plotOptions: { bar: { borderRadius: 6, columnWidth: '55%', dataLabels: { position: 'top' } } },
          dataLabels: { enabled: true, formatter: (v) => kilo(Number(v)), offsetY: -20, style: { fontSize: '11px', colors: [TEXT] } },
          yaxis: { labels: { formatter: kilo } },
          tooltip: { y: { formatter: baht } },
        })}
      />
    </ChartCard>
  )
}

export function OilByMonthChart({ chart }: { chart: Charts['oil_by_month'] }) {
  const series = [
    { name: 'ปริมาณที่ใช้น้ำมัน (ลิตร)', type: 'column', data: chart.liters },
    { name: 'อัตราการใช้พลังงาน L/Km', type: 'line', data: chart.liter_per_km },
  ]
  return (
    <ChartCard
      title="ปริมาณที่ใช้น้ำมันเชื้อเพลิงรวม"
      unit="ลิตร"
      empty={chart.labels.length === 0}
      rows={seriesRows(chart.labels, series)}
    >
      <Chart
        type="line"
        height={280}
        series={series}
        options={comboOptions({
          labels: chart.labels,
          colors: [COLOR.oil, COLOR.line],
          leftTitle: 'ลิตร',
          rightTitle: 'L/Km',
          leftFormat: (v) => num(v, 0),
          rightFormat: (v) => num(v, 2),
        })}
      />
    </ChartCard>
  )
}

export function WorkByMonthChart({ chart }: { chart: Charts['work_by_month'] }) {
  const series = [
    { name: 'ชั่วโมงทำงาน', type: 'column', data: chart.hours },
    { name: '% อัตราการทำงานเฉลี่ย', type: 'line', data: chart.percent },
  ]
  return (
    <ChartCard
      title="มิเตอร์ทำงานรวม"
      unit="ชั่วโมง, กิโลเมตร"
      empty={chart.labels.length === 0}
      rows={seriesRows(chart.labels, series)}
    >
      <Chart
        type="line"
        height={280}
        series={series}
        options={comboOptions({
          labels: chart.labels,
          colors: [COLOR.work, COLOR.line],
          leftTitle: 'ชั่วโมง',
          rightTitle: '%',
          leftFormat: (v) => num(v, 0),
          rightFormat: (v) => `${num(v, 2)}%`,
        })}
      />
    </ChartCard>
  )
}

export function RepairVsWorkChart({ chart }: { chart: Charts['repair_vs_work'] }) {
  const series = [
    { name: 'ค่าใช้จ่ายซ่อมบำรุง', type: 'column', data: chart.repair },
    { name: 'ชั่วโมงการทำงาน', type: 'line', data: chart.work },
  ]
  return (
    <ChartCard
      title="ค่าใช้จ่ายรวมต่อชั่วโมงการทำงาน"
      unit="บาท/ชั่วโมง"
      empty={chart.labels.length === 0}
      rows={seriesRows(chart.labels, series)}
    >
      <Chart
        type="line"
        height={280}
        series={series}
        options={comboOptions({
          labels: chart.labels,
          colors: [COLOR.repair, COLOR.work],
          leftTitle: 'บาท',
          rightTitle: 'ชั่วโมง',
          leftFormat: kilo,
          rightFormat: (v) => `${num(v, 0)} ชม.`,
        })}
      />
    </ChartCard>
  )
}

export function RepairByCarChart({ chart }: { chart: Charts['repair_by_car'] }) {
  const name = 'ค่าใช้จ่ายซ่อมบำรุง'
  // รถเยอะ: ให้กราฟกว้างตามจำนวนคันแล้วเลื่อนแนวนอนได้ (เดิม: .chart-scroll)
  const minWidth = Math.max(chart.labels.length * 48, 600)
  return (
    <ChartCard
      title="ค่าใช้จ่ายซ่อมบำรุงรวมตามทะเบียนรถ"
      unit="บาท"
      empty={chart.series.length === 0}
      rows={seriesRows(chart.labels, [{ name, data: chart.series }])}
    >
      <div className="overflow-x-auto">
        <div style={{ minWidth }}>
          <Chart
            type="bar"
            height={350}
            series={[{ name, data: chart.series }]}
            options={baseOptions({
              colors: [COLOR.repair],
              xaxis: { categories: chart.labels, axisBorder: { show: false }, axisTicks: { show: false } },
              plotOptions: { bar: { borderRadius: 6, dataLabels: { position: 'top' } } },
              dataLabels: { enabled: true, formatter: (v) => kilo(Number(v)), offsetY: -20, style: { fontSize: '11px', colors: [TEXT] } },
              yaxis: { labels: { formatter: kilo } },
              tooltip: { y: { formatter: baht } },
            })}
          />
        </div>
      </div>
    </ChartCard>
  )
}

export function RepairByTypeChart({ chart }: { chart: Charts['repair_by_type'] }) {
  return <PieCard title="ค่าซ่อมตามประเภทการซ่อม" type="donut" chart={chart} />
}

export function RepairByCarTypeChart({ chart }: { chart: Charts['repair_by_car_type'] }) {
  return <PieCard title="ค่าใช้จ่ายแบ่งตามประเภทรถ" type="pie" chart={chart} />
}
