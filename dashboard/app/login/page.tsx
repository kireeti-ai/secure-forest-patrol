"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { login } from "../../lib/rfidApi";

export default function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError("");
    const data = new FormData(event.currentTarget);
    try {
      const user = await login(String(data.get("email")), String(data.get("password")));
      router.replace(user.role === "OFFICER" ? "/dashboard/rfid-events" : "/dashboard/my-attendance");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to sign in"); }
    finally { setBusy(false); }
  }
  return <main style={{ maxWidth: 420, margin: "10vh auto", padding: 28 }}>
    <h1>Secure Forest Patrol</h1><p>Sign in to the RFID attendance dashboard.</p>
    <form onSubmit={submit} style={{ display: "grid", gap: 14 }}>
      <label>Email<input required name="email" type="email" style={{ display: "block", width: "100%", padding: 10, marginTop: 4 }} /></label>
      <label>Password<input required name="password" type="password" minLength={12} style={{ display: "block", width: "100%", padding: 10, marginTop: 4 }} /></label>
      {error && <p role="alert" style={{ color: "#b91c1c" }}>{error}</p>}
      <button disabled={busy} type="submit">{busy ? "Signing in…" : "Sign in"}</button>
    </form>
  </main>;
}
