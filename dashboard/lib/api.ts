  export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "https://secure-forest-patrol-4cxw.vercel.app";

function authHeaders(): Record<string, string> {
  return {};
}

// ============================================================
// FOREST PATROL DOMAIN TYPES
// ============================================================

export interface Checkpoint {
  id: string;
  checkpointId: string;
  zone: string;
  nodeId: string;
  location: string;
  state: "ONLINE" | "OFFLINE" | "MAINTENANCE";
  lastPatrolTime: string;
  lastSyncEvent: string;
  pendingRecords: number;
  verificationState: "VERIFIED" | "PENDING" | "MISMATCH";
}

export interface PatrolRecord {
  id: string;
  eventId: string;
  nodeId: string;
  checkpointId: string;
  officerId: string;
  officerName: string;
  rfid: string;
  rfidStatus: "VALID" | "INVALID";
  fingerprintStatus: "MATCH" | "NO_MATCH";
  timestamp: string;
  gatewayReceiveTime: string;
  backendReceiveTime: string;
  sequence: number;
  previousHash: string;
  currentHash: string;
  signatureStatus: "VALID" | "INVALID" | "PENDING";
  ledgerStatus: "VALID" | "BROKEN" | "PENDING";
  syncStatus: "SYNCED" | "PENDING" | "FAILED";
  recordStatus: "AUTHENTIC" | "TAMPERED" | "SUSPECTED";
}

export interface Officer {
  id: string;
  officerId: string;
  name: string;
  state: "ACTIVE" | "INACTIVE";
  // lastVerifiedPatrol/patrolCount/mismatchCount are real aggregates.
  // assignedCheckpoint is null -- officers have no checkpoint assignment
  // in the domain model yet.
  lastVerifiedPatrol: string | null;
  patrolCount: number;
  mismatchCount: number;
  assignedCheckpoint: string | null;
  badgeNumber: string;
}

export interface AcousticEvent {
  id: string;
  eventId: string;
  nodeId: string;
  checkpointId: string;
  zone: string;
  timestamp: string;
  classification: "Gunshot" | "Chainsaw" | "Non-threat";
  confidence: number; // e.g. 0.94 (94%)
  reviewStatus: "DETECTED" | "PENDING_REVIEW" | "REVIEWED" | "DISMISSED" | "CONFIRMED";
  signatureStatus: "VALID" | "INVALID";
  syncStatus: "SYNCED" | "PENDING" | "FAILED";
  clipAvailable: boolean;
  modelVersion?: string;
}

export interface LedgerRecord {
  sequence: number;
  nodeId: string;
  timestamp: string;
  previousHash: string;
  currentHash: string;
  signature: string;
  signatureStatus: "VALID" | "INVALID" | "PENDING";
  chainStatus: "VALID" | "BROKEN" | "PENDING";
  duplicateStatus: "UNIQUE" | "DUPLICATE";
}

export interface GatewayStatus {
  id: string;
  gatewayId: string;
  status: "ONLINE" | "OFFLINE";
  loraStatus: "CONNECTED" | "ACTIVE" | "NO_TRAFFIC" | "ERROR";
  wifiStatus: "CONNECTED" | "DISCONNECTED";
  backendStatus: "REACHABLE" | "UNREACHABLE";
  lastSeen: string;
  recordsReceived: number;
  recordsForwarded: number;
  pendingSyncQueue: number;
  // duplicatePackets/verificationFailures/wifiIp are null -- gateway
  // status reports don't carry them yet (see docs/GATEWAY_BACKEND_CONTRACT.md).
  duplicatePackets: number | null;
  verificationFailures: number | null;
  wifiIp: string | null;
  firmware: string;
}

export interface FieldNode {
  id: string;
  nodeId: string;
  nodeType: "CHECKPOINT_NODE" | "ACOUSTIC_NODE";
  checkpointId: string;
  zone: string;
  // lastEventTime is real (mirrors the node's last ingest). The rest are
  // null until node-firmware reports this telemetry -- see
  // docs/GATEWAY_BACKEND_CONTRACT.md. Render a placeholder, not "null".
  lastEventTime: string | null;
  lastSyncTime: string | null;
  loraActivity: "ACTIVE" | "IDLE" | "NO_SIGNAL" | null;
  localQueueState: number | null;
  rtcState: "SYNCED" | "DRIFT" | "ERROR" | null;
  batteryLevel: number | null;
  health: "HEALTHY" | "DEGRADED" | "OFFLINE" | null;
  firmwareVersion: string;
}

export interface SyncLog {
  id: string;
  eventId: string;
  nodeId: string;
  eventTimestamp: string;
  gatewayReceiveTime: string;
  backendReceiveTime: string;
  syncResult: "SUCCESS" | "FAILED" | "RETRYING";
  retryCount: number;
  duplicateState: "UNIQUE" | "DUPLICATE_DISCARDED";
  verificationResult: "PASSED" | "FAILED";
}

