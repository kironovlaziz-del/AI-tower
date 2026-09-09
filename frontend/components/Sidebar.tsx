"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth";

const NAV = [
  {
    section: "Обзор",
    items: [{ href: "/dashboard", label: "Панель управления" }],
  },
  {
    section: "Подключения",
    items: [{ href: "/connections", label: "Connections" }],
  },
  {
    section: "Управление",
    items: [
      { href: "/policies", label: "Policy Center" },
      { href: "/use-cases", label: "Сценарии использования" },
      { href: "/providers", label: "Vendor Risk Desk" },
    ],
  },
  {
    section: "Операции",
    items: [
      { href: "/requests", label: "Usage Registry" },
      { href: "/approvals", label: "Approval Workflow" },
    ],
  },
  {
    section: "Мониторинг",
    items: [
      { href: "/incidents", label: "Incident Tracker" },
      { href: "/shadow-ai", label: "Shadow AI Monitor" },
      { href: "/audit", label: "Audit & Reporting" },
    ],
  },
  {
    section: "MLOps",
    items: [
      { href: "/compute", label: "Compute Detector" },
      { href: "/datasets", label: "Dataset Manager" },
      { href: "/training", label: "Training Service" },
    ],
  },
  {
    section: "Настройки",
    items: [{ href: "/notifications", label: "Notification Service" }],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="sidebar-brand-title">AI Control Tower</div>
        <div className="sidebar-brand-sub">org-{user?.org_id ?? "—"}</div>
      </div>
      <nav className="sidebar-nav">
        {NAV.map((group) => (
          <div key={group.section}>
            <div className="sidebar-section">{group.section}</div>
            {group.items.map((item) => {
              const active =
                pathname === item.href || pathname?.startsWith(item.href + "/");
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`sidebar-link${active ? " active" : ""}`}
                >
                  {item.label}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>
      <div className="sidebar-footer">
        <div className="sidebar-user">{user?.name ?? "—"}</div>
        <div className="sidebar-org">{user?.role}</div>
        <button className="sidebar-logout" onClick={logout}>
          Выйти
        </button>
      </div>
    </aside>
  );
}
