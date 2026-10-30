"use client";
import * as React from "react";
import * as TabsPrimitive from "@radix-ui/react-tabs";
import { cn } from "../lib";

export const Tabs = TabsPrimitive.Root;
export function TabsList({ className, ...p }: React.ComponentPropsWithoutRef<typeof TabsPrimitive.List>) {
  return <TabsPrimitive.List className={cn("inline-flex gap-1 rounded-lg bg-slate-100 p-1", className)} {...p} />;
}
export function TabsTrigger({ className, ...p }: React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>) {
  return (
    <TabsPrimitive.Trigger
      className={cn("rounded-md px-3 py-1.5 text-sm text-slate-600 data-[state=active]:bg-white data-[state=active]:text-slate-900 data-[state=active]:shadow-sm", className)}
      {...p}
    />
  );
}
export const TabsContent = TabsPrimitive.Content;
