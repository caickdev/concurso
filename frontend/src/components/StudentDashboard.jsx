import { useEffect, useMemo, useState } from "react";
import { ChevronDown, Flame, ListFilter, Loader2, Target, Trophy } from "lucide-react";
import { api } from "../api/client";
import QuestionCard from "./QuestionCard.jsx";

const DIFFICULTY_OPTIONS = [
  { value: "", label: "Todas as dificuldades" },
  { value: "EASY", label: "Fácil" },
  { value: "MEDIUM", label: "Médio" },
  { value: "HARD", label: "Difícil" },
];

const SELECT_CLASSES =
  "rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 focus:border-brand-500 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100";

/**
 * Painel principal do aluno: estatísticas de gamificação, filtros avançados
 * de questões (matéria, banca, ano, dificuldade) e a lista de questões
 * filtradas/paginadas.
 */
export default function StudentDashboard({ user, onUserChange }) {
  const [leaderboard, setLeaderboard] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [boards, setBoards] = useState([]);

  const [filters, setFilters] = useState({
    subject_id: "",
    board_id: "",
    year: "",
    difficulty_level: "",
    page: 1,
    page_size: 10,
  });

  const [questionPage, setQuestionPage] = useState(null);
  const [loadingQuestions, setLoadingQuestions] = useState(true);
  const [error, setError] = useState(null);
  const [filtersOpen, setFiltersOpen] = useState(false);

  useEffect(() => {
    api.leaderboard.get(5).then(setLeaderboard).catch(() => setLeaderboard([]));
    api.taxonomy.subjects().then(setSubjects).catch(() => setSubjects([]));
    api.taxonomy.boards().then(setBoards).catch(() => setBoards([]));
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoadingQuestions(true);
    setError(null);

    api.questions
      .filter(filters)
      .then((data) => {
        if (!cancelled) setQuestionPage(data);
      })
      .catch(() => {
        if (!cancelled) setError("Não foi possível carregar as questões.");
      })
      .finally(() => {
        if (!cancelled) setLoadingQuestions(false);
      });

    return () => {
      cancelled = true;
    };
  }, [filters]);

  const dailyGoalProgress = useMemo(() => {
    if (!user) return 0;
    // Placeholder: em produção viria de um endpoint de progresso diário dedicado.
    return Math.min(100, Math.round((user.current_streak / Math.max(user.daily_goal, 1)) * 100));
  }, [user]);

  const updateFilter = (key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value, page: 1 }));
  };

  const handleAnswered = (result) => {
    onUserChange((prev) =>
      prev ? { ...prev, total_xp: result.total_xp, current_streak: result.current_streak } : prev
    );
  };

  const handleAddToNotebook = async (questionId) => {
    try {
      await api.users.addToNotebook({ question_id: questionId });
    } catch {
      // Falha silenciosa aqui é aceitável: a ação principal (responder) já foi concluída.
    }
  };

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6">
      <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard
          icon={<Flame className="h-5 w-5 text-orange-500" />}
          label="Sequência atual"
          value={user ? `${user.current_streak} dias` : "—"}
        />
        <StatCard
          icon={<Trophy className="h-5 w-5 text-amber-500" />}
          label="XP total"
          value={user ? user.total_xp : "—"}
        />
        <StatCard
          icon={<Target className="h-5 w-5 text-brand-600" />}
          label="Meta diária"
          value={user ? `${user.daily_goal} questões (${dailyGoalProgress}%)` : "—"}
        />
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
        <button
          type="button"
          onClick={() => setFiltersOpen((prev) => !prev)}
          className="flex w-full items-center justify-between gap-2 text-sm font-medium text-slate-700 dark:text-slate-200 md:pointer-events-none"
        >
          <span className="flex items-center gap-2">
            <ListFilter className="h-4 w-4" /> Filtros
          </span>
          <ChevronDown
            className={`h-4 w-4 shrink-0 transition-transform md:hidden ${filtersOpen ? "rotate-180" : ""}`}
          />
        </button>
        <div className={`mt-3 grid-cols-2 gap-3 sm:grid-cols-4 md:grid ${filtersOpen ? "grid" : "hidden"}`}>
          <select
            value={filters.subject_id}
            onChange={(e) => updateFilter("subject_id", e.target.value)}
            className={SELECT_CLASSES}
          >
            <option value="">Todas as matérias</option>
            {subjects.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
          <select
            value={filters.board_id}
            onChange={(e) => updateFilter("board_id", e.target.value)}
            className={SELECT_CLASSES}
          >
            <option value="">Todas as bancas</option>
            {boards.map((b) => (
              <option key={b.id} value={b.id}>
                {b.name}
              </option>
            ))}
          </select>
          <input
            type="number"
            placeholder="Ano"
            value={filters.year}
            onChange={(e) => updateFilter("year", e.target.value)}
            className={SELECT_CLASSES}
          />
          <select
            value={filters.difficulty_level}
            onChange={(e) => updateFilter("difficulty_level", e.target.value)}
            className={SELECT_CLASSES}
          >
            {DIFFICULTY_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      </section>

      <section className="space-y-4">
        {loadingQuestions && (
          <div className="flex items-center justify-center gap-2 py-10 text-slate-500 dark:text-slate-400">
            <Loader2 className="h-5 w-5 animate-spin" /> Carregando questões...
          </div>
        )}
        {error && <p className="text-sm text-rose-600 dark:text-rose-400">{error}</p>}
        {!loadingQuestions &&
          questionPage?.items?.map((question) => (
            <QuestionCard
              key={question.id}
              question={question}
              onAnswered={handleAnswered}
              onAddToNotebook={handleAddToNotebook}
            />
          ))}
        {!loadingQuestions && questionPage?.items?.length === 0 && (
          <p className="py-10 text-center text-sm text-slate-500 dark:text-slate-400">
            Nenhuma questão encontrada para os filtros selecionados.
          </p>
        )}
      </section>

      {questionPage && questionPage.total_pages > 1 && (
        <div className="flex justify-center gap-2">
          <button
            disabled={filters.page <= 1}
            onClick={() => setFilters((prev) => ({ ...prev, page: prev.page - 1 }))}
            className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-700 disabled:opacity-40 dark:border-slate-700 dark:text-slate-200"
          >
            Anterior
          </button>
          <span className="px-2 py-1.5 text-sm text-slate-500 dark:text-slate-400">
            Página {filters.page} de {questionPage.total_pages}
          </span>
          <button
            disabled={filters.page >= questionPage.total_pages}
            onClick={() => setFilters((prev) => ({ ...prev, page: prev.page + 1 }))}
            className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-700 disabled:opacity-40 dark:border-slate-700 dark:text-slate-200"
          >
            Próxima
          </button>
        </div>
      )}

      <section className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
        <div className="mb-3 flex items-center gap-2 text-sm font-medium text-slate-700 dark:text-slate-200">
          <Trophy className="h-4 w-4 text-amber-500" /> Ranking
        </div>
        <ol className="space-y-1.5 text-sm">
          {leaderboard.map((entry) => (
            <li key={entry.user_id} className="flex justify-between text-slate-600 dark:text-slate-300">
              <span>
                {entry.rank}. {entry.full_name}
              </span>
              <span className="font-medium text-slate-800 dark:text-slate-100">{entry.total_xp} XP</span>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}

function StatCard({ icon, label, value }) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
      <div className="rounded-lg bg-slate-50 p-2 dark:bg-slate-800">{icon}</div>
      <div>
        <p className="text-xs text-slate-500 dark:text-slate-400">{label}</p>
        <p className="text-lg font-semibold text-slate-800 dark:text-slate-100">{value}</p>
      </div>
    </div>
  );
}
