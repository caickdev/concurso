import { useState } from "react";
import { CheckCircle2, KeyRound, Loader2 } from "lucide-react";
import { api, ApiError } from "../api/client";

/**
 * Tela acessada via link de e-mail (`/?token=...`, ver App.jsx). Define uma
 * nova senha usando o token de redefinição.
 */
export default function ResetPasswordForm({ token, onDone }) {
  const [newPassword, setNewPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    setError(null);

    try {
      await api.auth.resetPassword({ token, new_password: newPassword });
      setSuccess(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao redefinir a senha.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto flex min-h-[70vh] max-w-sm flex-col justify-center px-6">
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <h2 className="mb-1 text-lg font-semibold text-slate-800 dark:text-slate-100">
          Redefinir senha
        </h2>

        {success ? (
          <div className="space-y-4">
            <p className="flex items-center gap-2 text-sm text-emerald-600 dark:text-emerald-400">
              <CheckCircle2 className="h-4 w-4" /> Senha redefinida com sucesso.
            </p>
            <button
              type="button"
              onClick={onDone}
              className="w-full rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-brand-700"
            >
              Ir para o login
            </button>
          </div>
        ) : (
          <>
            <p className="mb-5 text-sm text-slate-500 dark:text-slate-400">
              Escolha uma nova senha para sua conta.
            </p>
            <form onSubmit={handleSubmit} className="space-y-3">
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">
                  Nova senha
                </label>
                <input
                  type="password"
                  required
                  minLength={8}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 focus:border-brand-500 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
                />
                <p className="mt-1 text-xs text-slate-400 dark:text-slate-500">
                  Mínimo 8 caracteres, com ao menos 1 letra maiúscula e 1 número.
                </p>
              </div>

              {error && <p className="text-sm text-rose-600 dark:text-rose-400">{error}</p>}

              <button
                type="submit"
                disabled={submitting}
                className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <KeyRound className="h-4 w-4" />}
                Redefinir senha
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}
