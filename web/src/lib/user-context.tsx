"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { getMe } from "@/lib/auth-client";
import type { Me } from "@/lib/types";

type UserState = {
  user: Me | null;
  ready: boolean;
  refresh: () => Promise<void>;
  setUser: (user: Me | null) => void;
};

const UserContext = createContext<UserState | null>(null);

export function UserProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Me | null>(null);
  const [ready, setReady] = useState(false);

  const refresh = useCallback(
    () =>
      getMe().then(
        (me) => setUser(me),
        () => setUser(null), // 401 (anonymous) or API unreachable — stay signed out
      ).finally(() => setReady(true)),
    [],
  );

  useEffect(() => {
    let active = true;
    getMe().then(
      (me) => {
        if (active) setUser(me);
      },
      () => {
        if (active) setUser(null);
      },
    ).finally(() => {
      if (active) setReady(true);
    });
    return () => {
      active = false;
    };
  }, []);

  const value = useMemo(
    () => ({ user, ready, refresh, setUser }),
    [user, ready, refresh],
  );
  return <UserContext.Provider value={value}>{children}</UserContext.Provider>;
}

export function useUser(): UserState {
  const ctx = useContext(UserContext);
  if (!ctx) throw new Error("useUser must be used inside <UserProvider>");
  return ctx;
}