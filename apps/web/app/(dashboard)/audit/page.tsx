"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeadCell, TableRow } from "@/components/ui/table";
import { apiFetch, ApiRequestError } from "@/lib/api-client";

interface AuditLogEntryOut {
  id: string;
  ts: string;
  username: string;
  action: string;
  resource_type: string;
  resource_id: string;
  outcome: "allow" | "deny";
  reason: string;
  ip_address: string;
  request_path: string;
}

interface AuditChainVerification {
  intact: boolean;
  row_count: number;
}

export default function AuditLogPage() {
  const [entries, setEntries] = useState<AuditLogEntryOut[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [verification, setVerification] = useState<AuditChainVerification | null>(null);
  const [verifying, setVerifying] = useState(false);

  useEffect(() => {
    apiFetch<AuditLogEntryOut[]>("/admin/audit-log?limit=200")
      .then(setEntries)
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : "Failed to load audit log."));
  }, []);

  async function handleVerify() {
    setVerifying(true);
    try {
      setVerification(await apiFetch<AuditChainVerification>("/admin/audit-log/verify"));
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "Verification failed.");
    } finally {
      setVerifying(false);
    }
  }

  return (
    <div className="flex h-full flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-foreground">Audit Log</h1>
          <p className="text-sm text-muted">
            Immutable, hash-chained record of every access to tracking, watchlist, and evidence-export
            endpoints — plus every permission or jurisdiction denial, anywhere in the system.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {verification && (
            <Badge tone={verification.intact ? "success" : "danger"}>
              {verification.intact ? "Chain intact" : "Chain broken"} ({verification.row_count} rows)
            </Badge>
          )}
          <Button variant="secondary" size="sm" onClick={() => void handleVerify()} disabled={verifying}>
            {verifying ? "Verifying…" : "Verify chain integrity"}
          </Button>
        </div>
      </div>

      {error && (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      )}

      <Card className="min-h-0 flex-1 overflow-hidden">
        <CardHeader>
          <CardTitle>Recent entries</CardTitle>
        </CardHeader>
        <CardContent className="h-full overflow-y-auto p-0">
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
              {entries.map((entry) => (
                <TableRow key={entry.id}>
                  <TableCell className="whitespace-nowrap text-xs text-muted">
                    {new Date(entry.ts).toLocaleString()}
                  </TableCell>
                  <TableCell>{entry.username || "—"}</TableCell>
                  <TableCell className="font-mono text-xs">{entry.action}</TableCell>
                  <TableCell className="text-xs text-muted">
                    {entry.resource_type}
                    {entry.resource_id ? `:${entry.resource_id}` : ""}
                  </TableCell>
                  <TableCell>
                    <Badge tone={entry.outcome === "allow" ? "success" : "danger"}>{entry.outcome}</Badge>
                  </TableCell>
                  <TableCell className="text-xs text-muted">{entry.reason || "—"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          {entries.length === 0 && !error && <p className="p-4 text-sm text-muted">No audit entries yet.</p>}
        </CardContent>
      </Card>
    </div>
  );
}
