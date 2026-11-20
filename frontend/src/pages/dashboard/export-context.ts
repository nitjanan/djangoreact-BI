import { createContext, useContext } from 'react'

/** ตัวกรองที่ใช้อยู่ (บริษัท แผนก ประเภทรถ รถ) ใส่หัวไฟล์ Excel ทุกไฟล์ */
export const ExportFiltersContext = createContext<[string, string][]>([])

export function useExportFilters() {
  return useContext(ExportFiltersContext)
}

/** คำเรียกรถ = ชื่อแผนกที่เลือก (ยานพาหนะ, เครื่องจักรกลหนัก, ...) ใช้แทนคำว่า "รถ" ในข้อความ */
export const NounContext = createContext('รถ')

export function useNoun() {
  return useContext(NounContext)
}

/** อัตราการใช้น้ำมันของแผนกที่เลือก: เครื่องจักร = ลิตร/ชม., รถบรรทุก = ลิตร/กม. (backend เลือกให้) */
export type Fuel = { field: 'fuel_rate' | 'liter_per_km'; unit: string }

export const FuelContext = createContext<Fuel>({ field: 'fuel_rate', unit: 'ลิตร/ชม.' })

export function useFuel() {
  return useContext(FuelContext)
}
