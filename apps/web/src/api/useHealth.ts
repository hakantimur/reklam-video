import { useQuery } from "@tanstack/react-query";

import { api } from "./client";

/**
 * Backend bağlantı durumunu düzenli aralıklarla kontrol eder.
 * Sol menü/üst bar bağlantı rozetinde ve ekranların bağlantı durumu
 * göstergelerinde kullanılır (spec §5.4).
 */
export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: api.health,
    refetchInterval: 15_000,
    retry: 0,
  });
}
