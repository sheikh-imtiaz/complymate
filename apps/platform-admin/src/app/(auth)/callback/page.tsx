"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Spinner } from "@complymate/ui";
import { completeSignIn } from "@/lib/auth";

export default function Callback() {
  const router = useRouter();
  useEffect(() => {
    void completeSignIn().then(() => router.replace("/tenants"));
  }, [router]);
  return <div className="flex min-h-screen items-center justify-center"><Spinner /></div>;
}
