"use client";

import { useMemo, useState } from "react";
import type { AcousticEvent } from "../../lib/api";

// Categorical hues for the two classes (validated for colour-blind separation on the light surface).
const CLASS_COLOR = { Gunshot: "#2563a8", Chainsaw: "#c2762b" } as const;
const CLASSES = ["Gunshot", "Chainsaw"] as const;
type ClassName = (typeof CLASSES)[number];
type Range = "24h" | "7d" | "all";

const RANGES: { key: Range; label: string }[] = [
  { key: "24h", label: "Last 24 hours" },
  { key: "7d", label: "Last 7 days" },
  { key: "all", label: "All" },
];

const HOUR = 3600_000;
const DAY = 24 * HOUR;

type Bucket = { start: number; label: string; counts: Record<ClassName, number>; total: number };
type Tip = { x: number; y: number; title: string; lines: string[] } | null;

const pct = (n: number) => `${Math.round(n * 100)}%`;
const isClass = (c: string): c is ClassName => c === "Gunshot" || c === "Chainsaw";

function floorTo(ms: number, dayAligned: boolean): number {
  const d = new Date(ms);
  if (dayAligned) d.setHours(0, 0, 0, 0);
  else d.setMinutes(0, 0, 0);
  return d.getTime();
}

function buildBuckets(events: AcousticEvent[], range: Range, now: number): { buckets: Bucket[]; unit: number } {
  const times = events.map((e) => Date.parse(e.timestamp)).filter(Number.isFinite);
  let unit = HOUR;
  let count = 24;
  if (range === "7d") { unit = DAY; count = 7; }
  else if (range === "all") {
    const span = times.length ? now - Math.min(...times) : 0;
    if (span <= 48 * HOUR) { unit = HOUR; count = Math.max(6, Math.min(48, Math.ceil(span / HOUR) + 1)); }
    else { unit = DAY; count = Math.min(60, Math.ceil(span / DAY) + 1); }
  }
  const dayAligned = unit === DAY;
  const last = floorTo(now, dayAligned);
  const buckets: Bucket[] = [];
  for (let i = count - 1; i >= 0; i--) {
    const start = last - i * unit;
    const d = new Date(start);
    const label = dayAligned
      ? d.toLocaleDateString([], { day: "2-digit", month: "short" })
      : `${String(d.getHours()).padStart(2, "0")}:00`;
    buckets.push({ start, label, counts: { Gunshot: 0, Chainsaw: 0 }, total: 0 });
  }
  for (const e of events) {
    const t = Date.parse(e.timestamp);
    if (!Number.isFinite(t) || !isClass(e.classification)) continue;
    const idx = buckets.findIndex((b) => t >= b.start && t < b.start + unit);
    if (idx >= 0) { buckets[idx].counts[e.classification]++; buckets[idx].total++; }
  }
  return { buckets, unit };
}

function niceStep(max: number): number {
  if (max <= 5) return 1;
  const raw = max / 5;
  const pow = Math.pow(10, Math.floor(Math.log10(raw)));
  const f = raw / pow;
  return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10) * pow;
}

// Bar with a rounded data end (top) and a square baseline end.
function topRounded(x: number, y: number, w: number, h: number, r: number): string {
  const rr = Math.max(0, Math.min(r, h, w / 2));
  return `M${x} ${y + h}V${y + rr}Q${x} ${y} ${x + rr} ${y}H${x + w - rr}Q${x + w} ${y} ${x + w} ${y + rr}V${y + h}Z`;
}

function useTip() {
  const [tip, setTip] = useState<Tip>(null);
  const show = (e: React.MouseEvent | React.FocusEvent, title: string, lines: string[]) => {
    const host = (e.currentTarget as Element).closest(".an-chart") as HTMLElement | null;
    if (!host) return;
    const box = host.getBoundingClientRect();
    const el = e.currentTarget as Element;
    const r = el.getBoundingClientRect();
    const cx = "clientX" in e ? (e as React.MouseEvent).clientX : r.left + r.width / 2;
    const cy = "clientY" in e ? (e as React.MouseEvent).clientY : r.top;
    setTip({ x: cx - box.left, y: cy - box.top, title, lines });
  };
  return { tip, show, hide: () => setTip(null) };
}

function Tooltip({ tip }: { tip: Tip }) {
  if (!tip) return null;
  return (
    <div className="an-tip" style={{ left: tip.x, top: tip.y }} role="tooltip">
      <div className="an-tip-title">{tip.title}</div>
      {tip.lines.map((l) => <div key={l}>{l}</div>)}
    </div>
  );
}

