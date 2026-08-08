import { useState } from "react";
import { Flame, Loader2, Save, Target, Trophy } from "lucide-react";
import { api, ApiError } from "../api/client";

/**
 * Tela de perfil: estatísticas do usuário e edição de nome/meta diária.
 */
export default function ProfilePage({ user, onUserChange }) {
  const [fullName, setFullName] = useState(user.full_name);
  const [dailyGoal, setDailyGoal] = useState(user.daily_goal);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);

  const handleSave = async (e) => {
    e.preventDefault();
    if (saving) return;
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      const updated = await api.users.updateMe({
        full_name: fullName,
        daily_goal: Number(dailyGoal),
      });
      onUserChange(updated);
      setMessage("Perfil atualizado com sucesso.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao salvar as alterações.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100">Meu perfil</h2>

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard icon={<Flame className="h-5 w-5 text-orange-500" />} label="Sequência atual" value={`${user.current_streak} dias`} />
        <StatCard icon={<Trophy className="h-5 w-5 text-amber-500" />} label="XP total" value={user.total_xp} />
        <StatCard icon={<Target className="h-5 w-5 text-brand-600" />} label="Maior sequência" value={`${user.longest_streak} dias`} />
      </section>

      <form
        onSubmit={handleSave}
        className="space-y-4 rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900"
      >
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">
            Nome completo
          </label>
          <input
            type="text"
            required
            minLength={2}
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 focus:border-brand-500 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
          />
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">
            Meta diária de questões
          </label>
          <input
            type="number"
            required
            min={1}
            max={500}
            value={dailyGoal}
            onChange={(e) => setDailyGoal(e.target.value)}
            className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 focus:border-brand-500 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
          />
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">
            E-mail
          </label>
          <input
            type="email"
            disabled
            value={user.email}
            className="w-full cursor-not-allowed rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-500 dark:border-slate-700 dark:bg-slate-800/50 dark:text-slate-400"
          />
        </div>

        {message && <p className="text-sm text-emerald-600 dark:text-emerald-400">{message}</p>}
        {error && <p className="text-sm text-rose-600 dark:text-rose-400">{error}</p>}

        <button
          type="submit"
          disabled={saving}
          className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
          Salvar alterações
        </button>
      </form>
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
