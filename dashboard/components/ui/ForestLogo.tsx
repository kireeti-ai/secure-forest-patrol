// Secure Offline Patrol Verification mark: a three-tier conifer with a beacon signal arc (patrol + radio link).
// Stroke-only so it inherits `currentColor` and the stroke width set by the container.
export function ForestLogo({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3 7.5 9H10l-4.5 5.5H9.5L4 20h16l-5.5-5.5h4L14 9h2.5z" />
      <path d="M12 20v2" />
      <path d="M17.5 3.5a3.5 3.5 0 0 1 2 3" />
      <path d="M19 1.6a6 6 0 0 1 3.4 5.2" />
    </svg>
  );
}