function TimeChart({ buckets, unit }: { buckets: Bucket[]; unit: number }) {
  const { tip, show, hide } = useTip();
  const W = 720, H = 236, L = 34, R = 8, T = 10, B = 28;
  const plotW = W - L - R, plotH = H - T - B;
  const max = Math.max(1, ...buckets.map((b) => b.total));
  const step = niceStep(max);
  const top = Math.ceil(max / step) * step;
  const unitH = plotH / top;
  const slot = plotW / buckets.length;
  const barW = Math.min(24, slot * 0.7);
  const ticks: number[] = [];
  for (let v = 0; v <= top; v += step) ticks.push(v);
  const labelEvery = Math.max(1, Math.ceil(buckets.length / 8));
  const GAP = 2;

  return (
    <div className="an-chart">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Detections over time, stacked by class" className="an-svg">
        {ticks.map((v) => {
          const y = T + plotH - v * unitH;
          return (
            <g key={v}>
              <line x1={L} x2={W - R} y1={y} y2={y} className="an-grid" />
              <text x={L - 6} y={y + 4} textAnchor="end" className="an-axis">{v}</text>
            </g>
          );
        })}
        {buckets.map((b, i) => {
          const cx = L + slot * i + slot / 2;
          const x = cx - barW / 2;
          let base = T + plotH;
          const segs: React.ReactNode[] = [];
          const present = CLASSES.filter((c) => b.counts[c] > 0);
          present.forEach((c, k) => {
            const h = b.counts[c] * unitH - (k < present.length - 1 ? GAP : 0);
            const isTop = k === present.length - 1;
            const y = base - h;
            segs.push(isTop
              ? <path key={c} d={topRounded(x, y, barW, h, 4)} fill={CLASS_COLOR[c]} />
              : <rect key={c} x={x} y={y} width={barW} height={h} fill={CLASS_COLOR[c]} />);
            base = y - GAP;
          });
          const when = unit === DAY ? b.label : `${b.label} on ${new Date(b.start).toLocaleDateString([], { day: "2-digit", month: "short" })}`;
          return (
            <g key={b.start}>
              {segs}
              {i % labelEvery === 0 && <text x={cx} y={H - 8} textAnchor="middle" className="an-axis">{b.label}</text>}
              {b.total > 0 && (
                <text x={cx} y={T + plotH - b.total * unitH - 6} textAnchor="middle" className="an-value">{b.total}</text>
              )}
              <rect x={L + slot * i} y={T} width={slot} height={plotH} fill="transparent" tabIndex={0}
                aria-label={`${when}: ${b.total} detections`}
                onMouseMove={(e) => show(e, when, [`Gunshot ${b.counts.Gunshot}`, `Chainsaw ${b.counts.Chainsaw}`, `Total ${b.total}`])}
                onFocus={(e) => show(e, when, [`Gunshot ${b.counts.Gunshot}`, `Chainsaw ${b.counts.Chainsaw}`, `Total ${b.total}`])}
                onMouseLeave={hide} onBlur={hide} />
            </g>
          );
        })}
      </svg>
      <Tooltip tip={tip} />
    </div>
  );
}

function OutcomeBars({ rows }: { rows: { label: string; value: number; color: string; note: string }[] }) {
  const { tip, show, hide } = useTip();
  const max = Math.max(1, ...rows.map((r) => r.value));
  return (
    <div className="an-chart">
      <ul className="an-hbars" role="list">
        {rows.map((r) => (
          <li key={r.label} onMouseMove={(e) => show(e, r.label, [`${r.value} detections`, r.note])} onMouseLeave={hide}>
            <span className="an-hbar-label">{r.label}</span>
            <span className="an-hbar-track">
              <span className="an-hbar-fill" style={{ width: `${(r.value / max) * 100}%`, background: r.color }} />
            </span>
            <span className="an-hbar-value">{r.value}</span>
          </li>
        ))}
      </ul>
      <Tooltip tip={tip} />
    </div>
  );
}

const BINS = [
  { label: "<50%", lo: 0, hi: 0.5 }, { label: "50s", lo: 0.5, hi: 0.6 }, { label: "60s", lo: 0.6, hi: 0.7 },
  { label: "70s", lo: 0.7, hi: 0.8 }, { label: "80s", lo: 0.8, hi: 0.9 }, { label: "90%+", lo: 0.9, hi: 1.01 },
];

