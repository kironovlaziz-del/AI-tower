"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/lib/auth";
import { LanguageSwitcher } from "./LanguageSwitcher";

const NAV = [
  {
    sectionKey: "sidebar.sections.overview",
    items: [{ href: "/dashboard", labelKey: "sidebar.nav.dashboard" }],
  },
  {
    sectionKey: "sidebar.sections.connections",
    items: [{ href: "/connections", labelKey: "sidebar.nav.connections" }],
  },
  {
    sectionKey: "sidebar.sections.management",
    items: [
      { href: "/policies", labelKey: "sidebar.nav.policies" },
      { href: "/use-cases", labelKey: "sidebar.nav.use_cases" },
      { href: "/providers", labelKey: "sidebar.nav.providers" },
      { href: "/users", labelKey: "sidebar.nav.users", adminOnly: true },
    ],
  },
  {
    sectionKey: "sidebar.sections.operations",
    items: [
      { href: "/requests", labelKey: "sidebar.nav.requests" },
      { href: "/approvals", labelKey: "sidebar.nav.approvals" },
    ],
  },
  {
    sectionKey: "sidebar.sections.monitoring",
    items: [
      { href: "/incidents", labelKey: "sidebar.nav.incidents" },
      { href: "/shadow-ai", labelKey: "sidebar.nav.shadow_ai" },
      { href: "/audit", labelKey: "sidebar.nav.audit" },
    ],
  },
  {
    sectionKey: "sidebar.sections.mlops",
    items: [
      { href: "/compute", labelKey: "sidebar.nav.compute" },
      { href: "/datasets", labelKey: "sidebar.nav.datasets" },
      { href: "/training", labelKey: "sidebar.nav.training" },
      { href: "/deployments", labelKey: "sidebar.nav.deployments" },
    ],
  },
  {
    sectionKey: "sidebar.sections.settings",
    items: [{ href: "/notifications", labelKey: "sidebar.nav.notifications" }],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const { t } = useTranslation();

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="sidebar-brand-title">AI Control Tower</div>
        <div className="sidebar-brand-sub">org-{user?.org_id ?? "—"}</div>
      </div>
      <nav className="sidebar-nav">
        {NAV.map((group) => (
          <div key={group.sectionKey}>
            <div className="sidebar-section">{t(group.sectionKey)}</div>
            {group.items
              .filter((item: any) => !item.adminOnly || user?.role === "admin")
              .map((item) => {
                const active =
                  pathname === item.href || pathname?.startsWith(item.href + "/");
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`sidebar-link${active ? " active" : ""}`}
                  >
                    {t(item.labelKey)}
                  </Link>
                );
              })}
          </div>
        ))}
      </nav>
      <div className="sidebar-footer">
        <div className="sidebar-user">{user?.name ?? "—"}</div>
        <div className="sidebar-org">
          {t(`sidebar.role_${user?.role ?? "user"}`)}
        </div>
        <div style={{ marginTop: 8 }}>
          <LanguageSwitcher />
        </div>
        <button className="sidebar-logout" onClick={logout}>
          {t("sidebar.logout")}
        </button>
      </div>
    </aside>
  );
}