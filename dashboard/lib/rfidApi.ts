import { API_BASE_URL } from "./api";

export type AttendanceRecord = { date: string; entry_at: string; exit_at: string | null; status: string };
export type RfidEvent = { id: string; checkpoint_id: string | null; uid: string; employee_id: string | null; node_id: string; sequence: number; status: string; reason?: string | null; rssi: number | null; snr: number | null; timestamp: string; fingerprint_result: "MATCH" | "NO_MATCH" | "TIMEOUT" | null };
export type PresenceState = "PRESENT" | "CHECKED_OUT" | "YET_TO_ARRIVE" | "ABSENT";
export type OfficerPresence = { id: string; employee_id: string | null; name: string; role: string; rfid_uid: string | null; fingerprint_page_id: number | null; checkpoints: string[]; state?: PresenceState; present: boolean; attendance_date: string; absent_after?: string; timezone?: string; entry_at: string | null; exit_at: string | null };
export type VerificationStatus = "MATCH" | "MISMATCH" | "TIMEOUT";
export type VerificationEvent = {
  id: string; status: VerificationStatus; checkpoint_id: string | null;
  claimed_uid: string; claimed_employee_id: string | null; claimed_name: string | null;
  // null for a mismatch sourced from a signed patrol event: the signed wire payload is a
  // MATCH/NO_MATCH flag only, so which finger was actually presented and its score aren't
  // available (only the older, now-legacy two-factor flow captured that detail) -- see
  // backend/app/api/routes/rfid_attendance.py::list_verification_events.
  claimed_page_id: number | null; actual_page_id: number | null;
  actual_employee_id: string | null; actual_name: string | null;
  score: number | null; node_id: string; sequence: number; timestamp: string;
};

async function get<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, { cache: "no-store" });
  if (!response.ok) throw new Error("Unable to load data");
  return response.json() as Promise<T>;
}

export function fetchRfidEvents() { return get<RfidEvent[]>("/api/rfid-events"); }
export function fetchOfficerPresence() { return get<OfficerPresence[]>("/api/officer-presence"); }
export function fetchVerificationEvents(status?: VerificationStatus) {
  return get<VerificationEvent[]>(`/api/verification-events${status ? `?status=${status}` : ""}`);
}
