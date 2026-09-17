import { ForestLogo } from "./ForestLogo";

export function ForestLoading({ label = "Loading Forest Patrol" }: { label?: string }) {
  return (
    <main className="forest-loading" aria-label={label} role="status">
      <div className="forest-loading-mark" aria-hidden="true">
        <ForestLogo />
      </div>
      <p className="forest-loading-name">FOREST PATROL</p>
      <p className="forest-loading-label">{label}</p>
    </main>
  );
}
