import { API_BASE_URL } from "./api";

export type AttendanceRecord = { date: string; entry_at: string; exit_at: string | null; status: string };
export type RfidEvent = { id: string; checkpoint_id: string | null; uid: string; employee_id: string | null; node_id: string; sequence: number; status: string; rssi: number | null; snr: number | null; timestamp: string };
export type OfficerPresence = { id: string; employee_id: string | null; name: string; role: string; rfid_uid: string | null; checkpoints: string[]; present: boolean; attendance_date: string; entry_at: string | null; exit_at: string | null };

async function get<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, { cache: "no-store" });
  if (!response.ok) throw new Error("Unable to load data");
  return response.json() as Promise<T>;
}

export function fetchRfidEvents() { return get<RfidEvent[]>("/api/rfid-events"); }
export function fetchOfficerPresence() { return get<OfficerPresence[]>("/api/officer-presence"); }
