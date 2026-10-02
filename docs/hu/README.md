# HISTORIAS DE USUARIO

Organizadas por épico. Cada HU traz critérios de aceite verificáveis, as
dependências técnicas e as armadilhas conhecidas.

Os números citados foram **medidos no banco populado**, não estimados.

## Personas

| Persona | Quem é | O que precisa |
|---|---|---|
| **Clínico** | Médico explorando prontuários | Ver a história completa de um paciente rápido |
| **Pesquisador** | Analista de dados populacionais | Montar coortes, medir prevalência, exportar |
| **Engenheiro** | Dev integrando sistemas | API tipada, previsível, documentada |

## Épicos

| # | Épico | HUs | Camada |
|---|---|---|---|
| [E1](E1%20PRONTUARIO%20DO%20PACIENTE.md) | Prontuário do paciente | 6 | Back + Front |
| [E2](E2%20ATENDIMENTOS%20E%20TRAJETORIA.md) | Atendimentos e trajetória | 4 | Back + Front |
| [E3](E3%20COORTES%20E%20ESTATISTICAS.md) | Coortes e estatísticas | 5 | Back + Front |
| [E4](E4%20DICIONARIO%20E%20BUSCA.md) | Dicionário e busca | 3 | Back + Front |
| [E5](E5%20PLATAFORMA%20E%20QUALIDADE.md) | Plataforma e qualidade | 6 | Infra |

**Total: 24 HUs**

> A camada de agente de IA será especificada quando o tema for abordado — ver
> "Temas ainda sem ADR" no [índice das ADRs](../adr/README.md).

## Convenções

| Marcador | Significado |
|---|---|
| `MUST` | Bloqueia a entrega do épico |
| `SHOULD` | Importante, não bloqueia |
| `COULD` | Melhoria desejável |

## Premissas que valem para todas as HUs

Derivadas das ADRs — não repetidas em cada história:

- **Medicamentos** sempre via `vw_medicamento_valido`. Consultar
  `exposicao_medicamento` direto traz 7.899 diagnósticos rotulados como fármaco
  (ADR-008)
- **Exames não têm valor numérico.** Nenhuma HU promete gráfico de tendência,
  IMC ou controle pressórico (ADR-008)
- **Pacientes não têm nome.** Rótulo é `Paciente #<id>` (ADR-009)
- **Sem autenticação.** Nenhuma HU tem critério de login ou permissão (ADR-005)
- **Toda lista é paginada.** Um paciente chega a 2.486 exames (ADR-004)
- **Nas tabelas `exame`, `exposicao_medicamento` e `observacao`, o identificador
  é `pk`**, não o ID original (ADR-002, ADR-006)
- **Acesso a dados via SQLAlchemy**; SQL direto apenas nas consultas analíticas
  — timeline, agregações e trajetória (ADR-006)

## Ordem sugerida de implementação

```
E5 (plataforma)  →  E1 (prontuário)  →  E2 (atendimentos)
                         ↓
                    E4 (dicionário)
                         ↓
                    E3 (coortes)
```

E5 primeiro porque API e frontend precisam subir antes de qualquer tela, e os
modelos ORM e migrations são pré-requisito de todo o resto.
