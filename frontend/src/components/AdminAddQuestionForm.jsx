import { useState } from "react";
import { CheckCircle2, Loader2, Plus, Trash2, UploadCloud } from "lucide-react";
import { api, ApiError } from "../api/client";

const DIFFICULTY_OPTIONS = [
  { value: "", label: "Classificar automaticamente" },
  { value: "EASY", label: "Fácil" },
  { value: "MEDIUM", label: "Médio" },
  { value: "HARD", label: "Difícil" },
];

const INPUT_CLASSES =
  "w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 focus:border-brand-500 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100";
const LABEL_CLASSES = "mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300";

function emptyOption(letter) {
  return { letter, text: "" };
}

/**
 * Painel admin para cadastrar uma questão manualmente pela interface,
 * chamando o mesmo POST /questions/batch usado por integrações/scripts —
 * um único item na lista. Acesso restrito a usuários com is_admin=true
 * (ver Sidebar.jsx / App.jsx).
 */
export default function AdminAddQuestionForm() {
  const [content, setContent] = useState("");
  const [options, setOptions] = useState([emptyOption("A"), emptyOption("B")]);
  const [correctOption, setCorrectOption] = useState("A");
  const [boardName, setBoardName] = useState("");
  const [subjectName, setSubjectName] = useState("");
  const [organization, setOrganization] = useState("");
  const [role, setRole] = useState("");
  const [year, setYear] = useState(new Date().getFullYear());
  const [stateUf, setStateUf] = useState("");
  const [difficultyLevel, setDifficultyLevel] = useState("");

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const addOption = () => {
    if (options.length >= 5) return;
    const nextLetter = String.fromCharCode(65 + options.length); // A,B,C,D,E
    setOptions((prev) => [...prev, emptyOption(nextLetter)]);
  };

  const removeOption = (letter) => {
    if (options.length <= 2) return;
    setOptions((prev) => prev.filter((o) => o.letter !== letter));
    if (correctOption === letter) setCorrectOption(options[0].letter);
  };

  const updateOptionText = (letter, text) => {
    setOptions((prev) => prev.map((o) => (o.letter === letter ? { ...o, text } : o)));
  };

  const resetForm = () => {
    setContent("");
    setOptions([emptyOption("A"), emptyOption("B")]);
    setCorrectOption("A");
    setBoardName("");
    setSubjectName("");
    setOrganization("");
    setRole("");
    setYear(new Date().getFullYear());
    setStateUf("");
    setDifficultyLevel("");
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    setError(null);
    setResult(null);

    const optionsMap = Object.fromEntries(
      options.filter((o) => o.text.trim()).map((o) => [o.letter, o.text.trim()])
    );

    const item = {
      content: content.trim(),
      options: optionsMap,
      correct_option: correctOption,
      board_name: boardName.trim(),
      subject_name: subjectName.trim(),
      organization: organization.trim(),
      role: role.trim() || null,
      year: Number(year),
      state_uf: stateUf.trim() || null,
      difficulty_level: difficultyLevel || null,
    };

    try {
      const data = await api.questions.batch([item]);
      setResult(data);
      if (data.inserted > 0) resetForm();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao cadastrar a questão.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <div className="flex items-center gap-2">
        <UploadCloud className="h-5 w-5 text-brand-600" />
        <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100">
          Cadastrar nova questão
        </h2>
      </div>

      <form
        onSubmit={handleSubmit}
        className="space-y-4 rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900"
      >
        <div>
          <label className={LABEL_CLASSES}>Enunciado</label>
          <textarea
            required
            rows={4}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            className={INPUT_CLASSES}
          />
        </div>

        <div>
          <label className={LABEL_CLASSES}>Alternativas</label>
          <div className="space-y-2">
            {options.map((opt) => (
              <div key={opt.letter} className="flex items-center gap-2">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-slate-200 text-xs font-semibold text-slate-600 dark:border-slate-700 dark:text-slate-300">
                  {opt.letter}
                </span>
                <input
                  type="text"
                  required
                  value={opt.text}
                  onChange={(e) => updateOptionText(opt.letter, e.target.value)}
                  className={INPUT_CLASSES}
                />
                {options.length > 2 && (
                  <button
                    type="button"
                    onClick={() => removeOption(opt.letter)}
                    className="shrink-0 text-slate-400 hover:text-rose-600 dark:hover:text-rose-400"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                )}
              </div>
            ))}
          </div>
          {options.length < 5 && (
            <button
              type="button"
              onClick={addOption}
              className="mt-2 inline-flex items-center gap-1.5 text-xs font-medium text-brand-600 hover:text-brand-700 dark:text-brand-400"
            >
              <Plus className="h-3.5 w-3.5" /> Adicionar alternativa
            </button>
          )}
        </div>

        <div>
          <label className={LABEL_CLASSES}>Alternativa correta</label>
          <select
            value={correctOption}
            onChange={(e) => setCorrectOption(e.target.value)}
            className={INPUT_CLASSES}
          >
            {options.map((o) => (
              <option key={o.letter} value={o.letter}>
                {o.letter}
              </option>
            ))}
          </select>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className={LABEL_CLASSES}>Banca</label>
            <input
              type="text"
              required
              placeholder="Ex.: CEBRASPE"
              value={boardName}
              onChange={(e) => setBoardName(e.target.value)}
              className={INPUT_CLASSES}
            />
          </div>
          <div>
            <label className={LABEL_CLASSES}>Matéria</label>
            <input
              type="text"
              required
              placeholder="Ex.: Direito Constitucional"
              value={subjectName}
              onChange={(e) => setSubjectName(e.target.value)}
              className={INPUT_CLASSES}
            />
          </div>
          <div>
            <label className={LABEL_CLASSES}>Órgão/Concurso</label>
            <input
              type="text"
              required
              value={organization}
              onChange={(e) => setOrganization(e.target.value)}
              className={INPUT_CLASSES}
            />
          </div>
          <div>
            <label className={LABEL_CLASSES}>Cargo (opcional)</label>
            <input
              type="text"
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className={INPUT_CLASSES}
            />
          </div>
          <div>
            <label className={LABEL_CLASSES}>Ano</label>
            <input
              type="number"
              required
              min={1990}
              max={2100}
              value={year}
              onChange={(e) => setYear(e.target.value)}
              className={INPUT_CLASSES}
            />
          </div>
          <div>
            <label className={LABEL_CLASSES}>UF (opcional)</label>
            <input
              type="text"
              maxLength={2}
              placeholder="Ex.: SP ou BR (federal)"
              value={stateUf}
              onChange={(e) => setStateUf(e.target.value.toUpperCase())}
              className={INPUT_CLASSES}
            />
          </div>
        </div>

        <div>
          <label className={LABEL_CLASSES}>Dificuldade</label>
          <select
            value={difficultyLevel}
            onChange={(e) => setDifficultyLevel(e.target.value)}
            className={INPUT_CLASSES}
          >
            {DIFFICULTY_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {result && (
          <div className="flex items-start gap-2 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300">
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
            <span>
              {result.inserted > 0
                ? "Questão cadastrada com sucesso."
                : result.duplicates > 0
                ? "Essa questão já existe no banco (duplicata ignorada)."
                : "Nenhuma questão foi inserida — confira banca/matéria/órgão."}
            </span>
          </div>
        )}
        {error && <p className="text-sm text-rose-600 dark:text-rose-400">{error}</p>}

        <button
          type="submit"
          disabled={submitting}
          className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
          Cadastrar questão
        </button>
      </form>
    </div>
  );
}
