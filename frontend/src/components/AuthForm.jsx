import { useState } from "react";
import { KeyRound, Loader2, LogIn, UserPlus } from "lucide-react";
import { api, ApiError } from "../api/client";

const INPUT_CLASSES =
  "w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 focus:border-brand-500 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100";
const LABEL_CLASSES = "mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300";

/**
 * Formulário de autenticação: login, cadastro e "esqueci minha senha" em um
 * só componente, alternando por modo. Ao autenticar com sucesso, chama
 * `onAuthenticated(user)` para o App trocar de tela.
 */
export default function AuthForm({ onAuthenticated }) {
  const [mode, setMode] = useState("login"); // "login" | "register" | "forgot"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [info, setInfo] = useState(null);

  const isRegister = mode === "register";
  const isForgot = mode === "forgot";

  const switchMode = (next) => {
    setMode(next);
    setError(null);
    setInfo(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    setError(null);
    setInfo(null);

    try {
      if (isForgot) {
        const result = await api.auth.forgotPassword({ email });
        setInfo(result.message);
        return;
      }
      if (isRegister) {
        await api.auth.register({ email, password, full_name: fullName });
      }
      await api.auth.login({ email, password });
      const user = await api.auth.me();
      onAuthenticated(user);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao processar. Tente novamente.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto flex min-h-[70vh] max-w-sm flex-col justify-center px-6">
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <h2 className="mb-1 text-lg font-semibold text-slate-800 dark:text-slate-100">
          {isForgot ? "Esqueci minha senha" : isRegister ? "Criar conta" : "Entrar"}
        </h2>
        <p className="mb-5 text-sm text-slate-500 dark:text-slate-400">
          {isForgot
            ? "Informe seu e-mail cadastrado e enviaremos um link para redefinir sua senha."
            : isRegister
            ? "Cadastre-se para acompanhar seu progresso, XP e sequência de estudos."
            : "Entre para responder questões e acompanhar seu desempenho."}
        </p>

        <form onSubmit={handleSubmit} className="space-y-3">
          {isRegister && (
            <div>
              <label className={LABEL_CLASSES}>Nome completo</label>
              <input
                type="text"
                required
                minLength={2}
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className={INPUT_CLASSES}
              />
            </div>
          )}

          <div>
            <label className={LABEL_CLASSES}>E-mail</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className={INPUT_CLASSES}
            />
          </div>

          {!isForgot && (
            <div>
              <label className={LABEL_CLASSES}>Senha</label>
              <input
                type="password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className={INPUT_CLASSES}
              />
              {isRegister && (
                <p className="mt-1 text-xs text-slate-400 dark:text-slate-500">
                  Mínimo 8 caracteres, com ao menos 1 letra maiúscula e 1 número.
                </p>
              )}
            </div>
          )}

          {info && <p className="text-sm text-emerald-600 dark:text-emerald-400">{info}</p>}
          {error && <p className="text-sm text-rose-600 dark:text-rose-400">{error}</p>}

          <button
            type="submit"
            disabled={submitting}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {submitting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : isForgot ? (
              <KeyRound className="h-4 w-4" />
            ) : isRegister ? (
              <UserPlus className="h-4 w-4" />
            ) : (
              <LogIn className="h-4 w-4" />
            )}
            {isForgot ? "Enviar link de redefinição" : isRegister ? "Criar conta" : "Entrar"}
          </button>
        </form>

        <div className="mt-4 space-y-2 text-center text-xs">
          {!isForgot && (
            <button
              type="button"
              onClick={() => switchMode(isRegister ? "login" : "register")}
              className="block w-full text-slate-500 hover:text-brand-600 dark:text-slate-400 dark:hover:text-brand-400"
            >
              {isRegister ? "Já tem conta? Entrar" : "Não tem conta? Cadastre-se"}
            </button>
          )}
          {mode === "login" && (
            <button
              type="button"
              onClick={() => switchMode("forgot")}
              className="block w-full text-slate-500 hover:text-brand-600 dark:text-slate-400 dark:hover:text-brand-400"
            >
              Esqueci minha senha
            </button>
          )}
          {isForgot && (
            <button
              type="button"
              onClick={() => switchMode("login")}
              className="block w-full text-slate-500 hover:text-brand-600 dark:text-slate-400 dark:hover:text-brand-400"
            >
              Voltar para o login
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
