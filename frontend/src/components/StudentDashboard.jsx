import { useEffect, useMemo, useRef, useState } from "react";
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

// Tempo que a questão recém-respondida continua visível na aba "Não
// respondidas" (mostrando se acertou ou errou) antes de sumir de lá — ela já
// aparece na aba "Respondidas" desde o primeiro instante.
const ANSWER_TRANSITION_MS = 2500;

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
  const [answeredResults, setAnsweredResults] = useState({});
  const [transitioningIds, setTransitioningIds] = useState(() => new Set());
  const [activeTab, setActiveTab] = useState("pending");
  const transitionTimeouts = useRef(new Map());

  useEffect(() => {
    const timeouts = transitionTimeouts.current;
    return () => {
      timeouts.forEach(clearTimeout);
      timeouts.clear();
    };
  }, []);

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
    const questionId = result.question_id;
    setAnsweredResults((prev) => ({ ...prev, [questionId]: result }));
    onUserChange((prev) =>
      prev ? { ...prev, total_xp: result.total_xp, current_streak: result.current_streak } : prev
    );

    // Mantém a questão visível na aba "Não respondidas" por mais alguns
    // segundos — tempo suficiente para o usuário ver se acertou ou errou —
    // antes de sumir de lá (ela já passa a existir na aba "Respondidas"
    // imediatamente, então nunca fica invisível nas duas ao mesmo tempo).
    setTransitioningIds((prev) => new Set(prev).add(questionId));
    const existingTimeout = transitionTimeouts.current.get(questionId);
    if (existingTimeout) clearTimeout(existingTimeout);
    const timeoutId = setTimeout(() => {
      setTransitioningIds((prev) => {
        const next = new Set(prev);
        next.delete(questionId);
        return next;
      });
      transitionTimeouts.current.delete(questionId);
    }, ANSWER_TRANSITION_MS);
    transitionTimeouts.current.set(questionId, timeoutId);
  };

  const handleAddToNotebook = async (questionId) => {
    try {
      await api.users.addToNotebook({ question_id: questionId });
    } catch {
      // Falha silenciosa aqui é aceitável: a ação principal (responder) já foi concluída.
    }
  };

  // Contagens das abas refletem o estado real (não o transitório) para não
  // confundir o usuário com números que "voltam atrás".
  const answeredCount = questionPage?.items?.filter((q) => answeredResults[q.id]).length ?? 0;
  const pendingCount = (questionPage?.items?.length ?? 0) - answeredCount;

  // A lista da aba "Não respondidas" inclui, por mais alguns segundos, a
  // última questão respondida (para mostrar o gabarito antes de sumir); a
  // aba "Respondidas" já mostra a questão desde o primeiro instante.
  const pendingItems =
    questionPage?.items?.filter((q) => !answeredResults[q.id] || transitioningIds.has(q.id)) ?? [];
  const answeredItems = questionPage?.items?.filter((q) => answeredResults[q.id]) ?? [];
  const visibleItems = activeTab === "pending" ? pendingItems : answeredItems;

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
        {questionPage?.items?.length > 0 && (
          <div className="flex gap-2 border-b border-slate-200 dark:border-slate-800">
            <button
              type="button"
              onClick={() => setActiveTab("pending")}
              className={`flex items-center gap-1.5 border-b-2 px-3 py-2 text-sm font-medium transition-colors ${
                activeTab === "pending"
                  ? "border-brand-600 text-brand-700 dark:border-brand-400 dark:text-brand-300"
                  : "border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
              }`}
            >
              Não respondidas
              <span className="rounded-full bg-slate-100 px-1.5 py-0.5 text-xs text-slate-500 dark:bg-slate-800 dark:text-slate-400">
                {pendingCount}
              </span>
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("answered")}
              className={`flex items-center gap-1.5 border-b-2 px-3 py-2 text-sm font-medium transition-colors ${
                activeTab === "answered"
                  ? "border-brand-600 text-brand-700 dark:border-brand-400 dark:text-brand-300"
                  : "border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
              }`}
            >
              Respondidas
              <span className="rounded-full bg-slate-100 px-1.5 py-0.5 text-xs text-slate-500 dark:bg-slate-800 dark:text-slate-400">
                {answeredCount}
              </span>
            </button>
          </div>
        )}

        {loadingQuestions && (
          <div className="flex items-center justify-center gap-2 py-10 text-slate-500 dark:text-slate-400">
            <Loader2 className="h-5 w-5 animate-spin" /> Carregando questões...
          </div>
        )}
        {error && <p className="text-sm text-rose-600 dark:text-rose-400">{error}</p>}
        {!loadingQuestions &&
          visibleItems.map((question) => (
            <div key={question.id}>
              <QuestionCard
                question={question}
                initialResult={answeredResults[question.id]}
                onAnswered={handleAnswered}
                onAddToNotebook={handleAddToNotebook}
              />
              {activeTab === "pending" && transitioningIds.has(question.id) && (
                <p className="mt-1.5 text-right text-xs text-slate-400 dark:text-slate-500">
                  Movendo para a aba "Respondidas"...
                </p>
              )}
            </div>
          ))}
        {!loadingQuestions && questionPage?.items?.length === 0 && (
          <p className="py-10 text-center text-sm text-slate-500 dark:text-slate-400">
            Nenhuma questão encontrada para os filtros selecionados.
          </p>
        )}
        {!loadingQuestions && questionPage?.items?.length > 0 && visibleItems.length === 0 && (
          <p className="py-10 text-center text-sm text-slate-500 dark:text-slate-400">
            {activeTab === "pending"
              ? "Você já respondeu todas as questões desta página."
              : "Nenhuma questão respondida ainda nesta página."}
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
