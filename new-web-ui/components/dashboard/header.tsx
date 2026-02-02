"use client";

import { useTheme } from "next-themes";
import { useAccount, useConnect, useDisconnect } from "wagmi";
import { Button } from "@/components/ui/button";
import { Moon, Sun, Wallet, LogOut, ExternalLink } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

function formatAddress(address: string): string {
  return `${address.slice(0, 6)}...${address.slice(-4)}`;
}

function getChainName(chainId: number | undefined): string {
  const chains: Record<number, string> = {
    1: "Ethereum",
    11155111: "Sepolia",
    137: "Polygon",
    80002: "Amoy",
  };
  return chainId ? chains[chainId] || `Chain ${chainId}` : "";
}

export function Header() {
  const { theme, setTheme } = useTheme();
  const { address, isConnected, chainId } = useAccount();
  const { connect, connectors, isPending } = useConnect();
  const { disconnect } = useDisconnect();

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-16 items-center justify-between px-4">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
            <span className="text-sm font-bold text-primary-foreground">PR</span>
          </div>
          <div>
            <h1 className="text-lg font-semibold text-foreground">
              Performance Registry
            </h1>
            <p className="text-xs text-muted-foreground">On-chain Trading Proof</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            aria-label="테마 변경"
          >
            <Sun className="h-5 w-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
            <Moon className="absolute h-5 w-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
          </Button>

          {isConnected && address ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" className="gap-2 bg-transparent">
                  <div className="h-2 w-2 rounded-full bg-success" />
                  <span className="font-mono text-sm">
                    {formatAddress(address)}
                  </span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuItem disabled className="flex flex-col items-start">
                  <span className="text-xs text-muted-foreground">네트워크</span>
                  <span className="font-medium">{getChainName(chainId)}</span>
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() =>
                    window.open(
                      `https://sepolia.etherscan.io/address/${address}`,
                      "_blank"
                    )
                  }
                >
                  <ExternalLink className="mr-2 h-4 w-4" />
                  Etherscan에서 보기
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => disconnect()}>
                  <LogOut className="mr-2 h-4 w-4" />
                  연결 해제
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <Button
              onClick={() => connectors[0] && connect({ connector: connectors[0] })}
              disabled={isPending || !connectors[0]}
              className="gap-2"
            >
              <Wallet className="h-4 w-4" />
              {isPending ? "연결 중..." : "지갑 연결"}
            </Button>
          )}
        </div>
      </div>
    </header>
  );
}
