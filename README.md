# Sistema de Gestão de Salas e Recursos – SENAI

**Versão:** 1.0  
**Data de Emissão:** 08/01/2026  
**Responsável Técnico:** Álefe Leonardo da Silva Albuquerque – Coordenador Técnico

---

## 📌 Visão Geral

O **Sistema de Gestão de Salas e Recursos** é uma aplicação web desenvolvida para otimizar o processo de **ensalamento**, **intervalos** e **controle de Chromebooks e Notbooks** na unidade SENAI HUB DR/AC.

Ele substitui planilhas manuais e descentralizadas, fornecendo:

- centralização de informações  
- prevenção de conflitos de horário e sala  
- relatórios visuais automáticos  
- maior segurança nos dados  
- agilidade para coordenação e docentes  

---

## Funcionalidades

### ✔️ 1. Agendamento Inteligente
- validação automática de conflitos de sala
- suporte aos turnos: manhã, tarde, noite e integral
- bloqueio automático em caso de choque de horários
- regra específica para **Tempo Integral** (manhã + tarde)

### ✔️ 2. Controle de Inventário de TI
- acompanhamento em tempo real
- cálculo automático de saldo de equipamentos
- bloqueio de requisições acima do estoque disponível

### ✔️ 3. Relatórios e Dashboard
- visualização de ocupação diária
- filtros por data e turno
- geração automática de relatórios em **PNG**
- identidade visual SENAI aplicada

### ✔️ 4. Área Administrativa (Coordenação)
- acesso protegido por senha
- edição de agendamentos
- definição de intervalos por aula
- gestão direta na base de dados

---

## Tecnologias Utilizadas

- **Python 3.10+**
- **Streamlit** – interface web
- **Pandas** – processamento de dados
- **Matplotlib** – geração de relatórios
- **Google Sheets API** – banco de dados em nuvem

---

## Manual de Utilização Rápida

### ➕ Criar um novo agendamento
1. acesse **Novo Agendamento**
2. preencha docente, turma e sala
3. selecione data, turno e período
4. informe a quantidade de Chromebooks/Portáteis (opcional)
5. clique em **Confirmar Agendamento**

> o sistema bloqueia automaticamente conflitos e excesso de recursos

### Visualizar agenda
1. acesse **Visualizar Agenda**
2. selecione data e turno
3. veja os resultados atualizados automaticamente
4. clique em **📥 Baixar Relatório (PNG)** para exportar

### Área da Coordenação
1. acesse **Área Coordenação**
2. informe a senha
3. selecione a data e a aula
4. defina início e fim do intervalo
5. clique em **Salvar Intervalo**

---

## Como Executar o Sistema

### Pré-requisitos
- Python 3.10+
- Conta Google com acesso à planilha
- arquivo `credentials.json` da API Google

### Passos

```bash
# clonar o repositório
git clone https://github.com/SEU_USUARIO/NOME_DO_REPOSITORIO.git

# acessar pasta do projeto
cd NOME_DO_REPOSITORIO

# instalar dependências
pip install -r requirements.txt

# executar o sistema
streamlit run app.py

## Licença
- Projeto desenvolvido para uso institucional SENAI.
- Uso, cópia e redistribuição restritos à unidade autorizada.

## Suporte
- Responsável Técnico: Álefe Leonardo da Silva Albuquerque
- Função: Coordenador Técnico
- Contato: (68) 99944-2301
