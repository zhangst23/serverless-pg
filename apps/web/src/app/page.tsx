"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { getApiKey } from "@/lib/api";
import { Spinner } from "@/components/ui";

export default function Home() {
  const router = useRouter();
  useEffect(() => {
    router.replace(getApiKey() ? "/dashboard" : "/login");
  }, [router]);
  return (
    <div className="grid h-screen place-items-center">
      <Spinner label="跳转中…" />
    </div>
  );
}
