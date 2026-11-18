import { createContext, useContext } from 'react'

/** ตัวกรองที่ใช้อยู่ (บริษัท แผนก ประเภทรถ รถ) ใส่หัวไฟล์ Excel ทุกไฟล์ */
export const ExportFiltersContext = createContext<[string, string][]>([])

export function useExportFilters() {
  return useContext(ExportFiltersContext)
}
