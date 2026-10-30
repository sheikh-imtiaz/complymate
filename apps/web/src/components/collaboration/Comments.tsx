"use client";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button, Card, CardContent, CardHeader, CardTitle } from "@complymate/ui";
import type { CommentItem } from "@complymate/api-types";
import { get, post } from "@/lib/api-client";
import { formatDateTime } from "@/lib/format";
import { MentionInput } from "./MentionInput";

const renderMentions = (body: string) => body.replace(/@\[([^\]]+)\]\(user:[0-9a-f-]+\)/g, "@$1");

export function Comments({ resourceType, resourceId }: { resourceType: string; resourceId: string }) {
  const qc = useQueryClient();
  const key = ["comments", resourceType, resourceId];
  const { data = [] } = useQuery({ queryKey: key, queryFn: () => get<CommentItem[]>(`/comments?resource_type=${resourceType}&resource_id=${resourceId}`) });
  const [body, setBody] = useState("");
  const add = useMutation({
    mutationFn: () => post("/comments", { resource_type: resourceType, resource_id: resourceId, body }),
    onSuccess: () => {
      setBody("");
      void qc.invalidateQueries({ queryKey: key });
    },
  });
  return (
    <Card>
      <CardHeader><CardTitle>Comments</CardTitle></CardHeader>
      <CardContent className="space-y-3">
        {data.map((c) => (
          <div key={c.id} className="rounded-md bg-slate-50 p-3 text-sm">
            <p className="text-xs text-slate-500">{c.author_name ?? "User"} · {formatDateTime(c.created_at)}{c.edited_at ? " · edited" : ""}</p>
            <p className="mt-1 whitespace-pre-wrap">{renderMentions(c.body)}</p>
          </div>
        ))}
        <MentionInput value={body} onChange={setBody} />
        <div className="flex justify-end">
          <Button size="sm" onClick={() => add.mutate()} disabled={!body.trim()} loading={add.isPending}>Comment</Button>
        </div>
      </CardContent>
    </Card>
  );
}
