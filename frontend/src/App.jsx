import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { api } from "./api/client";
import { useTheme } from "./hooks/useTheme";
import AdminAddQuestionForm from "./components/AdminAddQuestionForm.jsx";
import AuthForm from "./components/AuthForm.jsx";
import ResetPasswordForm from "./components/ResetPasswordForm.jsx";
import Sidebar from "./components/Sidebar.jsx";
import StudentDashboard from "./components/StudentDashboard.jsx";
import NotebookPage from "./components/NotebookPage.jsx";
import ProfilePage from "./components/ProfilePage.jsx";

function getResetTokenFromUrl() {
  const params = new URLSearchParams(window.location.search);
  return params.get("token");
}

export default function App() {
  const { theme, toggleTheme } = useTheme();
  const [user, setUser] = useState(null);
  const [checkingSession, setCheckingSession] = useState(true);
  const [view, setView] = useState("dashboard");
  const [resetToken, setResetToken] = useState(getResetTokenFromUrl);

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
      setView("dashboard");
    }
  };

  const clearResetToken = () => {
    setResetToken(null);
    window.history.replaceState({}, "", window.location.pathname);
  };

  // O link de e-mail leva para "/?token=...": essa tela tem prioridade sobre
  // qualquer outra, autenticado ou não.
  if (resetToken) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
        <ResetPasswordForm token={resetToken} onDone={clearResetToken} />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      {checkingSession ? (
        <div className="flex min-h-screen items-center justify-center gap-2 text-slate-500 dark:text-slate-400">
          <Loader2 className="h-5 w-5 animate-spin" /> Carregando...
        </div>
      ) : user ? (
        <div className="flex flex-col md:flex-row">
          <Sidebar
            user={user}
            activeView={view}
            onNavigate={setView}
            onLogout={handleLogout}
            theme={theme}
            onToggleTheme={toggleTheme}
          />
          <main className="flex-1 overflow-y-auto overflow-x-hidden">
            {view === "dashboard" && <StudentDashboard user={user} onUserChange={setUser} />}
            {view === "notebook" && <NotebookPage />}
            {view === "profile" && <ProfilePage user={user} onUserChange={setUser} />}
            {view === "admin" && user.is_admin && <AdminAddQuestionForm />}
          </main>
        </div>
      ) : (
        <AuthForm onAuthenticated={setUser} />
      )}
    </div>
  );
}
