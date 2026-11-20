/** ลิงก์ไปหน้าประวัติรถรายคัน (รถหนึ่งคันแยกตามบริษัท เหมือนตารางรถ) */
export function carHistoryPath(carId: number, branchCompanyId: string) {
  return `/car/${carId}?company=${encodeURIComponent(branchCompanyId)}`
}
