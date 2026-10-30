"use client";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { Notification } from "@complymate/api-types";
import { Button, Card, CardContent, EmptyState, PageHeader } from "@complymate/ui";
import { get, post } from "@/lib/api-client";
import { formatDateTime } from "@/lib/format";

export default function NotificationsPage() {
  const qc = useQueryClient();
  const { data = [] } = useQuery({ queryKey: ["notifications"], queryFn: () => get<Notification[]>("/notifications") });
  const refresh = () => void qc.invalidateQueries({ queryKey: ["notifications"] });
  const readAll = useMutation({ mutationFn: () => post("/notifications/read-all"), onSuccess: refresh });
  return (
    <>
      <PageHeader title="Notifications" actions={<Button variant="secondary" onClick={() => readAll.mutate()}>Mark all read</Button>} />
      {!data.length ? <EmptyState title="No notifications" /> : (
        <div className="space-y-2">
          {data.map((n) => (
            <Card key={n.id} className={n.read_at ? "opacity-70" : ""}>
              <CardContent className="flex items-start justify-between gap-4 pt-4">
                <div>
                  <p className="font-medium">{n.title}</p>
                  {n.body ? <p className="text-sm text-slate-600">{n.body}</p> : null}
                  <p className="text-xs text-slate-400">{formatDateTime(n.created_at)}</p>
                </div>
                <div className="flex gap-2">
                  {n.link ? <Button asChild size="sm" variant="secondary"><Link href={n.link} onClick={() => void post(`/notifications/${n.id}/read`)}>Open</Link></Button> : null}
                  {!n.read_at ? <Button size="sm" variant="ghost" onClick={async () => { await post(`/notifications/${n.id}/read`); refresh(); }}>Read</Button> : null}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </>
  );
}