// ============================================================
// BACKEND -> DASHBOARD FIELD NORMALIZATION
//
// The backend serializes camelCase (see backend/app/schemas/forest.py),
// but a handful of fields are named differently on each side (not just
// casing) -- these functions are the single place that reconciles that.
// Raw response shapes are typed loosely (Record<string, any>) since they
// come straight off the wire; the return types are the real domain
// interfaces above.
// ============================================================

function normalizeCheckpoint(r: any): Checkpoint {
  return {
    id: r.id, checkpointId: r.checkpointId, zone: r.zoneId, nodeId: r.nodeId,
    location: r.zoneId ?? "—",
    // state is derived by the backend from the attached node's recent activity.
    state: r.state === "ONLINE" ? "ONLINE" : "OFFLINE",
    lastPatrolTime: r.lastPatrolAt ? new Date(r.lastPatrolAt).toLocaleString() : "—",
    // lastSyncEvent/pendingRecords/verificationState have no backend data
    // source yet -- honest placeholders, not fabricated.
    lastSyncEvent: "—", pendingRecords: 0,
    verificationState: "PENDING",
  };
}

function normalizePatrol(r: any): PatrolRecord {
  return {
    id: r.id, eventId: r.eventId, nodeId: r.nodeId, checkpointId: r.checkpointId,
    officerId: r.officerId, officerName: r.officerName ?? "—", rfid: r.rfid ?? "—",
    rfidStatus: r.rfidResult, fingerprintStatus: r.fingerprintResult,
    timestamp: r.eventCreatedAt, gatewayReceiveTime: r.gatewayReceivedAt,
    backendReceiveTime: r.backendReceivedAt, sequence: r.sequence,
    previousHash: r.previousHash, currentHash: r.recordHash,
    signatureStatus: r.signatureStatus, ledgerStatus: r.chainStatus,
    syncStatus: r.syncStatus, recordStatus: r.recordStatus ?? "SUSPECTED",
  };
}

function normalizeOfficer(r: any): Officer {
  return {
    id: r.id, officerId: r.officerId, name: r.name, state: r.status,
    lastVerifiedPatrol: r.lastVerifiedPatrol, patrolCount: r.patrolCount,
    mismatchCount: r.mismatchCount, assignedCheckpoint: r.assignedCheckpoint,
    badgeNumber: r.badgeNumber,
  };
}

function normalizeAcoustic(r: any): AcousticEvent {
  return {
    id: r.id, eventId: r.eventId, nodeId: r.nodeId, checkpointId: r.checkpointId,
    zone: r.zoneId, timestamp: r.eventCreatedAt, classification: r.classification,
    confidence: r.confidence, reviewStatus: r.reviewStatus,
    signatureStatus: r.signatureStatus, syncStatus: r.syncStatus,
    clipAvailable: r.clipAvailable, modelVersion: r.modelVersion,
  };
}

function normalizeLedger(r: any): LedgerRecord {
  return {
    sequence: r.sequence, nodeId: r.nodeId, timestamp: r.eventCreatedAt,
    previousHash: r.previousHash, currentHash: r.recordHash,
    signature: r.signature ?? "—", signatureStatus: r.signatureStatus,
    chainStatus: r.chainStatus, duplicateStatus: r.duplicateStatus,
  };
}

function normalizeGateway(r: any): GatewayStatus {
  return {
    id: r.id, gatewayId: r.gatewayId,
    // ONLINE/OFFLINE derived from backendStatus -- the raw `status` column
    // is a separate, unrelated lifecycle field (always "ACTIVE" today).
    status: r.backendStatus === "REACHABLE" ? "ONLINE" : "OFFLINE",
    loraStatus: r.loraStatus ?? "NO_TRAFFIC", wifiStatus: r.wifiStatus ?? "DISCONNECTED",
    backendStatus: r.backendStatus ?? "UNREACHABLE", lastSeen: r.lastSeenAt,
    recordsReceived: r.recordsReceived, recordsForwarded: r.recordsForwarded,
    pendingSyncQueue: r.pendingSyncQueue, duplicatePackets: r.duplicatePackets,
    verificationFailures: r.verificationFailures, wifiIp: r.wifiIp,
    firmware: r.firmwareVersion,
  };
}

function normalizeNode(r: any): FieldNode {
  return {
    id: r.id, nodeId: r.nodeId, nodeType: r.nodeType, checkpointId: r.checkpointId,
    zone: r.zoneId, lastEventTime: r.lastEventTime, lastSyncTime: r.lastSyncTime,
    loraActivity: r.loraActivity, localQueueState: r.localQueueState,
    rtcState: r.rtcState, batteryLevel: r.batteryLevel, health: r.health,
    firmwareVersion: r.firmwareVersion,
  };
}

