"use client";

import { useEffect, useState } from "react";

import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeadCell,
  TableRow,
} from "@/components/ui/table";
import { apiFetch, ApiRequestError } from "@/lib/api-client";
import type { AuditLogEntryOut, AuditChainVerification } from "@/lib/types";

export default function AuditLogPage() {
  const [search, setSearch] = useState("");
  const [outcome, setOutcome] = useState("all");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [loading, setLoading] = useState(true);
  const [entries, setEntries] = useState<AuditLogEntryOut[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [verification, setVerification] =
    useState<AuditChainVerification | null>(null);
  const [verifying, setVerifying] = useState(false);

  useEffect(() => {
    apiFetch<AuditLogEntryOut[]>("/admin/audit-log?limit=200")
      .then(setEntries)
      .catch((err) =>
        setError(
          err instanceof ApiRequestError
            ? err.message
            : "Failed to load audit log.",
        ),
      )
      .finally(() => setLoading(false));
  }, []);

  async function handleVerify() {
    setVerifying(true);
    try {
      setVerification(
        await apiFetch<AuditChainVerification>("/admin/audit-log/verify"),
      );
    } catch (err) {
      setError(
        err instanceof ApiRequestError ? err.message : "Verification failed.",
      );
    } finally {
      setVerifying(false);
    }
  }

  const filtered = entries.filter(
    (entry) =>
      (!search ||
        [
          entry.username,
          entry.action,
          entry.resource_type,
          entry.resource_id,
          entry.reason,
          entry.request_path,
          entry.ip_address,
        ].some((value) =>
          value.toLowerCase().includes(search.toLowerCase()),
        )) &&
      (outcome === "all" || entry.outcome === outcome) &&
      (!from || new Date(entry.ts) >= new Date(`${from}T00:00:00`)) &&
      (!to || new Date(entry.ts) <= new Date(`${to}T23:59:59.999`)),
  );

  return (
    <div className="flex h-full flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-foreground">Audit Log</h1>
          <p className="text-sm text-muted">
            Immutable, hash-chained record of every access to tracking,
            watchlist, and evidence-export endpoints — plus every permission or
            jurisdiction denial, anywhere in the system.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {verification && (
            <Badge tone={verification.intact ? "success" : "danger"}>
              {verification.intact ? "Chain intact" : "Chain broken"} (
              {verification.row_count} rows)
            </Badge>
          )}
          <Button
            variant="secondary"
            size="sm"
            onClick={() => void handleVerify()}
            disabled={verifying}
          >
            {verifying ? "Verifying…" : "Verify chain integrity"}
          </Button>
        </div>
      </div>

      {error && (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      )}

      <div className="flex flex-wrap items-end gap-3">
        <label className="text-xs text-muted">
          Search
          <Input
            aria-label="Search audit entries"
            placeholder="Actor, action, resource?"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </label>
        <label className="text-xs text-muted">
          Outcome
          <select
            className="block"
            value={outcome}
            onChange={(e) => setOutcome(e.target.value)}
          >
            <option value="all">All outcomes</option>
            <option value="allow">Allow</option>
            <option value="deny">Deny</option>
          </select>
        </label>
        <label className="text-xs text-muted">
          From
          <Input
            type="date"
            value={from}
            onChange={(e) => setFrom(e.target.value)}
          />
        </label>
        <label className="text-xs text-muted">
          To
          <Input
            type="date"
            value={to}
            min={from}
            onChange={(e) => setTo(e.target.value)}
          />
        </label>
        <span className="text-xs text-muted">
          {filtered.length} of {entries.length} loaded entries (latest 200)
        </span>
      </div>
      <Card className="flex min-h-0 flex-1 flex-col overflow-hidden">
        <CardHeader>
          <CardTitle>Recent entries</CardTitle>
        </CardHeader>
        <CardContent className="min-h-0 flex-1 overflow-y-auto p-0">
          <Table>
            <TableHead>
              <TableRow>
                <TableHeadCell>Time</TableHeadCell>
                <TableHeadCell>User</TableHeadCell>
                <TableHeadCell>Action</TableHeadCell>
                <TableHeadCell>Resource</TableHeadCell>
                <TableHeadCell>Outcome</TableHeadCell>
                <TableHeadCell>Reason</TableHeadCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filtered.map((entry) => (
                <TableRow key={entry.id}>
                  <TableCell className="whitespace-nowrap text-xs text-muted">
                    {new Date(entry.ts).toLocaleString()}
                  </TableCell>
                  <TableCell>{entry.username || "—"}</TableCell>
                  <TableCell className="font-mono text-xs">
                    {entry.action}
                    <div
                      className="mt-1 max-w-56 truncate text-xs text-muted"
                      title={entry.request_path}
                    >
                      {entry.request_path}
                    </div>
                  </TableCell>
                  <TableCell className="text-xs text-muted">
                    {entry.resource_type}
                    {entry.resource_id ? `:${entry.resource_id}` : ""}
                  </TableCell>
                  <TableCell>
                    <Badge
                      tone={entry.outcome === "allow" ? "success" : "danger"}
                    >
                      {entry.outcome}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-xs text-muted">
                    {entry.reason || "—"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          {loading && (
            <p role="status" className="p-4 text-sm text-muted">
              Loading audit entries?
            </p>
          )}
          {!loading && filtered.length === 0 && !error && (
            <p className="p-4 text-sm text-muted">
              No audit entries match this view.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
