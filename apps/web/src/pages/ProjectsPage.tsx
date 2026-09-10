import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { api, describeApiError } from "../api/client";
import type { ProjectSummary } from "../api/types";
import { EmptyState } from "../components/common/EmptyState";
import { ErrorBanner } from "../components/common/ErrorBanner";
import { LoadingState } from "../components/common/LoadingState";
import { useUIStore } from "../state/uiStore";

const SAMPLE_PROJECT_NAME = "Örnek Proje — Synova Reklamı";

function formatDate(value: string | null | undefined): string {
  if (!value) return "Henüz yok";
  try {
    return new Date(value).toLocaleString("tr-TR");
  } catch {
    return value;
  }
}

export function ProjectsPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const setActiveProjectId = useUIStore((state) => state.setActiveProjectId);

  const [newProjectName, setNewProjectName] = useState("");
  const [showNewProjectForm, setShowNewProjectForm] = useState(false);

  const projectsQuery = useQuery({
    queryKey: ["projects"],
    queryFn: api.listProjects,
  });

  const createProject = useMutation({
    mutationFn: api.createProject,
    onSuccess: (project) => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      setActiveProjectId(project.id);
      setShowNewProjectForm(false);
      setNewProjectName("");
      navigate("/studyo/brief");
    },
  });

  const openFolder = useMutation({
    mutationFn: (id: string) => api.openProjectFolder(id),
  });

  function handleCreateSubmit(event: FormEvent) {
    event.preventDefault();
    if (!newProjectName.trim()) return;
    createProject.mutate({ name: newProjectName.trim(), locale: "tr" });
  }

  function handleCreateSample() {
    createProject.mutate({ name: SAMPLE_PROJECT_NAME, locale: "tr" });
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-100">Projeler</h1>
          <p className="text-sm text-slate-400">
            Yerel reklam projelerinizi buradan yönetin.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowNewProjectForm((v) => !v)}
          className="rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white transition hover:bg-accent/90"
        >
          Yeni proje
        </button>
      </div>

      {showNewProjectForm ? (
        <form
          onSubmit={handleCreateSubmit}
          className="flex flex-col gap-3 rounded-lg border border-slate-700 bg-surface/60 p-4 sm:flex-row sm:items-end"
        >
          <div className="flex-1">
            <label htmlFor="new-project-name" className="mb-1 block text-sm text-slate-300">
              Proje adı
            </label>
            <input
              id="new-project-name"
              type="text"
              value={newProjectName}
              onChange={(event) => setNewProjectName(event.target.value)}
              placeholder="ör. Synova Reklamı"
              className="w-full rounded-md border border-slate-600 bg-bg px-3 py-2 text-sm text-slate-100 outline-none focus:border-accent"
            />
          </div>
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={createProject.isPending || !newProjectName.trim()}
              className="rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white transition hover:bg-accent/90 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {createProject.isPending ? "Oluşturuluyor…" : "Oluştur"}
            </button>
            <button
              type="button"
              onClick={() => setShowNewProjectForm(false)}
              className="rounded-md border border-slate-600 px-4 py-2 text-sm text-slate-300 transition hover:bg-slate-800"
            >
              Vazgeç
            </button>
          </div>
        </form>
      ) : null}

      {createProject.isError ? (
        <ErrorBanner
          title="Proje oluşturulamadı"
          message={`Kaydedilemedi: ${describeApiError(createProject.error)}`}
          onRetry={() => createProject.reset()}
        />
      ) : null}

      {projectsQuery.isLoading ? <LoadingState label="Projeler yükleniyor…" /> : null}

      {projectsQuery.isError ? (
        <ErrorBanner
          title="Projeler alınamadı"
          message={describeApiError(projectsQuery.error)}
          onRetry={() => projectsQuery.refetch()}
          retrying={projectsQuery.isFetching}
        />
      ) : null}

      {projectsQuery.isSuccess && projectsQuery.data.length === 0 ? (
        <EmptyState
          title="Henüz projeniz yok"
          description="Sıfırdan başlayabilir veya Synova örneğiyle uçtan uca akışı deneyebilirsiniz. Bu, gerçek bir kullanıcı projesi değildir — üzerinde çalışmaya devam edeceğiniz bir başlangıç noktasıdır."
          action={
            <button
              type="button"
              onClick={handleCreateSample}
              disabled={createProject.isPending}
              className="rounded-md border border-accent px-4 py-2 text-sm font-semibold text-accent transition hover:bg-accent/10 disabled:cursor-not-allowed disabled:opacity-60"
            >
              Örnek proje oluştur
            </button>
          }
        />
      ) : null}

      {projectsQuery.isSuccess && projectsQuery.data.length > 0 ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projectsQuery.data.map((project) => (
            <ProjectCard
              key={project.id}
              project={project}
              onOpen={() => {
                setActiveProjectId(project.id);
                navigate("/studyo/brief");
              }}
              onOpenFolder={() => openFolder.mutate(project.id)}
              folderError={
                openFolder.isError && openFolder.variables === project.id
                  ? describeApiError(openFolder.error)
                  : null
              }
              folderPending={openFolder.isPending && openFolder.variables === project.id}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}

interface ProjectCardProps {
  project: ProjectSummary;
  onOpen: () => void;
  onOpenFolder: () => void;
  folderError: string | null;
  folderPending: boolean;
}

function ProjectCard({ project, onOpen, onOpenFolder, folderError, folderPending }: ProjectCardProps) {
  return (
    <div className="flex flex-col gap-3 rounded-lg border border-slate-700 bg-surface/60 p-4">
      <div>
        <h2 className="text-base font-semibold text-slate-100">{project.name}</h2>
        <p className="text-xs text-slate-500">{project.slug}</p>
      </div>
      <dl className="grid grid-cols-2 gap-x-2 gap-y-1 text-xs text-slate-400">
        <dt>Son güncelleme</dt>
        <dd className="text-slate-300">{formatDate(project.updated_at)}</dd>
        <dt>Son çıktı</dt>
        <dd className="text-slate-300">{formatDate(project.last_export_at)}</dd>
        <dt>Son açılma</dt>
        <dd className="text-slate-300">{formatDate(project.last_opened_at)}</dd>
      </dl>
      <div className="mt-1 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={onOpen}
          className="rounded-md bg-accent px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-accent/90"
        >
          Stüdyoda aç
        </button>
        <button
          type="button"
          onClick={onOpenFolder}
          disabled={folderPending}
          className="rounded-md border border-slate-600 px-3 py-1.5 text-xs text-slate-300 transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {folderPending ? "Açılıyor…" : "Klasörde göster"}
        </button>
      </div>
      {folderError ? <p className="text-xs text-error">Klasör açılamadı: {folderError}</p> : null}
    </div>
  );
}
