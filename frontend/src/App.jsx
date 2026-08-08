import { useEffect, useState } from "react";
import { LogOut, Loader2 } from "lucide-react";
import { api } from "./api/client";
import AuthForm from "./components/AuthForm.jsx";
import StudentDashboard from "./components/StudentDashboard.jsx";

export default function App() {
  const [user, setUser] = useState(null);
  const [checkingSession, setCheckingSession] = useState(true);

  useEffect(() => {
    api.auth
      .me()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setCheckingSession(false));
  }, []);

  const handleLogout = async () => {
    try {
      await api.auth.logout();
    } finally {
      setUser(null);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-4">
        <h1 className="text-lg font-semibold text-slate-800">
          Plataforma de Questões para Concursos
        </h1>
        {user && (
          <div className="flex items-center gap-3 text-sm text-slate-600">
            <span>Olá, {user.full_name.split(" ")[0]}</span>
            <button
              type="button"
              onClick={handleLogout}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50"
            >
              <LogOut className="h-3.5 w-3.5" /> Sair
            </button>
          </div>
        )}
      </header>

      {checkingSession ? (
        <div className="flex min-h-[70vh] items-center justify-center gap-2 text-slate-500">
          <Loader2 className="h-5 w-5 animate-spin" /> Carregando...
        </div>
      ) : user ? (
        <StudentDashboard user={user} onUserChange={setUser} />
      ) : (
        <AuthForm onAuthenticated={setUser} />
      )}
    </div>
  );
}
