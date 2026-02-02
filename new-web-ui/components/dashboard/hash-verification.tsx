"use client";

import React from "react"

import { useState, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Upload,
  Shield,
  CheckCircle,
  XCircle,
  Copy,
  FileJson,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { HashVerificationResult } from "@/lib/types";

async function computeSHA256(data: string): Promise<string> {
  const encoder = new TextEncoder();
  const dataBuffer = encoder.encode(data);
  const hashBuffer = await crypto.subtle.digest("SHA-256", dataBuffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
}

export function HashVerification() {
  const [jsonInput, setJsonInput] = useState("");
  const [onChainHash, setOnChainHash] = useState("");
  const [result, setResult] = useState<HashVerificationResult | null>(null);
  const [isVerifying, setIsVerifying] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const file = e.dataTransfer.files[0];
    if (file && file.type === "application/json") {
      const reader = new FileReader();
      reader.onload = (event) => {
        const content = event.target?.result as string;
        setJsonInput(content);
      };
      reader.readAsText(file);
    }
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = (event) => {
          const content = event.target?.result as string;
          setJsonInput(content);
        };
        reader.readAsText(file);
      }
    },
    []
  );

  const verifyHash = async () => {
    if (!jsonInput.trim() || !onChainHash.trim()) {
      return;
    }

    setIsVerifying(true);
    try {
      // Normalize JSON (parse and stringify to ensure consistent formatting)
      const parsed = JSON.parse(jsonInput);
      const normalized = JSON.stringify(parsed, null, 0);
      const computedHash = await computeSHA256(normalized);

      const isValid =
        computedHash.toLowerCase() === onChainHash.toLowerCase().replace("0x", "");

      setResult({
        isValid,
        computedHash: `0x${computedHash}`,
        onChainHash: onChainHash.startsWith("0x")
          ? onChainHash
          : `0x${onChainHash}`,
        message: isValid
          ? "해시가 일치합니다. 데이터가 변조되지 않았습니다."
          : "해시가 일치하지 않습니다. 데이터가 변조되었을 수 있습니다.",
      });
    } catch {
      setResult({
        isValid: false,
        computedHash: "",
        onChainHash,
        message: "JSON 파싱 오류: 올바른 JSON 형식인지 확인하세요.",
      });
    } finally {
      setIsVerifying(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Shield className="h-5 w-5 text-primary" />
            해시 검증 도구
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* JSON Input */}
          <div className="space-y-2">
            <Label htmlFor="json-input">성과 요약 JSON</Label>
            <div
              className={cn(
                "relative rounded-lg border-2 border-dashed transition-colors",
                isDragging
                  ? "border-primary bg-primary/5"
                  : "border-border hover:border-muted-foreground"
              )}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
            >
              {!jsonInput ? (
                <div className="flex flex-col items-center justify-center gap-4 p-8">
                  <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted">
                    <FileJson className="h-6 w-6 text-muted-foreground" />
                  </div>
                  <div className="text-center">
                    <p className="text-sm font-medium">
                      JSON 파일을 드래그하거나 클릭하여 업로드
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      성과 요약 JSON 파일을 업로드하세요
                    </p>
                  </div>
                  <label htmlFor="file-upload">
                    <Button variant="outline" size="sm" className="gap-2 bg-transparent" asChild>
                      <span>
                        <Upload className="h-4 w-4" />
                        파일 선택
                      </span>
                    </Button>
                    <input
                      id="file-upload"
                      type="file"
                      accept=".json"
                      className="hidden"
                      onChange={handleFileInput}
                    />
                  </label>
                </div>
              ) : (
                <Textarea
                  id="json-input"
                  value={jsonInput}
                  onChange={(e) => setJsonInput(e.target.value)}
                  placeholder='{"totalPnl": 15.5, "maxDrawdown": -8.2, ...}'
                  className="min-h-[200px] resize-none border-0 font-mono text-sm focus-visible:ring-0"
                />
              )}
            </div>
            {jsonInput && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setJsonInput("")}
                className="text-muted-foreground"
              >
                초기화
              </Button>
            )}
          </div>

          {/* On-chain Hash Input */}
          <div className="space-y-2">
            <Label htmlFor="onchain-hash">온체인 해시 (스마트 컨트랙트에 기록된 값)</Label>
            <Input
              id="onchain-hash"
              value={onChainHash}
              onChange={(e) => setOnChainHash(e.target.value)}
              placeholder="0x..."
              className="font-mono"
            />
          </div>

          {/* Verify Button */}
          <Button
            onClick={verifyHash}
            disabled={!jsonInput.trim() || !onChainHash.trim() || isVerifying}
            className="w-full gap-2"
          >
            {isVerifying ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Shield className="h-4 w-4" />
            )}
            {isVerifying ? "검증 중..." : "해시 검증"}
          </Button>
        </CardContent>
      </Card>

      {/* Result */}
      {result && (
        <Card
          className={cn(
            "border-2",
            result.isValid ? "border-success/50" : "border-destructive/50"
          )}
        >
          <CardContent className="pt-6">
            <div className="flex items-start gap-4">
              <div
                className={cn(
                  "flex h-10 w-10 shrink-0 items-center justify-center rounded-full",
                  result.isValid ? "bg-success/10" : "bg-destructive/10"
                )}
              >
                {result.isValid ? (
                  <CheckCircle className="h-5 w-5 text-success" />
                ) : (
                  <XCircle className="h-5 w-5 text-destructive" />
                )}
              </div>
              <div className="flex-1 space-y-4">
                <div>
                  <Badge
                    variant={result.isValid ? "default" : "destructive"}
                    className={cn(
                      "mb-2",
                      result.isValid && "bg-success text-success-foreground"
                    )}
                  >
                    {result.isValid ? "검증 성공" : "검증 실패"}
                  </Badge>
                  <p className="text-sm text-muted-foreground">{result.message}</p>
                </div>

                {result.computedHash && (
                  <div className="space-y-3 rounded-lg bg-muted/50 p-4">
                    <div className="space-y-1">
                      <p className="text-xs text-muted-foreground">계산된 해시</p>
                      <div className="flex items-center gap-2">
                        <code className="flex-1 break-all rounded bg-background px-2 py-1 font-mono text-xs">
                          {result.computedHash}
                        </code>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 shrink-0"
                          onClick={() => copyToClipboard(result.computedHash)}
                        >
                          <Copy className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                    <div className="space-y-1">
                      <p className="text-xs text-muted-foreground">온체인 해시</p>
                      <div className="flex items-center gap-2">
                        <code className="flex-1 break-all rounded bg-background px-2 py-1 font-mono text-xs">
                          {result.onChainHash}
                        </code>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 shrink-0"
                          onClick={() => copyToClipboard(result.onChainHash)}
                        >
                          <Copy className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