const _SYNC_RESULT_BY_STATUS: Record<string, SyncLog["syncResult"]> = {
  VERIFIED: "SUCCESS", DUPLICATE: "SUCCESS", FAILED: "FAILED",
};

function normalizeSyncLog(r: any): SyncLog {
  return {
    id: r.id, eventId: r.eventId, nodeId: r.nodeId,
    eventTimestamp: r.eventTimestamp ?? r.receivedAt, gatewayReceiveTime: r.receivedAt,
    backendReceiveTime: r.forwardedAt,
    syncResult: _SYNC_RESULT_BY_STATUS[r.syncStatus] ?? "RETRYING",
    retryCount: r.attemptCount,
    duplicateState: r.duplicateState === "DUPLICATE" ? "DUPLICATE_DISCARDED" : "UNIQUE",
    verificationResult: r.verificationResult ?? "FAILED",
  };
}

export interface SystemComponentHealth {
  component: string;
  status: "OPERATIONAL" | "CONNECTED" | "REACHABLE" | "HEALTHY" | "DEGRADED" | "OFFLINE";
  details: string;
}

export interface ForestSystemStatus {
  fieldLayer: SystemComponentHealth;
  gateway: SystemComponentHealth;
  wifiBackhaul: SystemComponentHealth;
  backend: SystemComponentHealth;
  database: SystemComponentHealth;
  ledgerVerification: SystemComponentHealth;
}

// Production API fetchers. Failed requests return empty/unknown state; the
// dashboard must never present fabricated operational records as real data.
// ============================================================

export async function fetchCheckpoints(): Promise<Checkpoint[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/forest/checkpoints`, { cache: "no-store", headers: authHeaders() });
    if (!res.ok) return [];
    return (await res.json()).map(normalizeCheckpoint);
  } catch {
    return [];
  }
}

export async function fetchPatrols(): Promise<PatrolRecord[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/forest/patrols`, { cache: "no-store", headers: authHeaders() });
    if (!res.ok) return [];
    return (await res.json()).map(normalizePatrol);
  } catch {
    return [];
  }
}

export async function fetchPatrolById(id: string): Promise<PatrolRecord | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/forest/patrols/${encodeURIComponent(id)}`, { cache: "no-store", headers: authHeaders() });
    if (!res.ok) {
      return null;
    }
    return normalizePatrol(await res.json());
  } catch {
    return null;
  }
}

export async function fetchOfficers(): Promise<Officer[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/forest/officers`, { cache: "no-store", headers: authHeaders() });
    if (!res.ok) return [];
    return (await res.json()).map(normalizeOfficer);
  } catch {
    return [];
  }
}

export async function fetchAcousticEvents(): Promise<AcousticEvent[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/forest/acoustic-events`, { cache: "no-store", headers: authHeaders() });
    if (!res.ok) return [];
    return (await res.json()).map(normalizeAcoustic);
  } catch {
    return [];
  }
}

export async function fetchAcousticEventById(id: string): Promise<AcousticEvent | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/forest/acoustic-events/${encodeURIComponent(id)}`, { cache: "no-store", headers: authHeaders() });
    if (!res.ok) {
      return null;
    }
    return normalizeAcoustic(await res.json());
  } catch {
    return null;
  }
}

export async function fetchLedger(): Promise<LedgerRecord[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/forest/ledger`, { cache: "no-store", headers: authHeaders() });
    if (!res.ok) return [];
    return (await res.json()).map(normalizeLedger);
  } catch {
    return [];
  }
}

export async function fetchGateways(): Promise<GatewayStatus[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/forest/gateways`, { cache: "no-store", headers: authHeaders() });
    if (!res.ok) return [];
    return (await res.json()).map(normalizeGateway);
  } catch {
    return [];
  }
}

export async function fetchNodes(): Promise<FieldNode[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/forest/nodes`, { cache: "no-store", headers: authHeaders() });
    if (!res.ok) return [];
    return (await res.json()).map(normalizeNode);
  } catch {
    return [];
  }
}

export async function fetchSyncHistory(): Promise<SyncLog[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/forest/sync-history`, { cache: "no-store", headers: authHeaders() });
    if (!res.ok) return [];
    return (await res.json()).map(normalizeSyncLog);
  } catch {
    return [];
  }
}

export async function fetchForestSystemStatus(): Promise<ForestSystemStatus> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/forest/system-status`, { cache: "no-store", headers: authHeaders() });
    if (!res.ok) return { gateway: null, nodes: [], database: "UNKNOWN", lastUpdated: null } as unknown as ForestSystemStatus;
    return await res.json();
  } catch {
    return { gateway: null, nodes: [], database: "UNKNOWN", lastUpdated: null } as unknown as ForestSystemStatus;
  }
}