function ConfidenceChart({ events }: { events: AcousticEvent[] }) {
  const { tip, show, hide } = useTip();
  const bins = BINS.map((b) => {
    const inBin = events.filter((e) => e.confidence >= b.lo && e.confidence < b.hi);
    const dismissed = inBin.filter((e) => e.reviewStatus === "DISMISSED").length;
    const confirmed = inBin.filter((e) => e.reviewStatus === "CONFIRMED").length;
    return { ...b, n: inBin.length, dismissed, confirmed };
  });
  const W = 360, H = 200, L = 30, R = 8, T = 16, B = 26;
  const plotW = W - L - R, plotH = H - T - B;
  const max = Math.max(1, ...bins.map((b) => b.n));
  const step = niceStep(max);
  const topV = Math.ceil(max / step) * step;
  const unitH = plotH / topV;
  const slot = plotW / bins.length, barW = Math.min(24, slot * 0.6);
  const ticks: number[] = [];
  for (let v = 0; v <= topV; v += step) ticks.push(v);
  return (
    <div className="an-chart">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Detections by model confidence" className="an-svg">
        {ticks.map((v) => {
          const y = T + plotH - v * unitH;
          return <g key={v}><line x1={L} x2={W - R} y1={y} y2={y} className="an-grid" /><text x={L - 6} y={y + 4} textAnchor="end" className="an-axis">{v}</text></g>;
        })}
        {bins.map((b, i) => {
          const cx = L + slot * i + slot / 2, h = b.n * unitH, y = T + plotH - h;
          const decided = b.dismissed + b.confirmed;
          const lines = [`${b.n} detections`, decided ? `${b.dismissed} of ${decided} reviewed were false alarms` : "none reviewed yet"];
          return (
            <g key={b.label}>
              {b.n > 0 && <path d={topRounded(cx - barW / 2, y, barW, h, 4)} fill="var(--color-forest-dark)" />}
              {b.n > 0 && <text x={cx} y={y - 5} textAnchor="middle" className="an-value">{b.n}</text>}
              <text x={cx} y={H - 8} textAnchor="middle" className="an-axis">{b.label}</text>
              <rect x={L + slot * i} y={T} width={slot} height={plotH} fill="transparent" tabIndex={0}
                aria-label={`Confidence ${b.label}: ${b.n} detections`}
                onMouseMove={(e) => show(e, `Confidence ${b.label}`, lines)} onFocus={(e) => show(e, `Confidence ${b.label}`, lines)}
                onMouseLeave={hide} onBlur={hide} />
            </g>
          );
        })}
      </svg>
      <Tooltip tip={tip} />
    </div>
  );
}

