"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { api, type Ticket, type PaginatedTickets } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select } from "@/components/ui/select";
import { Card, CardContent } from "@/components/ui/card";

const priorityVariant = {
  High: "high",
  Medium: "medium",
  Low: "low",
} as const;

const statusVariant = {
  Open: "open",
  "In Progress": "in-progress",
  Resolved: "resolved",
} as const;

const STATUSES = ["Open", "In Progress", "Resolved"] as const;

export default function DashboardPage() {
  const router = useRouter();
  const [data, setData] = useState<PaginatedTickets | null>(null);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchTickets = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const result = await api.getTickets({
        page,
        per_page: 10,
        status: statusFilter || undefined,
        priority: priorityFilter || undefined,
      });
      setData(result);
    } catch (err) {
      if (err instanceof Error && err.message === "Invalid token") {
        localStorage.removeItem("token");
        router.push("/login");
        return;
      }
      setError(err instanceof Error ? err.message : "Failed to load tickets");
    } finally {
      setLoading(false);
    }
  }, [page, statusFilter, priorityFilter, router]);

  useEffect(() => {
    if (!localStorage.getItem("token")) {
      router.push("/login");
      return;
    }
    fetchTickets();
  }, [fetchTickets, router]);

  async function handleStatusChange(ticketId: string, newStatus: string) {
    try {
      await api.updateTicketStatus(ticketId, newStatus);
      fetchTickets();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to update ticket"
      );
    }
  }

  function handleLogout() {
    localStorage.removeItem("token");
    router.push("/login");
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            Ticket Dashboard
          </h1>
          <p className="text-muted-foreground mt-1">
            {data ? `${data.total} total tickets` : "Loading..."}
          </p>
        </div>
        <Button variant="outline" onClick={handleLogout}>
          Logout
        </Button>
      </div>

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <Select
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value);
            setPage(1);
          }}
          className="w-44"
        >
          <option value="">All Statuses</option>
          <option value="Open">Open</option>
          <option value="In Progress">In Progress</option>
          <option value="Resolved">Resolved</option>
        </Select>

        <Select
          value={priorityFilter}
          onChange={(e) => {
            setPriorityFilter(e.target.value);
            setPage(1);
          }}
          className="w-44"
        >
          <option value="">All Priorities</option>
          <option value="High">High</option>
          <option value="Medium">Medium</option>
          <option value="Low">Low</option>
        </Select>
      </div>

      {error && (
        <p className="text-sm text-destructive">{error}</p>
      )}

      {/* Ticket list */}
      {loading ? (
        <p className="text-muted-foreground text-sm">Loading tickets...</p>
      ) : data && data.tickets.length === 0 ? (
        <p className="text-muted-foreground text-sm">No tickets found.</p>
      ) : (
        <div className="space-y-3">
          {data?.tickets.map((ticket) => (
            <TicketRow
              key={ticket.id}
              ticket={ticket}
              onStatusChange={handleStatusChange}
            />
          ))}
        </div>
      )}

      {/* Pagination */}
      {data && data.total_pages > 1 && (
        <div className="flex items-center justify-center gap-2 pt-4">
          <Button
            variant="outline"
            size="sm"
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
          >
            Previous
          </Button>
          <span className="text-sm text-muted-foreground">
            Page {data.page} of {data.total_pages}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={page >= data.total_pages}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  );
}

function TicketRow({
  ticket,
  onStatusChange,
}: {
  ticket: Ticket;
  onStatusChange: (id: string, status: string) => void;
}) {
  return (
    <Card>
      <CardContent className="py-4 px-5">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0 space-y-1">
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="font-medium truncate">{ticket.title}</h3>
              <Badge variant={priorityVariant[ticket.priority]}>
                {ticket.priority}
              </Badge>
              <Badge variant={statusVariant[ticket.status]}>
                {ticket.status}
              </Badge>
              <Badge variant="secondary">{ticket.category}</Badge>
            </div>
            <p className="text-sm text-muted-foreground line-clamp-2">
              {ticket.description}
            </p>
            {ticket.ai_reasoning && (
              <p className="text-xs text-muted-foreground italic">
                AI: {ticket.ai_reasoning}
              </p>
            )}
            <p className="text-xs text-muted-foreground">
              {ticket.customer_email} &middot;{" "}
              {new Date(ticket.created_at).toLocaleDateString()}
            </p>
          </div>

          <Select
            value={ticket.status}
            onChange={(e) => onStatusChange(ticket.id, e.target.value)}
            className="w-36 shrink-0"
          >
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </Select>
        </div>
      </CardContent>
    </Card>
  );
}
