import { useState } from "react";
import {
  BookmarkPlus,
  CheckCircle2,
  Loader2,
  MessageSquare,
  Sparkles,
  XCircle,
} from "lucide-react";
import { api, ApiError } from "../api/client";

const DIFFICULTY_STYLES = {
  EASY: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300",
  MEDIUM: "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300",
  HARD: "bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300",
};

const DIFFICULTY_LABELS = {
  EASY: "Fácil",
  MEDIUM: "Médio",
  HARD: "Difícil",
};

/**
 * Cartão de questão: exibe enunciado + alternativas, permite responder (com
 * modo Cebraspe opcional), mostra o resultado e oferece explicação via Tutor IA.
 */
export default function QuestionCard({ question, onAnswered, onAddToNotebook }) {
  const [selectedOption, setSelectedOption] = useState(null);
  const [cebraspeMode, setCebraspeMode] = useState(false);
  const [result, setResult] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const [explanation, setExplanation] = useState(null);
  const [loadingExplanation, setLoadingExplanation] = useState(false);

  const handleSubmit = async () => {
    if (!selectedOption || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      const data = await api.questions.submitAnswer(question.id, {
        selected_option: selectedOption,
        is_cebraspe_mode: cebraspeMode,
      });
      setResult(data);
      onAnswered?.(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao enviar resposta.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleExplainAI = async () => {
    if (loadingExplanation) return;
    setLoadingExplanation(true);
    setError(null);
    try {
      const data = await api.questions.explainAI(question.id, {
        user_selected_option: selectedOption,
      });
      setExplanation(data.explanation_markdown);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao gerar explicação.");
    } finally {
      setLoadingExplanation(false);
    }
  };

  const answered = result !== null;

  return (
    <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <header className="mb-4 flex flex-wrap items-center gap-2 text-xs">
        <span className="rounded-full bg-brand-50 px-2.5 py-1 font-medium text-brand-700 dark:bg-brand-700/20 dark:text-brand-300">
          {question.board?.name}
        </span>
        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
          {question.subject?.name}
        </span>
        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
          {question.exam?.organization} · {question.year}
        </span>
        <span
          className={`rounded-full px-2.5 py-1 font-medium ${DIFFICULTY_STYLES[question.difficulty_level]}`}
        >
          {DIFFICULTY_LABELS[question.difficulty_level]}
        </span>
      </header>

      <p className="mb-4 whitespace-pre-line text-sm leading-relaxed text-slate-800 dark:text-slate-100">
        {question.content}
      </p>

      <div className="mb-4 space-y-2">
        {Object.entries(question.options).map(([letter, text]) => {
          const isSelected = selectedOption === letter;
          const isCorrect = answered && letter === result.correct_option;
          const isWrongSelected = answered && isSelected && !result.is_correct;

          let stateClasses = "border-slate-200 hover:border-brand-300 dark:border-slate-700 dark:hover:border-brand-500";
          if (answered && isCorrect) stateClasses = "border-emerald-400 bg-emerald-50 dark:border-emerald-600 dark:bg-emerald-900/30";
          else if (isWrongSelected) stateClasses = "border-rose-400 bg-rose-50 dark:border-rose-600 dark:bg-rose-900/30";
          else if (isSelected) stateClasses = "border-brand-500 bg-brand-50 dark:border-brand-500 dark:bg-brand-700/20";

          return (
            <button
              key={letter}
              type="button"
              disabled={answered || submitting}
              onClick={() => setSelectedOption(letter)}
              className={`flex w-full items-start gap-3 rounded-lg border px-3 py-2.5 text-left text-sm transition-colors disabled:cursor-default ${stateClasses}`}
            >
              <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-current text-xs font-semibold text-slate-500 dark:text-slate-300">
                {letter}
              </span>
              <span className="flex-1 text-slate-700 dark:text-slate-200">{text}</span>
              {answered && isCorrect && <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-600 dark:text-emerald-400" />}
              {isWrongSelected && <XCircle className="h-5 w-5 shrink-0 text-rose-600 dark:text-rose-400" />}
            </button>
          );
        })}
      </div>

      {error && <p className="mb-3 text-sm text-rose-600 dark:text-rose-400">{error}</p>}

      {!answered ? (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <label className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-300">
            <input
              type="checkbox"
              checked={cebraspeMode}
              onChange={(e) => setCebraspeMode(e.target.checked)}
              className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500 dark:border-slate-600"
            />
            Modo Cebraspe (1 erro anula 1 acerto)
          </label>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={!selectedOption || submitting}
            className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
            Responder
          </button>
        </div>
      ) : (
        <div className="space-y-3 border-t border-slate-100 pt-3 dark:border-slate-800">
          <div className="flex flex-wrap items-center gap-4 text-sm">
            <span className={result.is_correct ? "font-medium text-emerald-700 dark:text-emerald-400" : "font-medium text-rose-700 dark:text-rose-400"}>
              {result.is_correct ? "Você acertou!" : "Você errou."}
            </span>
            <span className="text-slate-500 dark:text-slate-400">XP: {result.xp_earned >= 0 ? "+" : ""}{result.xp_earned}</span>
            <span className="text-slate-500 dark:text-slate-400">Sequência: {result.current_streak} dias</span>
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => onAddToNotebook?.(question.id)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              <BookmarkPlus className="h-4 w-4" /> Caderno de erros
            </button>
            <button
              type="button"
              onClick={handleExplainAI}
              disabled={loadingExplanation}
              className="inline-flex items-center gap-1.5 rounded-lg border border-brand-200 px-3 py-1.5 text-xs font-medium text-brand-700 hover:bg-brand-50 disabled:opacity-50 dark:border-brand-700/40 dark:text-brand-300 dark:hover:bg-brand-700/10"
            >
              {loadingExplanation ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Sparkles className="h-4 w-4" />
              )}
              Explicar com IA
            </button>
            <span className="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium text-slate-500 dark:text-slate-400">
              <MessageSquare className="h-4 w-4" /> Comentários
            </span>
          </div>

          {explanation && (
            <div className="rounded-lg bg-slate-50 p-3 text-sm text-slate-700 dark:bg-slate-800 dark:text-slate-200">
              <pre className="whitespace-pre-wrap font-sans">{explanation}</pre>
            </div>
          )}
        </div>
      )}
    </article>
  );
}
