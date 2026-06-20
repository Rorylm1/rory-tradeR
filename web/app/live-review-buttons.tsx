"use client";

import { CheckCircle2, CircleHelp, XCircle } from "lucide-react";
import { useState } from "react";

type Props = {
  proposalId: string;
  currentStatus?: string | null;
  readOnly?: boolean;
};

const actions = [
  {
    status: "approved_for_operator_check",
    label: "Operator check",
    icon: CheckCircle2,
  },
  {
    status: "needs_more_context",
    label: "More context",
    icon: CircleHelp,
  },
  {
    status: "rejected",
    label: "Reject",
    icon: XCircle,
  },
];

export function LiveReviewButtons({ proposalId, currentStatus, readOnly = false }: Props) {
  const [pending, setPending] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(currentStatus ?? null);

  async function submit(nextStatus: string) {
    if (readOnly) return;

    setPending(nextStatus);
    const response = await fetch("/api/backend/api/live-review", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        proposal_id: proposalId,
        status: nextStatus,
        note: "Recorded from deployed dashboard. No live order was placed.",
      }),
    });
    setPending(null);
    if (response.ok) {
      setStatus(nextStatus);
    }
  }

  return (
    <div className="review-actions" aria-label="Live review actions">
      {actions.map((action) => {
        const Icon = action.icon;
        const active = status === action.status;
        return (
          <button
            key={action.status}
            type="button"
            className={active ? "icon-button active" : "icon-button"}
            disabled={readOnly || pending !== null}
            title={
              readOnly
                ? "Public read-only dashboard: review status cannot be changed"
                : `${action.label}: records review status only, never places a live order`
            }
            onClick={() => submit(action.status)}
          >
            <Icon size={16} />
            <span>{pending === action.status ? "Saving" : action.label}</span>
          </button>
        );
      })}
    </div>
  );
}
