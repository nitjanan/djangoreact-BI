import Chart from 'react-apexcharts'

import type { Schemas } from '@/api/client'
import { seriesRows } from '@/lib/export-excel'
import { num } from '@/lib/format'

import { ChartCard } from './ChartCard'
import { CHART_HELP } from './chart-help'
import { COLOR, TEXT, baseOptions, carLabel, comboOptions } from './chart-theme'
import { Kpi, KpiStrip } from './Kpi'

export function Reliability({ data }: { data: Schemas['Reliability'] }) {
  const trendSeries = [
    { name: 'จำนวนครั้งที่เสีย', type: 'column', data: data.trend.count },
    { name: 'เวลาซ่อมเฉลี่ย (ชม.)', type: 'line', data: data.trend.mttr },
  ]
  const topName = 'จำนวนครั้งที่เสีย'
  const topLabels = data.top_cars.labels.map((l, i) => carLabel(l, data.top_cars.companies[i]))

  return (
    <div className="grid grid-cols-1 gap-4">
      <KpiStrip className="sm:grid-cols-2 xl:grid-cols-4">
        <Kpi label="จำนวนครั้งที่เสีย" value={num(data.failure_count, 0)} unit="ครั้ง" />
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
      </KpiStrip>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <ChartCard
          title="จำนวนครั้งที่เสียและเวลาซ่อมเฉลี่ยรายเดือน"
          help={CHART_HELP.failureTrend}
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
          title="รถที่เสียบ่อยที่สุด 10 อันดับ"
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
      </div>
    </div>
  )
}
