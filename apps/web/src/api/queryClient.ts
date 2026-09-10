import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Otomatik yeniden deneme kapalı: TanStack Query varsayılan retry
      // davranışında, iki deneme arasındaki bekleme sekme arka plana
      // alındığında ("document.visibilityState === 'hidden'") süresiz
      // "paused" durumuna geçer ve kullanıcıya hiçbir zaman gerçek hata
      // göstermez — spec §2.3/§5.4'ün istediği "gerçek, anlık hata
      // durumu" ilkesiyle çelişir. Bunun yerine ilk hata hemen yüzeye
      // çıkar; kullanıcı ekranlardaki "Yeniden dene" düğmesiyle elle
      // tekrar dener.
      retry: 0,
      refetchOnWindowFocus: false,
      // Backend 127.0.0.1 üzerinde çalışır, yani genel internet
      // bağlantısından bağımsızdır. Varsayılan "online" ağ modu,
      // işletim sistemi kendini çevrimdışı sayarsa isteği hiç
      // denemeden bekletir; bu yüzden her zaman denenecek şekilde
      // ayarlanıyor — sonuç yine gerçek başarı/hata olarak kalır.
      networkMode: "always",
    },
    mutations: {
      retry: false,
      networkMode: "always",
    },
  },
});