export function AcousticAnalytics({ events }: { events: AcousticEvent[] }) {
  const [range, setRange] = useState<Range>("all");
  const now = Date.now();
  const scoped = useMemo(() => {
    if (range === "all") return events;
    const from = now - (range === "24h" ? DAY : 7 * DAY);
    return events.filter((e) => Date.parse(e.timestamp) >= from);
    // `now` moves every render; the range boundary only needs to be right when data or range change
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [events, range]);

  const { buckets, unit } = useMemo(() => buildBuckets(scoped, range, now),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [scoped, range]);

  const stats = useMemo(() => {
    const by = (s: string) => scoped.filter((e) => e.reviewStatus === s).length;
    const confirmed = by("CONFIRMED"), dismissed = by("DISMISSED");
    const decided = confirmed + dismissed;
    const perClass = CLASSES.map((c) => {
      const rows = scoped.filter((e) => e.classification === c);
      const cc = rows.filter((e) => e.reviewStatus === "CONFIRMED").length;
      const dd = rows.filter((e) => e.reviewStatus === "DISMISSED").length;
      return {
        c, n: rows.length,
        avg: rows.length ? rows.reduce((a, e) => a + e.confidence, 0) / rows.length : 0,
        confirmed: cc, dismissed: dd, pending: rows.filter((e) => e.reviewStatus === "PENDING_REVIEW").length,
        falseRate: cc + dd ? dd / (cc + dd) : null,
      };
    });
    const latest = scoped.reduce<string | null>((a, e) => (!a || e.timestamp > a ? e.timestamp : a), null);
    return {
      total: scoped.length, pending: by("PENDING_REVIEW"), confirmed, dismissed, reviewedOnly: by("REVIEWED"), decided,
      falseRate: decided ? dismissed / decided : null, perClass, latest,
    };
  }, [scoped]);

  const byNode = useMemo(() => {
    const m = new Map<string, { node: string; cp: string; n: number; last: string }>();
    for (const e of scoped) {
      const k = e.nodeId;
      const cur = m.get(k) ?? { node: e.nodeId, cp: e.checkpointId || "—", n: 0, last: e.timestamp };
      cur.n++;
      if (e.timestamp > cur.last) cur.last = e.timestamp;
      m.set(k, cur);
    }
    return [...m.values()].sort((a, b) => b.n - a.n);
  }, [scoped]);

  const outcomeRows = [
    { label: "Awaiting review", value: stats.pending, color: "var(--color-warning)", note: "Not looked at yet" },
    { label: "Confirmed threat", value: stats.confirmed, color: "var(--color-danger)", note: "A person confirmed it was real" },
    { label: "False alarm", value: stats.dismissed, color: "var(--color-faint)", note: "A person dismissed it" },
    { label: "Reviewed, unclear", value: stats.reviewedOnly, color: "var(--color-healthy)", note: "Looked at, no decision" },
  ];

  return (
    <section className="an" aria-label="Acoustic analytics">
      <div className="an-head">
        <h2>Analytics</h2>
        <div className="scan-tabs" role="group" aria-label="Time range">
          {RANGES.map((r) => (
            <button key={r.key} type="button" className="scan-tab" aria-pressed={range === r.key} onClick={() => setRange(r.key)}>{r.label}</button>
          ))}
        </div>
      </div>

      {stats.total === 0 ? (
        <p className="an-empty">No detections in this range.</p>
      ) : (
        <>
          <div className="stat-grid">
            <div className="ui-card stat"><p className="stat-label">Detections</p><p className="stat-value">{stats.total}</p></div>
            <div className="ui-card stat"><p className="stat-label">Awaiting review</p><p className="stat-value" style={{ color: stats.pending ? "var(--color-warning)" : undefined }}>{stats.pending}</p></div>
            <div className="ui-card stat"><p className="stat-label">Confirmed threats</p><p className="stat-value" style={{ color: stats.confirmed ? "var(--color-danger)" : undefined }}>{stats.confirmed}</p></div>
            <div className="ui-card stat">
              <p className="stat-label">False-alarm rate</p>
              <p className="stat-value">{stats.falseRate === null ? "—" : pct(stats.falseRate)}</p>
              <p className="an-sub">{stats.decided ? `${stats.dismissed} of ${stats.decided} decided` : "Nothing decided yet"}</p>
            </div>
          </div>

          <div className="an-grid2">
            <div className="ui-card an-card">
              <div className="an-card-head">
                <h3>Detections over time</h3>
                <ul className="an-legend" role="list">
                  {CLASSES.map((c) => (
                    <li key={c}><span className="an-swatch" style={{ background: CLASS_COLOR[c] }} />{c} {stats.perClass.find((p) => p.c === c)?.n ?? 0}</li>
                  ))}
                </ul>
              </div>
              <TimeChart buckets={buckets} unit={unit} />
              <details className="an-table-view">
                <summary>View as table</summary>
                <table className="an-table">
                  <thead><tr><th>{unit === DAY ? "Day" : "Hour"}</th><th className="num">Gunshot</th><th className="num">Chainsaw</th><th className="num">Total</th></tr></thead>
                  <tbody>
                    {buckets.filter((b) => b.total > 0).map((b) => (
                      <tr key={b.start}>
                        <td>{unit === DAY ? b.label : `${b.label}, ${new Date(b.start).toLocaleDateString([], { day: "2-digit", month: "short" })}`}</td>
                        <td className="num">{b.counts.Gunshot}</td><td className="num">{b.counts.Chainsaw}</td><td className="num">{b.total}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </details>
            </div>

            <div className="ui-card an-card">
              <h3>Review outcomes</h3>
              <OutcomeBars rows={outcomeRows} />
              <p className="an-sub">
                {stats.decided
                  ? `${stats.dismissed} of ${stats.decided} decided detections were false alarms.`
                  : "Open a detection and confirm it or mark it a false alarm to build this picture."}
              </p>
            </div>
          </div>

          <div className="an-grid2 an-grid2-b">
            <div className="ui-card an-card">
              <h3>Model confidence</h3>
              <ConfidenceChart events={scoped} />
              <p className="an-sub">Confidence is the model&apos;s own probability, not a measured accuracy.</p>
            </div>

            <div className="ui-card an-card">
              <h3>By class</h3>
              <table className="an-table">
                <thead><tr><th>Class</th><th className="num">Detections</th><th className="num">Avg conf.</th><th className="num">Confirmed</th><th className="num">False alarm</th><th className="num">Pending</th></tr></thead>
                <tbody>
                  {stats.perClass.map((p) => (
                    <tr key={p.c}>
                      <td><span className="an-swatch" style={{ background: CLASS_COLOR[p.c] }} />{p.c}</td>
                      <td className="num">{p.n}</td><td className="num">{p.n ? pct(p.avg) : "—"}</td>
                      <td className="num">{p.confirmed}</td>
                      <td className="num">{p.dismissed}{p.falseRate !== null ? ` (${pct(p.falseRate)})` : ""}</td>
                      <td className="num">{p.pending}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <h3 className="an-h3-gap">By node</h3>
              <table className="an-table">
                <thead><tr><th>Node</th><th>Checkpoint</th><th className="num">Detections</th><th>Latest</th></tr></thead>
                <tbody>
                  {byNode.map((n) => (
                    <tr key={n.node}>
                      <td className="mono">{n.node}</td><td>{n.cp}</td><td className="num">{n.n}</td>
                      <td>{new Date(n.last).toLocaleString([], { hour12: false, day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </section>
  );
}
