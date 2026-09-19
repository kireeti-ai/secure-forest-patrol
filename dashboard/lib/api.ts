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
  isDemo?: boolean;
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
  isDemo?: boolean;
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
  isDemo?: boolean;
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
  isDemo?: boolean;
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
  isDemo?: boolean;
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
  isDemo?: boolean;
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
  isDemo?: boolean;
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
  isDemo?: boolean;
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
    // location/lastPatrolTime/lastSyncEvent/pendingRecords/verificationState
    // have no backend data source yet (checkpoints aren't cross-referenced
    // against patrol/sync history) -- honest placeholders, not fabricated.
    location: r.zoneId ?? "—",
    state: r.active ? "ONLINE" : "OFFLINE",
    lastPatrolTime: "—", lastSyncEvent: "—", pendingRecords: 0,
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
  isDemo?: boolean;
}

// ============================================================
// DEMO / MOCK DATA ADAPTERS (Explicitly Labeled)
// ============================================================

const MOCK_CHECKPOINTS: Checkpoint[] = [
  { id: "cp-1", checkpointId: "CP-01", zone: "Zone A - North Ridge", nodeId: "FN-01", location: "Sector 1 Trail", state: "ONLINE", lastPatrolTime: "2026-09-17 11:42:18", lastSyncEvent: "EVT-104", pendingRecords: 0, verificationState: "VERIFIED", isDemo: true },
  { id: "cp-2", checkpointId: "CP-02", zone: "Zone B - River Valley", nodeId: "FN-02", location: "Valley Pass Alpha", state: "ONLINE", lastPatrolTime: "2026-09-17 11:15:02", lastSyncEvent: "EVT-103", pendingRecords: 2, verificationState: "VERIFIED", isDemo: true },
  { id: "cp-3", checkpointId: "CP-03", zone: "Zone B - River Valley", nodeId: "FN-03", location: "Valley Pass Beta", state: "ONLINE", lastPatrolTime: "2026-09-17 09:30:45", lastSyncEvent: "EVT-098", pendingRecords: 0, verificationState: "VERIFIED", isDemo: true },
  { id: "cp-4", checkpointId: "CP-04", zone: "Zone C - Deep Forest", nodeId: "FN-04", location: "Old Mill Crossing", state: "OFFLINE", lastPatrolTime: "2026-09-16 16:20:00", lastSyncEvent: "EVT-085", pendingRecords: 5, verificationState: "PENDING", isDemo: true },
];

