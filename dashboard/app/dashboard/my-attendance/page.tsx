"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { fetchMyAttendance, logout, session, type AttendanceRecord } from "../../../lib/rfidApi";

export default function MyAttendancePage() {
  const router = useRouter(); const [records, setRecords] = useState<AttendanceRecord[]>([]); const [profile, setProfile] = useState<{ name: string; employee_id: string; rfid_uid: string | null } | null>(null); const [error, setError] = useState("");
  useEffect(() => { const current = session(); if (!current || current.user.role !== "EMPLOYEE") { router.replace("/login"); return; } fetchMyAttendance().then(data => { setProfile(data.employee); setRecords(data.records); }).catch(e => setError(e.message)); }, [router]);
  const today = records[0];
  return <section><h2>My RFID Attendance</h2>{error && <p role="alert">{error}</p>}{profile && <><p><strong>{profile.name}</strong> · {profile.employee_id} · RFID {profile.rfid_uid || "Not assigned"}</p><p>Today: {today ? `${new Date(today.entry_at).toLocaleTimeString()} entry${today.exit_at ? ` · ${new Date(today.exit_at).toLocaleTimeString()} exit` : " · exit pending"}` : "No scan recorded"}</p><table><thead><tr><th>Date</th><th>Entry</th><th>Exit</th><th>Status</th></tr></thead><tbody>{records.map(row => <tr key={row.date}><td>{row.date}</td><td>{new Date(row.entry_at).toLocaleTimeString()}</td><td>{row.exit_at ? new Date(row.exit_at).toLocaleTimeString() : "—"}</td><td>{row.status}</td></tr>)}</tbody></table></>}<button onClick={() => { logout(); router.replace("/login"); }}>Sign out</button></section>;
}
