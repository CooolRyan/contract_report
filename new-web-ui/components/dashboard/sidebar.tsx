"use client";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  LayoutDashboard,
  ShieldCheck,
  FileText,
  Settings,
  HelpCircle,
  Github,
} from "lucide-react";
import type { TabType } from "@/lib/types";

interface SidebarProps {
  activeTab: TabType;
  onTabChange: (tab: TabType) => void;
}

const navigation = [
  { id: "dashboard" as const, label: "대시보드", icon: LayoutDashboard },
  { id: "verify" as const, label: "해시 검증", icon: ShieldCheck },
  { id: "detail" as const, label: "성과 상세", icon: FileText },
];

const bottomLinks = [
  { label: "설정", icon: Settings, href: "#" },
  { label: "도움말", icon: HelpCircle, href: "#" },
  { label: "GitHub", icon: Github, href: "https://github.com" },
];

export function Sidebar({ activeTab, onTabChange }: SidebarProps) {
  return (
    <aside className="hidden w-64 flex-col border-r border-border bg-sidebar lg:flex">
      <nav className="flex flex-1 flex-col gap-1 p-4">
        <div className="mb-2 px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          메뉴
        </div>
        {navigation.map((item) => (
          <Button
            key={item.id}
            variant={activeTab === item.id ? "secondary" : "ghost"}
            className={cn(
              "w-full justify-start gap-3",
              activeTab === item.id && "bg-sidebar-accent text-sidebar-accent-foreground"
            )}
            onClick={() => onTabChange(item.id)}
          >
            <item.icon className="h-4 w-4" />
            {item.label}
          </Button>
        ))}
      </nav>

      <div className="border-t border-sidebar-border p-4">
        <div className="flex flex-col gap-1">
          {bottomLinks.map((link) => (
            <Button
              key={link.label}
              variant="ghost"
              className="w-full justify-start gap-3 text-muted-foreground hover:text-foreground"
              asChild
            >
              <a href={link.href} target={link.href.startsWith("http") ? "_blank" : undefined} rel="noopener noreferrer">
                <link.icon className="h-4 w-4" />
                {link.label}
              </a>
            </Button>
          ))}
        </div>
      </div>
    </aside>
  );
}
