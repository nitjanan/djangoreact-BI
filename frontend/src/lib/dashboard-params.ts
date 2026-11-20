import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router";

import type { DashboardQuery } from "@/api/hooks";
import type { Me } from "@/api/client";

const LAST_COMPANY_KEY = "fleet:last-company";

function readLastCompany() {
  try {
    return localStorage.getItem(LAST_COMPANY_KEY);
  } catch {
    return null;
  }
}

function saveLastCompany(code: string) {
  try {
    localStorage.setItem(LAST_COMPANY_KEY, code);
  } catch {
    // private mode ฯลฯ — ไม่จำก็ได้
  }
}

function toInt(value: string | null) {
  if (value === null || value === "") return undefined;
  const n = Number(value);
  return Number.isInteger(n) ? n : undefined;
}

/**
 * ตัวกรองของ dashboard เก็บใน URL
 * (?company=&year=&month_from=&month_to=&car_dep=&car_type=&car_id=&branch_company_id=)
 * แทน session ของหน้าเดิม — refresh/แชร์ลิงก์แล้วได้หน้าเดิม
 */
export function useDashboardParams(me: Me) {
  const [params, setParams] = useSearchParams();

  const companies = me.companies.map((c) => c.code);
  const fromUrl = params.get("company");
  const last = readLastCompany();
  const company =
    (fromUrl && companies.includes(fromUrl) && fromUrl) ||
    (last && companies.includes(last) && last) ||
    me.default_company ||
    null;

  const year = toInt(params.get("year"));
  const monthFrom = toInt(params.get("month_from"));
  const monthTo = toInt(params.get("month_to"));
  const carDep = toInt(params.get("car_dep")) ?? 1;
  const carType = toInt(params.get("car_type"));
  const carId = toInt(params.get("car_id"));
  const branchCompanyId = params.get("branch_company_id") || undefined;

  const query = useMemo<DashboardQuery | null>(
    () =>
      company
        ? {
            company,
            ...(year ? { year } : {}),
            month_from: monthFrom ?? null,
            month_to: monthTo ?? null,
            car_dep: carDep,
            car_type: carType ?? null,
            car_id: carId ?? null,
            branch_company_id: branchCompanyId ?? null,
          }
        : null,
    [
      company,
      year,
      monthFrom,
      monthTo,
      carDep,
      carType,
      carId,
      branchCompanyId,
    ],
  );

  const update = useCallback(
    (changes: Record<string, string | number | null | undefined>) => {
      setParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          for (const [key, value] of Object.entries(changes)) {
            if (value === null || value === undefined || value === "")
              next.delete(key);
            else next.set(key, String(value));
          }
          return next;
        },
        { replace: false },
      );
    },
    [setParams],
  );

  const clearCar = { car_id: null, branch_company_id: null };

  return {
    query,
    company,
    year: year ?? null,
    monthFrom: monthFrom ?? null,
    monthTo: monthTo ?? null,
    carDep,
    carType: carType ?? null,
    selectCompany: (code: string) => {
      saveLastCompany(code);
      // เปลี่ยนบริษัทแล้วล้างรถที่เลือกไว้ (เหมือนหน้าเดิม)
      update({ company: code, ...clearCar });
    },
    /** ช่วงเวลา: ปี + ช่วงเดือน (null = ทั้งปี) — คงรถที่เลือกไว้ เพื่อดูคันเดิมในช่วงอื่น */
    selectPeriod: (y: number, from: number | null, to: number | null) =>
      update({ year: y, month_from: from, month_to: to }),
    selectCarDep: (id: number) =>
      update({ car_dep: id, car_type: null, ...clearCar }),
    selectCarType: (id: number | null) => update({ car_type: id, ...clearCar }),
    selectCar: (carId: number, branchCompanyId: string) =>
      update({ car_id: carId, branch_company_id: branchCompanyId }),
    clearCar: () => update(clearCar),
    resetFilters: () => update({ car_type: null, ...clearCar }),
  };
}
