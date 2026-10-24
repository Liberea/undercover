import type { Status } from "./api";
import { STATUS_LABELS } from "./format";

export function StatusPill({ status }: Readonly<{ status: Status }>) {
  return (
    <span className={`pill status-${status}`}>
      <span className="dot" aria-hidden="true" />
      {STATUS_LABELS[status]}
    </span>
  );
}
