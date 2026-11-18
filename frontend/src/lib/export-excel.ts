/** ส่งออกข้อมูลกราฟเป็น .xlsx (แบบเดียวกับปุ่ม Excel ของหน้าเดิม) */

export type ExportTable = (string | number | null)[][]

export interface ExportInput {
  title: string
  unit?: string
  /** ตัวกรองที่ใช้อยู่ ใส่ไว้หัวไฟล์ให้รู้ว่าเป็นข้อมูลชุดไหน */
  filters: [string, string][]
  rows: ExportTable
}

const round2 = (v: number) => Math.round(v * 100) / 100

/** กราฟวงกลม: รายการ / มูลค่า / สัดส่วน */
export function pieRows(labels: string[], values: number[]): ExportTable {
  const total = values.reduce((a, b) => a + b, 0)
  return [
    ['รายการ', 'มูลค่า', 'สัดส่วน (%)'],
    ...labels.map((label, i) => [label, round2(values[i]), total ? round2((values[i] / total) * 100) : 0]),
    ['รวม', round2(total), total ? 100 : 0],
  ]
}

/** กราฟแท่ง/เส้น: 1 แถวต่อ 1 หมวด, 1 คอลัมน์ต่อ 1 ชุดข้อมูล */
export function seriesRows(
  labels: string[],
  series: { name: string; data: (number | null)[] }[],
): ExportTable {
  return [
    ['รายการ', ...series.map((s) => s.name)],
    ...labels.map((label, i) => [
      label,
      ...series.map((s) => (s.data[i] == null ? null : round2(s.data[i] as number))),
    ]),
  ]
}

export async function downloadExcel({ title, unit, filters, rows }: ExportInput) {
  const XLSX = await import('xlsx') // โหลดเมื่อกดปุ่มเท่านั้น

  const header: ExportTable = [[title], ...filters, ...(unit ? [['หน่วย', unit]] : []), []]
  const sheet = XLSX.utils.aoa_to_sheet([...header, ...rows])
  sheet['!cols'] = [{ wch: 32 }, ...rows[0].slice(1).map(() => ({ wch: 18 }))]

  const book = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(book, sheet, title.replace(/[\\/?*[\]:]/g, ' ').slice(0, 31))
  const today = new Date().toISOString().slice(0, 10)
  XLSX.writeFile(book, `${title} ${today}.xlsx`)
}
