import StudentDashboard from "./components/StudentDashboard.jsx";

export default function App() {
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white px-6 py-4">
        <h1 className="text-lg font-semibold text-slate-800">
          Plataforma de Questões para Concursos
        </h1>
      </header>
      <StudentDashboard />
    </div>
  );
}
