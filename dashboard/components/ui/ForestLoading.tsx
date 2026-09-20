import { ForestLogo } from "./ForestLogo";

export function ForestLoading({ label = "Loading Secure Offline Patrol Verification" }: { label?: string }) {
  return (
    <main className="forest-loading" aria-label={label} role="status">
      <div className="forest-loading-mark" aria-hidden="true">
        <ForestLogo />
      </div>
      <p className="forest-loading-name">Secure Offline Patrol Verification</p>
      <p className="forest-loading-label">{label}</p>
    </main>
  );
}
