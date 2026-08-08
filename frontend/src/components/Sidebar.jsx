import { BookMarked, LayoutDashboard, LogOut, Moon, Sun, User as UserIcon } from "lucide-react";

const NAV_ITEMS = [
  { key: "dashboard", label: "Questões", icon: LayoutDashboard },
  { key: "notebook", label: "Caderno de Erros", icon: BookMarked },
  { key: "profile", label: "Perfil", icon: UserIcon },
];

/**
 * Barra lateral fixa: navegação entre telas, alternância de tema e logout.
 */
export default function Sidebar({ user, activeView, onNavigate, onLogout, theme, onToggleTheme }) {
  return (
    <aside className="flex h-screen w-60 shrink-0 flex-col border-r border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
      <div className="border-b border-slate-200 px-5 py-4 dark:border-slate-800">
        <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">
          Plataforma de Concursos
        </p>
        {user && (
          <p className="mt-0.5 truncate text-xs text-slate-500 dark:text-slate-400">{user.email}</p>
        )}
      </div>

      <nav className="flex-1 space-y-1 px-3 py-4">
        {NAV_ITEMS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            type="button"
            onClick={() => onNavigate(key)}
            className={`flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
              activeView === key
                ? "bg-brand-50 text-brand-700 dark:bg-brand-700/20 dark:text-brand-300"
                : "text-slate-600 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-800"
            }`}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </nav>

      <div className="space-y-1 border-t border-slate-200 px-3 py-4 dark:border-slate-800">
        <button
          type="button"
          onClick={onToggleTheme}
          className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-800"
        >
          {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          {theme === "dark" ? "Tema claro" : "Tema escuro"}
        </button>
        <button
          type="button"
          onClick={onLogout}
          className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium text-rose-600 hover:bg-rose-50 dark:text-rose-400 dark:hover:bg-rose-950/40"
        >
          <LogOut className="h-4 w-4" />
          Sair
        </button>
      </div>
    </aside>
  );
}
