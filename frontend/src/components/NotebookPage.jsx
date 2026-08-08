import { useEffect, useState } from "react";
import { BookMarked, Loader2, Trash2 } from "lucide-react";
import { api, ApiError } from "../api/client";

const STATUS_LABELS = {
  PENDING_REVIEW: "Pendente de revisão",
  REVIEWED: "Revisada",
  MASTERED: "Dominada",
};

/**
 * Caderno de Erros: questões que o aluno marcou para revisar depois, com
 * anotações pessoais e status de progresso.
 */
export default function NotebookPage() {
  const [items, setItems] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = () => {
    setLoading(true);
    api.users
      .listNotebook()
      .then(setItems)
      .catch(() => setError("Não foi possível carregar o caderno de erros."))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const handleStatusChange = async (itemId, status) => {
    try {
      const updated = await api.users.updateNotebookItem(itemId, { status });
      setItems((prev) => prev.map((it) => (it.id === itemId ? updated : it)));
    } catch {
      // Falha ao atualizar status é silenciosa — o usuário pode tentar de novo.
    }
  };

  const handleNotesBlur = async (itemId, personal_notes) => {
    try {
      const updated = await api.users.updateNotebookItem(itemId, { personal_notes });
      setItems((prev) => prev.map((it) => (it.id === itemId ? updated : it)));
    } catch {
      // Idem — anotação continua editável, só não persistiu desta vez.
    }
  };

  const handleRemove = async (itemId) => {
    try {
      await api.users.removeFromNotebook(itemId);
      setItems((prev) => prev.filter((it) => it.id !== itemId));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao remover item.");
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-4 p-6">
      <div className="flex items-center gap-2">
        <BookMarked className="h-5 w-5 text-brand-600" />
        <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100">Caderno de Erros</h2>
      </div>

      {loading && (
        <div className="flex items-center justify-center gap-2 py-10 text-slate-500 dark:text-slate-400">
          <Loader2 className="h-5 w-5 animate-spin" /> Carregando...
        </div>
      )}
      {error && <p className="text-sm text-rose-600 dark:text-rose-400">{error}</p>}

      {!loading && items?.length === 0 && (
        <p className="py-10 text-center text-sm text-slate-500 dark:text-slate-400">
          Nenhuma questão salva ainda. Marque questões que errar como "Caderno de erros" para
          revisá-las aqui depois.
        </p>
      )}

      {items?.map((item) => (
        <article
          key={item.id}
          className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900"
        >
          <div className="mb-2 flex flex-wrap items-center gap-2 text-xs">
            <span className="rounded-full bg-brand-50 px-2.5 py-1 font-medium text-brand-700 dark:bg-brand-700/20 dark:text-brand-300">
              {item.question.board?.name}
            </span>
            <span className="rounded-full bg-slate-100 px-2.5 py-1 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
              {item.question.subject?.name}
            </span>
          </div>

          <p className="mb-3 text-sm text-slate-800 dark:text-slate-100">{item.question.content}</p>

          <div className="mb-3 flex items-center gap-2">
            <label className="text-xs text-slate-500 dark:text-slate-400">Status:</label>
            <select
              value={item.status}
              onChange={(e) => handleStatusChange(item.id, e.target.value)}
              className="rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs text-slate-700 focus:border-brand-500 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
            >
              {Object.entries(STATUS_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>

          <textarea
            defaultValue={item.personal_notes ?? ""}
            placeholder="Suas anotações sobre essa questão..."
            onBlur={(e) => handleNotesBlur(item.id, e.target.value)}
            rows={2}
            className="mb-3 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 focus:border-brand-500 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
          />

          <button
            type="button"
            onClick={() => handleRemove(item.id)}
            className="inline-flex items-center gap-1.5 text-xs font-medium text-rose-600 hover:text-rose-700 dark:text-rose-400"
          >
            <Trash2 className="h-3.5 w-3.5" /> Remover do caderno
          </button>
        </article>
      ))}
    </div>
  );
}
