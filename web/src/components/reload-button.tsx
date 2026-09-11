"use client";

import { Button } from "./Button";

export function ReloadButton({ label }: { label: string }) {
  return <Button onClick={() => window.location.reload()}>{label}</Button>;
}