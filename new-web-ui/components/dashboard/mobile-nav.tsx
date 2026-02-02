"use client";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { LayoutDashboard, ShieldCheck, FileText } from "lucide-react";
import type { TabType } from "@/lib/types";

interface MobileNavProps {
  activeTab: TabType;
  onTabChange: (tab: TabType) => void;
}

const navigation = [
  { id: "dashboard" as const, label: "대시보드", icon: LayoutDashboard },
  { id: "verify" as const, label: "검증", icon: ShieldCheck },
  { id: "detail" as const, label: "상세", icon: FileText },
];

export function MobileNav({ activeTab, onTabChange }: MobileNavProps) {
  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 border-t border-border bg-background lg:hidden">
      <div className="flex items-center justify-around">
        {navigation.map((item) => (
          <Button
            key={item.id}
            variant="ghost"
            className={cn(
              "flex h-16 flex-1 flex-col items-center justify-center gap-1 rounded-none",
              activeTab === item.id && "bg-accent text-accent-foreground"
            )}
            onClick={() => onTabChange(item.id)}
          >
            <item.icon className="h-5 w-5" />
            <span className="text-xs">{item.label}</span>
          </Button>
        ))}
      </div>
    </nav>
  );
}
