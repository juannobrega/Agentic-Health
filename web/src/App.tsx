import { NavLink, Route, Routes } from "react-router-dom";

import { Atendimento } from "./paginas/Atendimento";
import { Atendimentos } from "./paginas/Atendimentos";
import { Condicoes } from "./paginas/Condicoes";
import { Coortes } from "./paginas/Coortes";
import { Dashboard } from "./paginas/Dashboard";
import { ListaPacientes } from "./paginas/ListaPacientes";
import { Prontuario } from "./paginas/Prontuario";
import { Trajetoria } from "./paginas/Trajetoria";

const MENU = [
  ["/", "Visão geral"],
  ["/pacientes", "Pacientes"],
  ["/atendimentos", "Atendimentos"],
  ["/prevalencia", "Prevalência"],
  ["/coortes", "Coortes"],
] as const;

export function App() {
  return (
    <div className="app">
      <aside className="menu">
        <h1>
          Agentic Health
          <small>dados sintéticos · OMOP CDM</small>
        </h1>
        <nav>
          {MENU.map(([caminho, rotulo]) => (
            <NavLink
              key={caminho}
              to={caminho}
              end={caminho === "/"}
              className={({ isActive }) => (isActive ? "ativo" : "")}
            >
              {rotulo}
            </NavLink>
          ))}
        </nav>
      </aside>

      <main className="conteudo">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/pacientes" element={<ListaPacientes />} />
          <Route path="/pacientes/:id" element={<Prontuario />} />
          <Route path="/pacientes/:id/trajetoria" element={<Trajetoria />} />
          <Route path="/atendimentos" element={<Atendimentos />} />
          <Route path="/atendimentos/:id" element={<Atendimento />} />
          <Route path="/prevalencia" element={<Condicoes />} />
          <Route path="/coortes" element={<Coortes />} />
          <Route
            path="*"
            element={<div className="estado">Página não encontrada.</div>}
          />
        </Routes>
      </main>
    </div>
  );
}
