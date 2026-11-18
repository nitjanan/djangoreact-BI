import Chart from 'react-apexcharts'

import type { Schemas } from '@/api/client'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { seriesRows } from '@/lib/export-excel'
import { num } from '@/lib/format'

import { ChartCard } from './ChartCard'
import { COLOR, baseOptions, comboOptions } from './chart-theme'
import { Kpi } from './Kpi'

export function Reliability({ data }: { data: Schemas['Reliability'] }) {
  const trendSeries = [
    { name: 'จำนวนครั้งที่เสีย', type: 'column', data: data.trend.count },
    { name: 'เวลาซ่อมเฉลี่ย (ชม.)', type: 'line', data: data.trend.mttr },
  ]
  const topName = 'จำนวนครั้งที่เสีย'

  return (
    <Card>
      <CardHeader>
        <CardTitle>ความถี่การเสียและเวลาซ่อม</CardTitle>
        <CardDescription>นับจากใบแจ้งซ่อมประเภท “ซ่อม”</CardDescription>
      </CardHeader>
      <CardContent className="grid grid-cols-1 gap-4">
        <div className="grid grid-cols-2 gap-px overflow-hidden rounded-xl border bg-border lg:grid-cols-4">
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
        </div>

        <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
          <ChartCard
            title="จำนวนครั้งที่เสียและเวลาซ่อมเฉลี่ยรายเดือน"
            unit="ครั้ง, ชั่วโมง"
            rows={seriesRows(data.trend.labels, trendSeries)}
            className="shadow-none"
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
                // None = เดือนที่ไม่มีใบปิดงาน แสดงเป็นช่องว่าง
                dataLabels: { enabled: true, enabledOnSeries: [0] },
              }}
            />
          </ChartCard>

          <ChartCard
            title="รถที่เสียบ่อยที่สุด 10 อันดับ"
            unit="ครั้ง"
            empty={data.top_cars.labels.length === 0}
            rows={seriesRows(data.top_cars.labels, [{ name: topName, data: data.top_cars.count }])}
            className="shadow-none"
          >
            <Chart
              type="bar"
              height={280}
              series={[{ name: topName, data: data.top_cars.count }]}
              options={baseOptions({
                colors: [COLOR.failure],
                plotOptions: { bar: { horizontal: true, borderRadius: 4, barHeight: '60%' } },
                xaxis: { categories: data.top_cars.labels, labels: { formatter: (v) => num(Number(v), 0) } },
                dataLabels: { enabled: true },
                tooltip: { y: { formatter: (v) => `${v} ครั้ง` } },
              })}
            />
          </ChartCard>
        </div>
      </CardContent>
    </Card>
  )
}
