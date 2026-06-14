"use client";

import { useState } from "react";
import { api, Notification } from "@/lib/api";

export default function NotificationBell({
  notifications,
  onChanged,
}: {
  notifications: Notification[];
  onChanged: () => void;
}) {
  const [open, setOpen] = useState(false);
  const unread = notifications.filter((n) => !n.read).length;

  async function markRead(n: Notification) {
    if (!n.read) {
      await api.markRead(n.id).catch(() => {});
      onChanged();
    }
  }

  async function markAll() {
    await api.markAllRead().catch(() => {});
    onChanged();
  }

  return (
    <div className="bell-wrap">
      <button className="btn secondary" onClick={() => setOpen((o) => !o)}>
        🔔{unread > 0 && <span className="bell-badge">{unread}</span>}
      </button>
      {open && (
        <div className="bell-panel">
          <div className="row" style={{ justifyContent: "space-between" }}>
            <strong>Notifications</strong>
            {unread > 0 && (
              <button className="link-btn" onClick={markAll}>
                Mark all read
              </button>
            )}
          </div>
          {notifications.length === 0 && (
            <p className="muted">No notifications yet.</p>
          )}
          {notifications.slice(0, 20).map((n) => (
            <div
              key={n.id}
              className={`bell-item ${n.read ? "" : "unread"}`}
              onClick={() => markRead(n)}
            >
              <div style={{ fontSize: 14 }}>{n.title}</div>
              {n.body && <div className="muted">{n.body}</div>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
