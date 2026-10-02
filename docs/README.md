# DOCUMENTACAO

| Pasta | Conteúdo |
|---|---|
| [adr/](adr/) | Architecture Decision Records — 9 decisões com contexto, alternativas descartadas e gatilhos de revisão |
| [hu/](hu/) | Histórias de Usuário — 24 HUs em 5 épicos, com critérios de aceite verificáveis |

## Por onde começar

1. **[ADR-008 LIMITACOES DOS DADOS](adr/ADR-008%20LIMITACOES%20DOS%20DADOS%20EXPLICITAS%20NA%20UI.md)** —
   define o que é possível construir. É o constrangimento mais forte do produto.
2. **[E5 PLATAFORMA E QUALIDADE](hu/E5%20PLATAFORMA%20E%20QUALIDADE.md)** —
   primeiro épico a implementar; as demais HUs dependem dele.
3. **[Índice das ADRs](adr/README.md)** e **[Índice das HUs](hu/README.md)**.

## Convenção de nomenclatura

Arquivos em **CAIXA ALTA com espaços reais**, sem acentos:

```
ADR-001 DATASET OMOP SINTETICO.md
E1 PRONTUARIO DO PACIENTE.md
```

Os acentos são omitidos no **nome do arquivo** para evitar problemas de encoding
entre sistemas; o conteúdo é em português com acentuação normal.
