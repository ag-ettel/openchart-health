"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

interface CompareTarget {
  ccn: string;
  name: string;
  providerType: string;
}

const CompareCtx = createContext<{
  target: CompareTarget | null;
  setTarget: (t: CompareTarget | null) => void;
}>({ target: null, setTarget: () => {} });

export function CompareProvider({ children }: { children: ReactNode }) {
  const [target, setTarget] = useState<CompareTarget | null>(null);
  return (
    <CompareCtx.Provider value={{ target, setTarget }}>
      {children}
    </CompareCtx.Provider>
  );
}

export function useCompareTarget() {
  return useContext(CompareCtx);
}

/**
 * Drop this into a server-component page to register the current provider
 * as the compare target. It sets context on mount and clears on unmount.
 */
export function SetCompareTarget({ ccn, name, providerType }: CompareTarget) {
  const { setTarget } = useCompareTarget();
  useEffect(() => {
    setTarget({ ccn, name, providerType });
    return () => setTarget(null);
  }, [ccn, name, providerType, setTarget]);
  return null;
}
