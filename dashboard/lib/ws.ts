/**
 * Backend -> Dashboard live-update WebSocket client.
 *
 * PostgreSQL (via REST) remains the source of truth -- see docs/WEBSOCKET.md.
 * This client only notifies; on connect and on every reconnect it expects
 * the caller to refetch REST state rather than trusting anything reconstructed
 * from socket messages alone.
 */
import { useEffect, useRef } from "react";
import { API_BASE_URL } from "./api";

export type ForestWsEventType =
  | "PATROL_EVENT_VERIFIED"
  | "PATROL_EVENT_REJECTED"
  | "ACOUSTIC_EVENT_RECEIVED"
  | "LEDGER_VERIFICATION_RESULT"
  | "NODE_STATUS_CHANGED"
  | "GATEWAY_STATUS_CHANGED"
  | "SYNC_UPDATED";

export interface ForestWsMessage {
  type: ForestWsEventType;
  timestamp: string;
  [key: string]: unknown;
}

const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 15000;

function wsUrl(): string {
  return API_BASE_URL.replace(/^http/, "ws") + "/ws";
}

/**
 * Subscribes to the backend WebSocket and calls `onEvent` for every message
 * whose type is in `eventTypes`. Calls `onReconnect` once right after every
 * successful connection (including the first) so the caller can refetch its
 * REST data -- this hook never assumes the dashboard can rebuild state from
 * socket messages alone.
 */
export function useForestWebSocket(
  eventTypes: ForestWsEventType[],
  onEvent: (message: ForestWsMessage) => void,
  onReconnect: () => void
): void {
  const onEventRef = useRef(onEvent);
  const onReconnectRef = useRef(onReconnect);
  onEventRef.current = onEvent;
  onReconnectRef.current = onReconnect;

  useEffect(() => {
    let socket: WebSocket | null = null;
    let closedByEffect = false;
    let attempt = 0;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

    function connect() {
      try {
        socket = new WebSocket(wsUrl());
      } catch {
        scheduleReconnect();
        return;
      }

      socket.onopen = () => {
        attempt = 0;
        onReconnectRef.current();
      };

      socket.onmessage = (event) => {
        let message: ForestWsMessage;
        try {
          message = JSON.parse(event.data);
        } catch {
          return;
        }
        if (eventTypes.includes(message.type)) {
          onEventRef.current(message);
        }
      };

      socket.onclose = () => {
        if (!closedByEffect) scheduleReconnect();
      };

      socket.onerror = () => {
        socket?.close();
      };
    }

    function scheduleReconnect() {
      const delay = Math.min(RECONNECT_BASE_MS * 2 ** attempt, RECONNECT_MAX_MS);
      attempt += 1;
      reconnectTimer = setTimeout(connect, delay);
    }

    connect();

    return () => {
      closedByEffect = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      socket?.close();
    };
    // eventTypes is expected to be a stable literal array per call site.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
}