const MOCK_PATROLS: PatrolRecord[] = [
  { id: "pat-104", eventId: "EVT-104", nodeId: "FN-01", checkpointId: "CP-01", officerId: "OFF-08", officerName: "Officer K. Sharma", rfid: "RFID-9842A", rfidStatus: "VALID", fingerprintStatus: "MATCH", timestamp: "2026-09-17 11:42:18", gatewayReceiveTime: "2026-09-17 11:42:20", backendReceiveTime: "2026-09-17 11:42:22", sequence: 104, previousHash: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", currentHash: "8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4", signatureStatus: "VALID", ledgerStatus: "VALID", syncStatus: "SYNCED", recordStatus: "AUTHENTIC", isDemo: true },
  { id: "pat-103", eventId: "EVT-103", nodeId: "FN-02", checkpointId: "CP-02", officerId: "OFF-03", officerName: "Officer R. Verma", rfid: "RFID-4410B", rfidStatus: "VALID", fingerprintStatus: "MATCH", timestamp: "2026-09-17 11:15:02", gatewayReceiveTime: "2026-09-17 11:15:05", backendReceiveTime: "2026-09-17 11:15:08", sequence: 103, previousHash: "7d8f4346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4", currentHash: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", signatureStatus: "VALID", ledgerStatus: "VALID", syncStatus: "SYNCED", recordStatus: "AUTHENTIC", isDemo: true },
  { id: "pat-102", eventId: "EVT-102", nodeId: "FN-02", checkpointId: "CP-02", officerId: "OFF-12", officerName: "Unknown Subject", rfid: "RFID-0000X", rfidStatus: "INVALID", fingerprintStatus: "NO_MATCH", timestamp: "2026-09-17 10:05:44", gatewayReceiveTime: "2026-09-17 10:05:48", backendReceiveTime: "2026-09-17 10:05:52", sequence: 102, previousHash: "9a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b", currentHash: "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b", signatureStatus: "INVALID", ledgerStatus: "BROKEN", syncStatus: "SYNCED", recordStatus: "TAMPERED", isDemo: true },
];

const MOCK_OFFICERS: Officer[] = [
  { id: "off-1", officerId: "OFF-08", name: "Officer K. Sharma", state: "ACTIVE", lastVerifiedPatrol: "2026-09-17 11:42:18", patrolCount: 42, mismatchCount: 0, assignedCheckpoint: "CP-01", badgeNumber: "FP-884", isDemo: true },
  { id: "off-2", officerId: "OFF-03", name: "Officer R. Verma", state: "ACTIVE", lastVerifiedPatrol: "2026-09-17 11:15:02", patrolCount: 38, mismatchCount: 1, assignedCheckpoint: "CP-02", badgeNumber: "FP-412", isDemo: true },
  { id: "off-3", officerId: "OFF-15", name: "Officer M. Singh", state: "INACTIVE", lastVerifiedPatrol: "2026-09-15 14:00:00", patrolCount: 19, mismatchCount: 0, assignedCheckpoint: "CP-03", badgeNumber: "FP-109", isDemo: true },
];

const MOCK_ACOUSTIC_EVENTS: AcousticEvent[] = [
  { id: "ac-1", eventId: "AC-201", nodeId: "AN-01", checkpointId: "CP-02", zone: "Zone B - River Valley", timestamp: "2026-09-17 10:45:12", classification: "Gunshot", confidence: 0.94, reviewStatus: "PENDING_REVIEW", signatureStatus: "VALID", syncStatus: "SYNCED", clipAvailable: true, modelVersion: "TinyML-Forest-v1.2", isDemo: true },
  { id: "ac-2", eventId: "AC-202", nodeId: "AN-02", checkpointId: "CP-04", zone: "Zone C - Deep Forest", timestamp: "2026-09-17 08:20:30", classification: "Chainsaw", confidence: 0.88, reviewStatus: "CONFIRMED", signatureStatus: "VALID", syncStatus: "SYNCED", clipAvailable: true, modelVersion: "TinyML-Forest-v1.2", isDemo: true },
  { id: "ac-3", eventId: "AC-203", nodeId: "AN-01", checkpointId: "CP-01", zone: "Zone A - North Ridge", timestamp: "2026-09-16 19:10:00", classification: "Non-threat", confidence: 0.72, reviewStatus: "DISMISSED", signatureStatus: "VALID", syncStatus: "SYNCED", clipAvailable: false, modelVersion: "TinyML-Forest-v1.2", isDemo: true },
];

const MOCK_LEDGER_RECORDS: LedgerRecord[] = [
  { sequence: 101, nodeId: "FN-01", timestamp: "2026-09-17 08:00:00", previousHash: "0000000000000000000000000000000000000000000000000000000000000000", currentHash: "4b825dc642cb6eb9a060e54bf8d69288fbee4904", signature: "3045022100a98f...", signatureStatus: "VALID", chainStatus: "VALID", duplicateStatus: "UNIQUE", isDemo: true },
  { sequence: 102, nodeId: "FN-01", timestamp: "2026-09-17 09:15:00", previousHash: "4b825dc642cb6eb9a060e54bf8d69288fbee4904", currentHash: "7d8f4346648f6b96df89dda901c5176b10a6d839", signature: "304402201e7b8f...", signatureStatus: "VALID", chainStatus: "VALID", duplicateStatus: "UNIQUE", isDemo: true },
  { sequence: 103, nodeId: "FN-01", timestamp: "2026-09-17 11:15:02", previousHash: "7d8f4346648f6b96df89dda901c5176b10a6d839", currentHash: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4", signature: "3045022100f89a...", signatureStatus: "VALID", chainStatus: "VALID", duplicateStatus: "UNIQUE", isDemo: true },
  { sequence: 104, nodeId: "FN-01", timestamp: "2026-09-17 11:42:18", previousHash: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4", currentHash: "8f434346648f6b96df89dda901c5176b10a6d839", signature: "3045022100c41b...", signatureStatus: "VALID", chainStatus: "VALID", duplicateStatus: "UNIQUE", isDemo: true },
];

const MOCK_GATEWAY: GatewayStatus = {
  id: "gw-1",
  gatewayId: "GW-FOREST-01",
  status: "ONLINE",
  loraStatus: "ACTIVE",
  wifiStatus: "CONNECTED",
  backendStatus: "REACHABLE",
  lastSeen: new Date().toISOString(),
  recordsReceived: 142,
  recordsForwarded: 139,
  pendingSyncQueue: 3,
  duplicatePackets: 4,
  verificationFailures: 1,
  wifiIp: "192.168.1.150",
  firmware: "v2.1.0-esp32s3",
  isDemo: true,
};

const MOCK_NODES: FieldNode[] = [
  { id: "n-1", nodeId: "FN-01", nodeType: "CHECKPOINT_NODE", checkpointId: "CP-01", zone: "Zone A", lastEventTime: "2026-09-17 11:42:18", lastSyncTime: "2026-09-17 11:42:20", loraActivity: "ACTIVE", localQueueState: 0, rtcState: "SYNCED", batteryLevel: 94, health: "HEALTHY", firmwareVersion: "v1.4.0", isDemo: true },
  { id: "n-2", nodeId: "FN-02", nodeType: "CHECKPOINT_NODE", checkpointId: "CP-02", zone: "Zone B", lastEventTime: "2026-09-17 11:15:02", lastSyncTime: "2026-09-17 11:15:05", loraActivity: "ACTIVE", localQueueState: 2, rtcState: "SYNCED", batteryLevel: 88, health: "HEALTHY", firmwareVersion: "v1.4.0", isDemo: true },
  { id: "n-3", nodeId: "AN-01", nodeType: "ACOUSTIC_NODE", checkpointId: "CP-02", zone: "Zone B", lastEventTime: "2026-09-17 10:45:12", lastSyncTime: "2026-09-17 10:45:15", loraActivity: "ACTIVE", localQueueState: 0, rtcState: "SYNCED", batteryLevel: 91, health: "HEALTHY", firmwareVersion: "v2.0.1-tinyml", isDemo: true },
  { id: "n-4", nodeId: "FN-04", nodeType: "CHECKPOINT_NODE", checkpointId: "CP-04", zone: "Zone C", lastEventTime: "2026-09-16 16:20:00", lastSyncTime: "2026-09-16 16:20:05", loraActivity: "NO_SIGNAL", localQueueState: 5, rtcState: "DRIFT", batteryLevel: 42, health: "DEGRADED", firmwareVersion: "v1.4.0", isDemo: true },
];

const MOCK_SYNC_LOGS: SyncLog[] = [
  { id: "syn-1", eventId: "EVT-104", nodeId: "FN-01", eventTimestamp: "2026-09-17 11:42:18", gatewayReceiveTime: "2026-09-17 11:42:20", backendReceiveTime: "2026-09-17 11:42:22", syncResult: "SUCCESS", retryCount: 0, duplicateState: "UNIQUE", verificationResult: "PASSED", isDemo: true },
  { id: "syn-2", eventId: "EVT-103", nodeId: "FN-02", eventTimestamp: "2026-09-17 11:15:02", gatewayReceiveTime: "2026-09-17 11:15:05", backendReceiveTime: "2026-09-17 11:15:08", syncResult: "SUCCESS", retryCount: 0, duplicateState: "UNIQUE", verificationResult: "PASSED", isDemo: true },
  { id: "syn-3", eventId: "AC-201", nodeId: "AN-01", eventTimestamp: "2026-09-17 10:45:12", gatewayReceiveTime: "2026-09-17 10:45:14", backendReceiveTime: "2026-09-17 10:45:16", syncResult: "SUCCESS", retryCount: 1, duplicateState: "UNIQUE", verificationResult: "PASSED", isDemo: true },
];

const MOCK_SYSTEM_STATUS: ForestSystemStatus = {
  fieldLayer: { component: "Field Nodes & Checkpoints", status: "OPERATIONAL", details: "4 Field Nodes Active, RTC Synced" },
  gateway: { component: "LoRa Gateway Receiver", status: "CONNECTED", details: "SX1278 433MHz Active" },
  wifiBackhaul: { component: "Wi-Fi Backhaul IP Link", status: "CONNECTED", details: "IP 192.168.1.150 - WPA2 Secured" },
  backend: { component: "FastAPI Forest Service", status: "REACHABLE", details: "Endpoints active" },
  database: { component: "PostgreSQL Database", status: "HEALTHY", details: "Tables & constraints valid" },
  ledgerVerification: { component: "Hash Chain & RSA Verification", status: "OPERATIONAL", details: "Tamper-evident verification active" },
  isDemo: true,
};

// ============================================================
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
    if (!res.ok) return { gateway: null, nodes: [], database: "UNKNOWN", lastUpdated: null, isDemo: false } as unknown as ForestSystemStatus;
    return await res.json();
  } catch {
    return { gateway: null, nodes: [], database: "UNKNOWN", lastUpdated: null, isDemo: false } as unknown as ForestSystemStatus;
  }
}


