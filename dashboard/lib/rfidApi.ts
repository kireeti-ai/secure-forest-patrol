import { API_BASE_URL } from "./api";

export type SessionUser = { id: string; email: string; role: "OFFICER" | "EMPLOYEE"; full_name: string };
export type AttendanceRecord = { date: string; entry_at: string; exit_at: string | null; status: string };
export type RfidEvent = { id: string; uid: string; employee_id: string | null; node_id: string; sequence: number; status: string; rssi: number | null; snr: number | null; timestamp: string };
export type OfficerPresence = { id: string; employee_id: string | null; name: string; role: string; rfid_uid: string | null; present: boolean; attendance_date: string; entry_at: string | null; exit_at: string | null };

const tokenKey = "sfp_access_token";
const userKey = "sfp_session_user";

export function session(): { token: string; user: SessionUser } | null {
  if (typeof window === "undefined") return null;
  const token = localStorage.getItem(tokenKey);
  const rawUser = localStorage.getItem(userKey);
  if (!token || !rawUser) return null;
  try { return { token, user: JSON.parse(rawUser) as SessionUser }; } catch { return null; }
}

export async function login(email: string, password: string): Promise<SessionUser> {
  const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, password }),
  });
  const body = await response.json();
  if (!response.ok) throw new Error(body.detail || "Invalid email or password");
  if (body.user.role !== "OFFICER" && body.user.role !== "EMPLOYEE") throw new Error("This account does not have an RFID dashboard role");
  localStorage.setItem(tokenKey, body.access_token);
  localStorage.setItem(userKey, JSON.stringify(body.user));
  return body.user;
}

export function logout() { localStorage.removeItem(tokenKey); localStorage.removeItem(userKey); }

async function authorized<T>(path: string): Promise<T> {
  const current = session();
  if (!current) throw new Error("Please sign in");
  const response = await fetch(`${API_BASE_URL}${path}`, { cache: "no-store", headers: { Authorization: `Bearer ${current.token}` } });
  if (!response.ok) throw new Error(response.status === 403 ? "You are not allowed to view this data" : "Unable to load data");
  return response.json() as Promise<T>;
}

export function fetchMyAttendance() { return authorized<{ employee: { employee_id: string; name: string; rfid_uid: string | null }; records: AttendanceRecord[] }>("/api/my-attendance"); }
export function fetchRfidEvents() { return authorized<RfidEvent[]>("/api/rfid-events"); }
export function fetchOfficerPresence() { return authorized<OfficerPresence[]>("/api/officer-presence"); }
