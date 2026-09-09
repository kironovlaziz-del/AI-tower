"use client";

import React, { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { Sidebar } from "@/components/Sidebar";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/login");
    }
  }, [loading, user, router]);

  if (loading) {
    return <div className="loading-line" style={{ padding: 40 }}>Загрузка…</div>;
  }

  if (!user) {
    return null;
  }

  return (
    <div className="shell">
      <Sidebar />
      <div className="main">{children}</div>
    </div>
  );
}
