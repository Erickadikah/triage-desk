"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { api, type Ticket } from "@/lib/api";
import { removeToken } from "@/lib/auth";
import { Badge } from "@/components/ui/badge";
import { Select } from "@/components/ui/select";
import { Card, CardContent } from "@/components/ui/card";
import { ProtectedRoute } from "@/components/protected-route";

const priorityVariant = {
  High: "high",
  Medium: "medium",
  Low: "low",
} as const;

const COLUMNS = [
  { status: "Open", label: "Open", color: "bg-blue-500" },
  { status: "In Progress", label: "In Progress", color: "bg-purple-500" },
  { status: "Resolved", label: "Resolved", color: "bg-gray-400" },
] as const;

export default function DashboardPage() {
  return (
    <ProtectedRoute>
      <DashboardContent />
    </ProtectedRoute>
  );
}

function DashboardContent() {
  const router = useRouter();
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [priorityFilter, setPriorityFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchTickets = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      // Fetch all tickets (high per_page to get them all for the board)
      const result = await api.getTickets({
        page: 1,
        per_page: 100,
        priority: priorityFilter || undefined,
      });
      setTickets(result.tickets);
    } catch (err) {
      if (err instanceof Error && err.message === "Invalid token") {
        removeToken();
        router.push("/login");
        return;
      }
      setError(err instanceof Error ? err.message : "Failed to load tickets");
    } finally {
      setLoading(false);
    }
  }, [priorityFilter, router]);

  useEffect(() => {
    fetchTickets();
  }, [fetchTickets]);

  async function handleStatusChange(ticketId: string, newStatus: string) {
    // Optimistic update — move the ticket immediately
    const previousTickets = [...tickets];
    setTickets((prev) =>
      prev.map((t) =>
        t.id === ticketId ? { ...t, status: newStatus as Ticket["status"] } : t
      )
    );

    try {
      await api.updateTicketStatus(ticketId, newStatus);
    } catch (err) {
      // Revert on failure
      setTickets(previousTickets);
      setError(
        err instanceof Error ? err.message : "Failed to update ticket"
      );
    }
  }

  const ticketsByStatus = (status: string) =>
    tickets.filter((t) => t.status === status);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            Agent Dashboard
          </h1>
          <p className="text-muted-foreground mt-1">
            {tickets.length} ticket{tickets.length !== 1 ? "s" : ""}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Select
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
            className="w-44"
          >
            <option value="">All Priorities</option>
            <option value="High">High</option>
            <option value="Medium">Medium</option>
            <option value="Low">Low</option>
          </Select>
        </div>
      </div>

      {error && (
        <div className="rounded-md bg-destructive/10 border border-destructive/20 px-4 py-3">
          <p className="text-sm text-destructive">{error}</p>
        </div>
      )}

      {/* Kanban Board */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {COLUMNS.map((col) => (
            <KanbanColumn
              key={col.status}
              label={col.label}
              color={col.color}
              tickets={ticketsByStatus(col.status)}
              onStatusChange={handleStatusChange}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function KanbanColumn({
  label,
  color,
  tickets,
  onStatusChange,
}: {
  label: string;
  color: string;
  tickets: Ticket[];
  onStatusChange: (id: string, status: string) => void;
}) {
  return (
    <div className="flex flex-col rounded-lg border border-border bg-muted/30 min-h-[60vh]">
      {/* Column header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-border">
        <div className={`h-2.5 w-2.5 rounded-full ${color}`} />
        <h2 className="text-sm font-semibold">{label}</h2>
        <span className="ml-auto text-xs text-muted-foreground bg-muted rounded-full px-2 py-0.5">
          {tickets.length}
        </span>
      </div>

      {/* Cards */}
      <div className="flex-1 p-2 space-y-2 overflow-y-auto">
        {tickets.length === 0 ? (
          <p className="text-xs text-muted-foreground text-center py-8">
            No tickets
          </p>
        ) : (
          tickets.map((ticket) => (
            <TicketCard
              key={ticket.id}
              ticket={ticket}
              onStatusChange={onStatusChange}
            />
          ))
        )}
      </div>
    </div>
  );
}

function TicketCard({
  ticket,
  onStatusChange,
}: {
  ticket: Ticket;
  onStatusChange: (id: string, status: string) => void;
}) {
  return (
    <Card className="shadow-sm hover:shadow-md transition-shadow">
      <CardContent className="p-3 space-y-2">
        <h3 className="text-sm font-medium leading-snug">{ticket.title}</h3>

        <div className="flex items-center gap-1.5 flex-wrap">
          <Badge variant={priorityVariant[ticket.priority]} className="text-[10px] px-1.5 py-0">
            {ticket.priority}
          </Badge>
          <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
            {ticket.category}
          </Badge>
        </div>

        <p className="text-xs text-muted-foreground line-clamp-2">
          {ticket.description}
        </p>

        {ticket.ai_reasoning && (
          <p className="text-[11px] text-muted-foreground italic border-l-2 border-primary/30 pl-2">
            {ticket.ai_reasoning}
          </p>
        )}

        <div className="flex items-center justify-between pt-1 border-t border-border/50">
          <span className="text-[10px] text-muted-foreground truncate max-w-[120px]">
            {ticket.customer_email}
          </span>
          <Select
            value={ticket.status}
            onChange={(e) => onStatusChange(ticket.id, e.target.value)}
            className="h-7 text-xs w-[110px] px-1.5 py-0"
          >
            <option value="Open">Open</option>
            <option value="In Progress">In Progress</option>
            <option value="Resolved">Resolved</option>
          </Select>
        </div>
      </CardContent>
    </Card>
  );
}
