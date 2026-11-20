import Chart from 'react-apexcharts'

import type { Schemas } from '@/api/client'
import { seriesRows } from '@/lib/export-excel'
import { num } from '@/lib/format'

import { ChartCard } from './ChartCard'
import { useChartHelp } from './chart-help'
import { useNoun } from './export-context'
import { COLOR, PALETTE, TEXT, baseOptions, carLabel, comboOptions } from './chart-theme'
import { Kpi, KpiStrip } from './Kpi'

const PM_COLOR = PALETTE[7] // เขียว: งานเชิงรุก
const DOWNTIME_COLOR = PALETTE[5] // แดงเข้ม: เวลาที่รถหยุด

export function Reliability({ data }: { data: Schemas['Reliability'] }) {
  const CHART_HELP = useChartHelp()
  const noun = useNoun()
  const trendSeries = [
    { name: 'จำนวนครั้งที่เสีย', type: 'column', data: data.trend.count },
    { name: 'เวลาซ่อมเฉลี่ย (ชม.)', type: 'line', data: data.trend.mttr },
  ]
  // รถที่ไม่มีใบแจ้งซ่อม นับครั้งที่ซ่อมจากใบจ่ายอะไหล่ (Express) แทน
  const docNote =
    data.doc_failure_count > 0
      ? `รวม ${num(data.doc_failure_count, 0)} ครั้งที่นับจากใบจ่ายอะไหล่ (${noun}ที่ไม่มีใบแจ้งซ่อม)`
      : undefined
  const topName = 'จำนวนครั้งที่เสีย'
  const topLabels = data.top_cars.labels.map((l, i) => carLabel(l, data.top_cars.companies[i]))

  const mixSeries = [
    { name: 'PM (บำรุงรักษาตามรอบ)', data: data.trend.pm },
    { name: 'ซ่อมเมื่อเสีย', data: data.trend.count },
  ]
  const downtimeSeries = [{ name: 'ชั่วโมงหยุดซ่อม', data: data.trend.downtime }]
  const downtimeLabels = data.top_downtime.labels.map((l, i) =>
    carLabel(l, data.top_downtime.companies[i]),
  )
  const topDowntimeSeries = [{ name: 'ชั่วโมงหยุดซ่อม', data: data.top_downtime.hours }]

  return (
    <div className="grid grid-cols-1 gap-4">
      <KpiStrip className="sm:grid-cols-3 xl:grid-cols-6">
        <Kpi label="จำนวนครั้งที่เสีย" value={num(data.failure_count, 0)} unit="ครั้ง" note={docNote} />
        <Kpi label="MTBF ระยะเวลาเฉลี่ยระหว่างการเสีย" value={num(data.mtbf, 1)} unit="ชม." />
        <Kpi
          label="MTTR เวลาซ่อมเฉลี่ย"
          value={num(data.mttr, 1)}
          unit="ชม."
          note={`จากใบที่ปิดงานแล้ว ${data.repair_closed} ใบ`}
        />
        <Kpi
          label="ความพร้อมใช้งาน (Availability)"
          value={num(data.availability, 1)}
          unit="%"
          meter={data.availability}
        />
        <Kpi
          label="Downtime ชั่วโมงหยุดซ่อมรวม"
          value={num(data.downtime_hours, 0)}
          unit="ชม."
          note={`≈ ${num(data.downtime_hours / 24, 0)} วัน · จากใบที่ปิดงานแล้ว`}
        />
        <Kpi
          label="สัดส่วน PM"
          value={num(data.pm_ratio, 0)}
          unit="%"
          meter={data.pm_ratio}
          note={
            `PM ${num(data.pm_count, 0)} · ซ่อม ${num(data.failure_count, 0)} ครั้ง` +
            (data.doc_pm_count > 0 ? ` (PM จากใบจ่ายอะไหล่ ${num(data.doc_pm_count, 0)})` : '')
          }
        />
      </KpiStrip>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <ChartCard
          title="จำนวนครั้งที่เสียและเวลาซ่อมเฉลี่ยรายเดือน"
          help={CHART_HELP.failureTrend}
          description={docNote && `${docNote} · ไม่มีเวลาปิดงาน จึงไม่นับในเวลาซ่อมเฉลี่ย`}
          unit="ครั้ง, ชั่วโมง"
          empty={data.failure_count === 0}
          rows={seriesRows(data.trend.labels, trendSeries)}
        >
          <Chart
            type="line"
            height={280}
            series={trendSeries}
            options={{
              ...comboOptions({
                labels: data.trend.labels,
                colors: [COLOR.failure, COLOR.repair],
                leftTitle: 'ครั้ง',
                rightTitle: 'ชั่วโมง',
                leftFormat: (v) => num(v, 0),
                rightFormat: (v) => num(v, 1),
              }),
              // เดือนที่ไม่มีใบปิดงาน (null) แสดงเป็นช่องว่าง
              dataLabels: {
                enabled: true,
                enabledOnSeries: [0],
                background: { enabled: false },
                style: { fontSize: '11px', colors: [TEXT] },
              },
            }}
          />
        </ChartCard>

        <ChartCard
          title={`${noun}ที่เสียบ่อยที่สุด 10 อันดับ`}
          help={CHART_HELP.topFailures}
          unit="ครั้ง"
          empty={data.top_cars.labels.length === 0}
          rows={seriesRows(topLabels, [{ name: topName, data: data.top_cars.count }])}
        >
          <Chart
            type="bar"
            height={280}
            series={[{ name: topName, data: data.top_cars.count }]}
            options={baseOptions({
              colors: [COLOR.failure],
              plotOptions: { bar: { horizontal: true, borderRadius: 4, barHeight: '60%' } },
              xaxis: {
                categories: topLabels,
                labels: { formatter: (v) => num(Number(v), 0) },
              },
              // ตัวเลขสีเข้มบนแท่งปะการัง (ขาวบนปะการังอ่านยาก)
              dataLabels: { enabled: true, style: { colors: [TEXT] } },
              tooltip: { y: { formatter: (v) => `${v} ครั้ง` } },
            })}
          />
        </ChartCard>

        <ChartCard
          title="PM เทียบกับการซ่อมเมื่อเสีย รายเดือน"
          description={
            'PM น้อยแต่ซ่อมเมื่อเสียมาก = งานบำรุงรักษาเชิงรุกยังไม่พอ · นับจากใบแจ้งซ่อม' +
            (data.doc_failure_count + data.doc_pm_count > 0
              ? ` และใบจ่ายอะไหล่ของ${noun}ที่ไม่มีใบแจ้งซ่อม (ประเภทการซ่อม "PM" = PM)`
              : '')
          }
          unit="ใบ"
          empty={data.pm_count === 0 && data.failure_count === 0}
          rows={seriesRows(data.trend.labels, mixSeries)}
        >
          <Chart
            type="bar"
            height={280}
            series={mixSeries}
            options={baseOptions({
              colors: [PM_COLOR, COLOR.failure],
              chart: { stacked: true },
              plotOptions: { bar: { borderRadius: 3, columnWidth: '55%' } },
              xaxis: { categories: data.trend.labels },
              yaxis: { labels: { formatter: (v) => num(v, 0) } },
              dataLabels: { enabled: false },
              legend: { position: 'top', horizontalAlign: 'left' },
              tooltip: { y: { formatter: (v) => `${v} ใบ` } },
            })}
          />
        </ChartCard>

        <ChartCard
          title="Downtime ชั่วโมงหยุดซ่อมรายเดือน"
          description="รวมเวลาตั้งแต่แจ้งซ่อมจนหัวหน้าช่างปิดงาน ของใบซ่อมที่ปิดงานแล้ว (นับตามเดือนที่แจ้งซ่อม)"
          unit="ชั่วโมง"
          empty={data.downtime_hours === 0}
          rows={seriesRows(data.trend.labels, downtimeSeries)}
        >
          <Chart
            type="bar"
            height={280}
            series={downtimeSeries}
            options={baseOptions({
              colors: [DOWNTIME_COLOR],
              plotOptions: { bar: { borderRadius: 3, columnWidth: '55%' } },
              xaxis: { categories: data.trend.labels },
              yaxis: { labels: { formatter: (v) => num(v, 0) } },
              dataLabels: { enabled: false },
              tooltip: {
                y: { formatter: (v) => `${num(v, 0)} ชม. (≈ ${num(Number(v) / 24, 1)} วัน)` },
              },
            })}
          />
        </ChartCard>
      </div>

      <ChartCard
        title={`${noun}ที่หยุดซ่อมนานที่สุด 10 อันดับ`}
        description="ชั่วโมงหยุดซ่อมรวมของแต่ละคันในช่วงที่เลือก (ใบซ่อมที่ปิดงานแล้ว)"
        unit="ชั่วโมง"
        empty={data.top_downtime.labels.length === 0}
        rows={seriesRows(downtimeLabels, topDowntimeSeries)}
      >
        <Chart
          type="bar"
          height={300}
          series={topDowntimeSeries}
          options={baseOptions({
            colors: [DOWNTIME_COLOR],
            plotOptions: { bar: { horizontal: true, borderRadius: 4, barHeight: '60%' } },
            xaxis: {
              categories: downtimeLabels,
              labels: { formatter: (v) => num(Number(v), 0) },
            },
            dataLabels: { enabled: true, formatter: (v) => num(Number(v), 0) },
            tooltip: {
              y: { formatter: (v) => `${num(v, 0)} ชม. (≈ ${num(Number(v) / 24, 1)} วัน)` },
            },
          })}
        />
      </ChartCard>
    </div>
  )
}
