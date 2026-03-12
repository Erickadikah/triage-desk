"use client";

import { useState } from "react";
import { FilePlus, CheckCircle, X } from "lucide-react";
import { api, type Ticket } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { PRIORITY_VARIANT } from "@/lib/utils";

export default function SubmitTicketPage() {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [created, setCreated] = useState<Ticket | null>(null);
  const [toast, setToast] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const ticket = await api.createTicket({
        title,
        description,
        customer_email: email,
      });
      setCreated(ticket);
      setToast(true);
      setTimeout(() => setToast(false), 4000);
      setTitle("");
      setDescription("");
      setEmail("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create ticket");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
            <FilePlus className="h-5 w-5 text-primary" />
          </div>
          <h1 className="text-3xl font-bold tracking-tight">Submit a Support Ticket</h1>
        </div>
        <p className="text-muted-foreground mt-2">
          Describe your issue and our AI will automatically categorize and prioritize it.
        </p>
      </div>

      <Card>
        <CardContent className="pt-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <label htmlFor="title" className="text-sm font-medium">
                Title
              </label>
              <Input
                id="title"
                placeholder="Brief summary of your issue"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                required
                minLength={3}
                maxLength={255}
              />
            </div>

            <div className="space-y-2">
              <label htmlFor="description" className="text-sm font-medium">
                Description
              </label>
              <textarea
                id="description"
                placeholder="Please provide details about your issue..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                required
                minLength={10}
                rows={5}
                className="flex w-full rounded-md border border-border bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
            </div>

            <div className="space-y-2">
              <label htmlFor="email" className="text-sm font-medium">
                Your Email
              </label>
              <Input
                id="email"
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>

            {error && (
              <p className="text-sm text-destructive">{error}</p>
            )}

            <Button type="submit" disabled={loading} className="w-full">
              {loading ? "Submitting..." : "Submit Ticket"}
            </Button>
          </form>
        </CardContent>
      </Card>

      {created && (
        <Card className="border-green-200 bg-green-50">
          <CardHeader>
            <CardTitle className="text-lg">Ticket Created</CardTitle>
            <CardDescription>
              Your ticket has been submitted and automatically triaged by AI.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center gap-2 flex-wrap">
              <Badge variant={PRIORITY_VARIANT[created.priority]}>
                {created.priority} Priority
              </Badge>
              <Badge variant="secondary">{created.category}</Badge>
              <Badge variant="open">{created.status}</Badge>
            </div>
            {created.ai_reasoning && (
              <div className="rounded-md bg-white p-3 text-sm border border-green-200">
                <span className="font-medium">AI Reasoning: </span>
                {created.ai_reasoning}
              </div>
            )}
            <p className="text-xs text-muted-foreground">
              Ticket ID: {created.id}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Success toast */}
      {toast && (
        <div className="fixed bottom-6 right-6 z-50 animate-in slide-in-from-bottom-4 fade-in duration-300">
          <div className="flex items-center gap-3 rounded-lg border border-green-200 bg-green-50 px-4 py-3 shadow-lg">
            <CheckCircle className="h-5 w-5 text-green-600" />
            <p className="text-sm font-medium text-green-800">Ticket created successfully!</p>
            <button onClick={() => setToast(false)} className="ml-2 text-green-600 hover:text-green-800" aria-label="Dismiss notification">
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
