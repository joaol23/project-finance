# Projeto Organizador Financeiro - Diretrizes do Assistente (Rules)

Este arquivo define as regras de desenvolvimento e comportamento específicas para o projeto **Organizador Financeiro** no workspace atual. Toda sessão subsequente deve ler este arquivo e respeitar estas diretrizes.

---

## 📌 Contexto de Referência
* A arquitetura completa, estrutura de arquivos e esquema do banco de dados estão documentados em [project_context.md](file:///C:/Users/joaol/OneDrive/Área de Trabalho/projeto-financa/docs/project_context.md).

---

## 🛠️ Regras de Desenvolvimento

1. **Integridade da Interface e Estilo CSS**:
   * O aplicativo possui um estilo visual escuro personalizado com roxo (`#9333ea` / `#a855f7`). Nunca utilize widgets Streamlit padrão sem verificar se eles entram em conflito com o CSS customizado em [app.py](file:///C:/Users/joaol/OneDrive/Área de Trabalho/projeto-financa/app.py).
   * Mantenha o CSS limpo e isolado. Se precisar adicionar novos elementos visuais, adicione as regras CSS correspondentes no bloco de estilos centralizado em `app.py`.

2. **Gerenciamento de Sessão do Banco de Dados (SQLAlchemy)**:
   * Sempre feche as sessões abertas chamando `session.close()` ao final de cada script de view ou função para evitar vazamento de conexões com o banco SQLite.
   * Ao fazer alterações que envolvem commit no banco de dados, utilize tratamento de exceções com `session.rollback()` em caso de falha.

3. **Regra Contábil do Mês (Período Contábil)**:
   * Lembre-se de que a regra do período contábil do mês é personalizada: o início é o **último dia útil do mês anterior (exclusivo)** e o fim é o **último dia útil do mês selecionado (inclusivo)**. 
   * As transações pertencem a um mês se a data for `> period_start` e `<= period_end`.

4. **Tratamento de Investimentos**:
   * Novas transações de investimento (compra/venda) devem passar pelo fluxo de vinculação de ativos. Elas começam sem `investment_id` e ficam pendentes na view de investimentos até serem associadas a um Ticker.
   * Ao criar novas transações, respeite os tipos de dados `Decimal` nas colunas de quantidade, preço e valores para evitar erros de precisão.

5. **Importador de Dados**:
   * O importador é robusto e possui regras para ignorar duplicatas. Qualquer alteração em [import_data.py](file:///C:/Users/joaol/OneDrive/Área de Trabalho/projeto-financa/views/import_data.py) deve manter a compatibilidade com os formatos CSV Bradesco/Nubank e PDFs do Bradesco.
