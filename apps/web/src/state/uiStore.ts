import { create } from "zustand";
import { persist } from "zustand/middleware";

/**
 * Yalnızca yerel UI tercihleri burada tutulur (spec §6.1: "UI veri erişimi
 * ... yerel seçimler için Zustand"). Sunucudan gelen veri (projeler,
 * brief, iş durumları vb.) TanStack Query içinde kalır, bu store'a
 * kopyalanmaz.
 */
interface UIState {
  /** Stüdyo ekranının şu an üzerinde çalıştığı proje. */
  activeProjectId: string | null;
  setActiveProjectId: (id: string | null) => void;

  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      activeProjectId: null,
      setActiveProjectId: (id) => set({ activeProjectId: id }),

      sidebarCollapsed: false,
      toggleSidebar: () =>
        set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
    }),
    {
      name: "lad-ui-preferences",
    },
  ),
);
