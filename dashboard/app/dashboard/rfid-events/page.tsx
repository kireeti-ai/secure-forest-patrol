"use client";

import { useEffect, useState } from "react";
import { fetchRfidEvents, type RfidEvent } from "../../../lib/rfidApi";

export default function RfidEventsPage() {
  const [events, setEvents] = useState<RfidEvent[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    const load = () => fetchRfidEvents().then((rows) => { setEvents(rows); setError(""); }).catch((e) => setError(e.message));
    load();
    const timer = setInterval(load, 5000);
    return () => clearInterval(timer);
  }, []);
  return <section><h2>Live RFID Events</h2><p>Automatically refreshed every 5 seconds.</p>{error && <p role="alert">{error}</p>}<table><thead><tr><th>Time</th><th>Node</th><th>Checkpoint</th><th>Employee</th><th>UID</th><th>Status</th><th>LoRa</th></tr></thead><tbody>{events.map(event => <tr key={event.id}><td>{new Date(event.timestamp).toLocaleString()}</td><td>{event.node_id}</td><td>{event.checkpoint_id ?? "—"}</td><td>{event.employee_id || "Unknown"}</td><td>{event.uid}</td><td>{event.status}</td><td>{event.rssi ?? "—"} dBm / {event.snr ?? "—"} dB</td></tr>)}</tbody></table></section>;
}
