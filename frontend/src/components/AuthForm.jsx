import { useState } from "react";
import { Loader2, LogIn, UserPlus } from "lucide-react";
import { api, ApiError } from "../api/client";

/**
 * Formulário de login/cadastro. Alterna entre os dois modos e, ao autenticar
 * com sucesso, chama `onAuthenticated(user)` para o App trocar de tela.
 */
export default function AuthForm({ onAuthenticated }) {
  const [mode, setMode] = useState("login"); // "login" | "register"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const isRegister = mode === "register";

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    setError(null);

    try {
      if (isRegister) {
        await api.auth.register({ email, password, full_name: fullName });
      }
      await api.auth.login({ email, password });
      const user = await api.auth.me();
      onAuthenticated(user);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao autenticar. Tente novamente.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto flex min-h-[70vh] max-w-sm flex-col justify-center px-6">
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="mb-1 text-lg font-semibold text-slate-800">
          {isRegister ? "Criar conta" : "Entrar"}
        </h2>
        <p className="mb-5 text-sm text-slate-500">
          {isRegister
            ? "Cadastre-se para acompanhar seu progresso, XP e sequência de estudos."
            : "Entre para responder questões e acompanhar seu desempenho."}
        </p>

        <form onSubmit={handleSubmit} className="space-y-3">
          {isRegister && (
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600">Nome completo</label>
              <input
                type="text"
                required
                minLength={2}
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
              />
            </div>
          )}

          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600">E-mail</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600">Senha</label>
            <input
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
            />
            {isRegister && (
              <p className="mt-1 text-xs text-slate-400">
                Mínimo 8 caracteres, com ao menos 1 letra maiúscula e 1 número.
              </p>
            )}
          </div>

          {error && <p className="text-sm text-rose-600">{error}</p>}

          <button
            type="submit"
            disabled={submitting}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {submitting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : isRegister ? (
              <UserPlus className="h-4 w-4" />
            ) : (
              <LogIn className="h-4 w-4" />
            )}
            {isRegister ? "Criar conta" : "Entrar"}
          </button>
        </form>

        <button
          type="button"
          onClick={() => {
            setMode(isRegister ? "login" : "register");
            setError(null);
          }}
          className="mt-4 w-full text-center text-xs text-slate-500 hover:text-brand-600"
        >
          {isRegister ? "Já tem conta? Entrar" : "Não tem conta? Cadastre-se"}
        </button>
      </div>
    </div>
  );
}
