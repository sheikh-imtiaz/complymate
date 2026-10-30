"use client";
import { use } from "react";
import { Card, CardContent } from "@complymate/ui";
import { ActivityFeed } from "@/components/collaboration/ActivityFeed";

export default function ActivityPage({ params }: { params: Promise<{ clientId: string }> }) {
  const { clientId } = use(params);
  return <Card><CardContent className="pt-5"><ActivityFeed clientId={clientId} /></CardContent></Card>;
}
