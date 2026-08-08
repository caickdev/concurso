import { useState } from "react";
import {
  BookMarked,
  LayoutDashboard,
  LogOut,
  Menu,
  Moon,
  ShieldPlus,
  Sun,
  User as UserIcon,
  X,
} from "lucide-react";

const NAV_ITEMS = [
  { key: "dashboard", label: "Questões", icon: LayoutDashboard },
  { key: "notebook", label: "Caderno de Erros", icon: BookMarked },
  { key: "profile", label: "Perfil", icon: UserIcon },
];

/**
 * Navegação entre telas, alternância de tema e logout. Em telas < md vira um
 * menu hambúrguer com gaveta retrátil; a partir de md fica fixa lateral.
 */
export default function Sidebar({ user, activeView, onNavigate, onLogout, theme, onToggleTheme }) {
  const [mobileOpen, setMobileOpen] = useState(false);

  const navItems = user?.is_admin
    ? [...NAV_ITEMS, { key: "admin", label: "Cadastrar questão", icon: ShieldPlus }]
    : NAV_ITEMS;

  const handleNavigate = (key) => {
    onNavigate(key);
    setMobileOpen(false);
  };

  return (
    <>
      <header className="flex h-14 shrink-0 items-center justify-between border-b border-slate-200 bg-white px-4 dark:border-slate-800 dark:bg-slate-900 md:hidden">
        <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">
          Plataforma de Concursos
        </p>
        <button
          type="button"
          onClick={() => setMobileOpen(true)}
          aria-label="Abrir menu"
          className="rounded-lg p-2 text-slate-600 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-800"
        >
          <Menu className="h-5 w-5" />
        </button>
      </header>

      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/40 md:hidden"
          onClick={() => setMobileOpen(false)}
          aria-hidden="true"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-50 flex h-screen w-64 shrink-0 -translate-x-full flex-col border-r border-slate-200 bg-white transition-transform duration-200 dark:border-slate-800 dark:bg-slate-900 md:static md:h-screen md:w-60 md:translate-x-0 ${
          mobileOpen ? "translate-x-0" : ""
        }`}
      >
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4 dark:border-slate-800">
          <div>
            <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">
              Plataforma de Concursos
            </p>
            {user && (
              <p className="mt-0.5 truncate text-xs text-slate-500 dark:text-slate-400">{user.email}</p>
            )}
          </div>
          <button
            type="button"
            onClick={() => setMobileOpen(false)}
            aria-label="Fechar menu"
            className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-50 dark:text-slate-400 dark:hover:bg-slate-800 md:hidden"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <nav className="flex-1 space-y-1 px-3 py-4">
          {navItems.map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              type="button"
              onClick={() => handleNavigate(key)}
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
    </>
  );
}
