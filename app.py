import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
from modules.database import carregar_dados, carregar_lista_auxiliar, conectar_google_sheets
from modules.logic import verificar_conflito_sala, verificar_disponibilidade_recursos, TOTAL_CHROMEBOOKS, TOTAL_NOTEBOOKS
from modules.relatorio import gerar_imagem_ensalamento




# CONFIGURAÇÃO DA PÁGINA

st.set_page_config(
    page_title="Gestão de Salas | SENAI HUB",
    page_icon="assets/logo.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

if 'logado' not in st.session_state:
    st.session_state['logado'] = False

if not st.session_state['logado']:
    
    
    st.markdown("""
        <style>
            [data-testid="stSidebar"] {display: none;}
            [data-testid="collapsedControl"] {display: none;}
        </style>
    """, unsafe_allow_html=True)
    
    
    col1, col2, col3 = st.columns([1, 1.2, 1])
    
    with col2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        
        
        with st.form("form_login"):
            
            try: 
                
                st.image("assets/logo.png", use_container_width=True) 
            except: 
                st.markdown("<h2 style='text-align: center; color: #004587; margin-bottom: 0;'>SENAI HUB</h2>", unsafe_allow_html=True)
            
            st.markdown("<p style='text-align: center; color: #666; font-size: 15px; margin-top: 0;'>Gestão de Salas • Acesso Restrito</p>", unsafe_allow_html=True)
            
            st.info("👋 Olá! Insira sua credencial para acessar o painel.")
            
            
            senha_input = st.text_input("Senha de Acesso", type="password", placeholder="Digite a senha...")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            submit = st.form_submit_button("Entrar no Sistema", use_container_width=True)
            
            if submit:
                if "senha_coordenacao" in st.secrets:
                    senha_correta = st.secrets["senha_coordenacao"]
                    
                    if senha_input == senha_correta:
                        st.session_state['logado'] = True
                        st.rerun() 
                    else:
                        st.error("❌ Senha incorreta.")
                else:
                    st.error("⚠️ ERRO DE SISTEMA: Senha não configurada no cofre do servidor.")
    
    st.stop() 


with open("style/style.css", encoding="utf-8") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


# LISTAS DE DADOS

OPCOES_INICIO = ["07:30", "13:00", "13:30", "18:00", "18:30"]
OPCOES_FIM = ["11:00", "11:30", "16:00", "17:00", "17:30", "21:50"]

OPCOES_INTERVALO = [
    "Sem Intervalo", 
    "08:45 – 09:05",
    "09:10 – 09:30",
    "09:35 – 09:55",
    "14:45 – 15:05",
    "15:10 – 15:30",
    "15:35 – 15:55",
    "19:40 – 20:00",
    "20:05 – 20:25"
]

with st.sidebar:
    st.markdown("<br>", unsafe_allow_html=True)
    try: st.image("assets/logo.png", use_container_width=True)
    except: pass
    st.markdown("---")
    try:
        st.image("assets/1.png", use_container_width=True)
        
    except: pass
    st.caption("Sistema de Gestão v1.0")


# HEADER

st.markdown("""
<div class="header-senai">
    <h1>Gestão de Salas</h1>
    <p>Painel de Controle de Ensalamento e Recursos</p>
</div>
""", unsafe_allow_html=True)

# --- INICIALIZA A MEMÓRIA DA NAVEGAÇÃO ---
if 'menu_ativo' not in st.session_state:
    st.session_state['menu_ativo'] = "Novo Agendamento"

# --- O NOVO MENU EM FORMATO DE BOTÕES ---
c_menu1, c_menu2, c_menu3, c_menu4 = st.columns(4)

with c_menu1:
    if st.button("Novo Agendamento", use_container_width=True, type="primary" if st.session_state['menu_ativo'] == "Novo Agendamento" else "secondary"):
        st.session_state['menu_ativo'] = "Novo Agendamento"
        st.rerun()

with c_menu2:
    if st.button("Visualizar Agenda", use_container_width=True, type="primary" if st.session_state['menu_ativo'] == "Visualizar Agenda" else "secondary"):
        st.session_state['menu_ativo'] = "Visualizar Agenda"
        st.rerun()

with c_menu3:
    if st.button("Coordenação", use_container_width=True, type="primary" if st.session_state['menu_ativo'] == "Coordenação" else "secondary"):
        st.session_state['menu_ativo'] = "Coordenação"
        st.rerun()

with c_menu4:
    if st.button("Dashboard", use_container_width=True, type="primary" if st.session_state['menu_ativo'] == "Dashboard" else "secondary"):
        st.session_state['menu_ativo'] = "Dashboard"
        st.rerun()

st.markdown("---")

# --- LÓGICA DE EXIBIÇÃO DE TELAS ---
menu_selecionado = st.session_state.get('menu_ativo', 'Novo Agendamento')


# TAB 1: AGENDAMENTO 
 

if menu_selecionado == "Novo Agendamento":
    
    lista_docentes = carregar_lista_auxiliar("Docentes")
    lista_turmas = carregar_lista_auxiliar("Turmas")
    lista_salas = carregar_lista_auxiliar("Salas")

    with st.form("form_agendamento", clear_on_submit=True):
        st.subheader("Dados do Agendamento")
        c1, c2 = st.columns(2)
        
        with c1:
            professor = st.selectbox("Docente", lista_docentes) if lista_docentes else st.text_input("Docente (Cadastre na aba Coordenação)")
            turma = st.selectbox("Turma/Curso", lista_turmas) if lista_turmas else st.text_input("Turma (Cadastre na aba Coordenação)")
            sala = st.selectbox("Ambiente / Sala", lista_salas) if lista_salas else st.warning("Cadastre salas na aba Coordenação")
            
            st.markdown("<br>", unsafe_allow_html=True) 
            
            # --- CAMPOS DE PERÍODO ---
            cd1, cd2 = st.columns(2)
            data_inicio = cd1.date_input("Data Inicial", key="hub_data_ini")
            data_fim = cd2.date_input("Data Final", value=data_inicio, help="Para um único dia, deixe igual à data inicial.", key="hub_data_fim")

            st.markdown("<br>", unsafe_allow_html=True)
            qtd_alunos = st.number_input("Quantidade de Alunos", min_value=0, step=1, help="Número aproximado de alunos", key="hub_alunos")
        
        with c2:
            turno = st.selectbox("Turno", ["Manhã", "Tarde", "Noite", "Integral"])
            situacao = st.radio("Período", ["Turno Inteiro", "1º Horário", "2º Horário"], horizontal=True)
            
            ch1, ch2 = st.columns(2)
            hora_inicio = ch1.selectbox("Início Aula", OPCOES_INICIO)
            hora_fim = ch2.selectbox("Fim Aula", OPCOES_FIM)
            
            st.markdown("<br>", unsafe_allow_html=True)
            ci1, ci2 = st.columns(2)
            with ci1:
                st.markdown(
                    """
                    <p style='margin-bottom: 7px; font-size: 14px; font-weight: bold;'>Intervalo</p>
                    """, 
                    unsafe_allow_html=True
                )
                sel_intervalo = st.selectbox("Selecione intervalo", OPCOES_INTERVALO, label_visibility="collapsed")
            
            if sel_intervalo and "–" in sel_intervalo:
                partes = sel_intervalo.split("–")
                inicio_intervalo = partes[0].strip()
                fim_intervalo = partes[1].strip()
            else:
                inicio_intervalo = ""
                fim_intervalo = ""

        st.markdown("---")
        st.markdown(f"**Recursos Móveis (Estoque: {TOTAL_CHROMEBOOKS} Chrome | {TOTAL_NOTEBOOKS} Note)**")
        cr1, cr2 = st.columns(2)
        qtd_chrome = cr1.number_input("Qtd. Chromebooks", 0, TOTAL_CHROMEBOOKS)
        qtd_note = cr2.number_input("Qtd. Notebooks", 0, TOTAL_NOTEBOOKS)

        st.markdown("<br>", unsafe_allow_html=True)
        
        # --- LÓGICA DE VALIDAÇÃO EM LOTE ---
        if st.form_submit_button("Confirmar Agendamento", type="primary", use_container_width=True):
            
            if not professor or not turma or not sala:
                st.warning("⚠️ Verifique se Docente, Turma e Sala estão selecionados.")
            elif data_fim < data_inicio:
                st.error("❌ Lógica Incorreta: A Data Final não pode ser anterior à Data Inicial.")
            else:
                obj_inicio = datetime.strptime(hora_inicio, "%H:%M").time()
                obj_fim = datetime.strptime(hora_fim, "%H:%M").time()
                
                if obj_fim <= obj_inicio:
                    st.error("❌ Erro de Lógica: O horário de FIM deve ser maior que o INÍCIO.")
                else:
                    from datetime import timedelta
                    dias_uteis = []
                    delta = data_fim - data_inicio
                    
                    # Filtra Sábados e Domingos
                    for i in range(delta.days + 1):
                        dia_atual = data_inicio + timedelta(days=i)
                        if dia_atual.weekday() < 5: 
                            dias_uteis.append(dia_atual)
                    
                    if not dias_uteis:
                        st.error("❌ O período selecionado não possui dias úteis.")
                    else:
                        df_check = carregar_dados()
                        erros = []
                        
                        # Verifica todos os dias
                        for dia in dias_uteis:
                            conflito, msg_c = verificar_conflito_sala(df_check, sala, dia, obj_inicio, obj_fim)
                            recurso_ok, msg_r = verificar_disponibilidade_recursos(df_check, dia, obj_inicio, obj_fim, qtd_chrome, qtd_note)
                            
                            if conflito: erros.append(f"• **{dia.strftime('%d/%m/%Y')}**: {msg_c}")
                            if not recurso_ok: erros.append(f"• **{dia.strftime('%d/%m/%Y')}**: {msg_r}")
                            
                        if erros:
                            st.error("⚠️ Foram encontrados conflitos no seu período:")
                            for erro in erros:
                                st.write(erro)
                        else:
                            ss = conectar_google_sheets()
                            sheet = ss.sheet1
                            agora_str = str(datetime.now())
                            
                            linhas_para_inserir = []
                            for dia in dias_uteis:
                                linhas_para_inserir.append([
                                    str(dia), turno, situacao, hora_inicio, hora_fim,
                                    str(sala).upper(),      
                                    str(professor).upper(), 
                                    str(turma).upper(),     
                                    agora_str,
                                    qtd_chrome, qtd_note, inicio_intervalo, fim_intervalo,
                                    qtd_alunos              
                                ])
                            
                            sheet.append_rows(linhas_para_inserir)
                            st.success(f"✅ Agendamento de {len(dias_uteis)} dia(s) útil(eis) realizado com sucesso!")
                            import time; time.sleep(1.5)
                            st.rerun()


# TAB 2: VISUALIZAÇÃO (CORRIGIDA)

if menu_selecionado == "Visualizar Agenda":
    
    c1, c2, c3 = st.columns([1,2,1])
    filtro_data = c1.date_input("Data", datetime.today())
    filtro_turno = c2.multiselect("Turno", ["Manhã", "Tarde", "Noite", "Integral"], default=["Manhã", "Tarde", "Noite", "Integral"])
    if c3.button("🔄 Atualizar"): st.cache_data.clear()

    df = carregar_dados()
    if not df.empty:
        df['data'] = df['data'].astype(str)
        
        df_view = df[(df['data'] == str(filtro_data)) & (df['turno'].isin(filtro_turno))].sort_values('hora_inicio')
        
        if not df_view.empty:
            
            df_view['intervalo_tela'] = df_view.apply(
                lambda r: f"{str(r['inicio_intervalo'])}-{str(r['fim_intervalo'])}" 
                if r['inicio_intervalo'] and str(r['inicio_intervalo']).strip() != "" 
                else "-", 
                axis=1
            )

            cols_view = ['hora_inicio', 'hora_fim', 'situacao', 'sala', 'professor', 'turma', 'qtd_alunos', 'intervalo_tela', 'qtd_chromebooks', 'qtd_notebooks']
            
            df_display = df_view[cols_view].rename(columns={
                'hora_inicio': 'Início',
                'hora_fim': 'Fim',
                'situacao': 'Situação',
                'sala': 'Ambiente',
                'professor': 'Professor',
                'turma': 'Turma',
                'qtd_alunos': 'Alunos',
                'intervalo_tela': 'Intervalo', 
                'qtd_chromebooks': 'Chromebooks',
                'qtd_notebooks': 'Notebooks'
            })
            
            
            st.dataframe(
                df_display,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Alunos": st.column_config.NumberColumn(
                        "Alunos",
                        format="%d", 
                    ),
                    "Chromebooks": st.column_config.NumberColumn(
                        "Chromebooks",
                        format="%d",
                    ),
                    "Notebooks": st.column_config.NumberColumn(
                        "Notebooks",
                        format="%d",
                    )
                }
            )
            
            
            col_d1, _ = st.columns([1,3])
            buf = gerar_imagem_ensalamento(df_view, filtro_data)
            col_d1.download_button("📥 Baixar Relatório (PNG)", data=buf, file_name=f"Ensalamento_{filtro_data}.png", mime="image/png")
            
            total_alunos = int(df_view['qtd_alunos'].sum())
            st.caption(f"Total Reservado: {df_view['qtd_chromebooks'].sum()} Chromebooks | {df_view['qtd_notebooks'].sum()} Notebooks | Total Alunos: {total_alunos}")
        else:
            st.info("Nenhum agendamento encontrado.")



# TAB 3: COORDENAÇÃO 

if menu_selecionado == "Coordenação":
    st.subheader("Gestão de Cadastros e Agendamentos")
    
    with st.expander("Remover Agendamentos", expanded=True):
        st.warning("Cuidado: A exclusão é permanente.")
        
        col_del1, col_del2 = st.columns(2)
        data_del = col_del1.date_input("Filtrar Data", datetime.today(), key="data_del")
        turno_del = col_del2.selectbox("Filtrar Turno", ["Manhã", "Tarde", "Noite", "Integral"], key="turno_del")
        
        df_del = carregar_dados()
        
        if not df_del.empty:
            df_del['data'] = df_del['data'].astype(str)
            
            aulas_filtradas = df_del[
                (df_del['data'] == str(data_del)) & 
                (df_del['turno'] == turno_del)
            ]
            
            if not aulas_filtradas.empty:
                
                opcoes_exclusao = {
                    f"{row['sala']} | {row['professor']} | {row['hora_inicio']} - {row['hora_fim']}": i 
                    for i, row in aulas_filtradas.iterrows()
                }
                
                escolha_exclusao = st.selectbox("Selecione o agendamento para EXCLUIR:", list(opcoes_exclusao.keys()))
                
                if st.button("❌ Confirmar Exclusão"):
                    try:
                        ss = conectar_google_sheets()
                        ws = ss.sheet1
                        
                        idx_df = opcoes_exclusao[escolha_exclusao]
                        linha_dados = aulas_filtradas.loc[idx_df]
                        
                        todos_dados = ws.get_all_records()
                        linha_para_deletar = None
                        
                        for i, registro in enumerate(todos_dados):
                            if (str(registro['data']) == str(linha_dados['data']) and 
                                registro['sala'] == linha_dados['sala'] and 
                                registro['hora_inicio'] == linha_dados['hora_inicio'] and
                                registro['professor'] == linha_dados['professor']):
                                
                                linha_para_deletar = i + 2 
                                break
                        
                        if linha_para_deletar:
                            ws.delete_rows(linha_para_deletar)
                            st.success(f"Agendamento removido com sucesso!")
                            
                            import time; time.sleep(1.5)
                            st.rerun()
                        else:
                            st.error("Erro ao localizar a linha na planilha. Tente atualizar a página.")
                            
                    except Exception as e:
                        st.error(f"Erro de conexão ao excluir: {e}")
            else:
                st.info("Nenhum agendamento encontrado para esta Data/Turno.")
        else:
            st.info("Banco de dados vazio.")

    st.markdown("---")
    
    st.info("Utilize esta área para alimentar a base de dados do sistema.")
    
    col_a, col_b, col_c = st.columns(3)
    
    # --- CADASTRO DE DOCENTES ---
    with col_a:
        st.markdown("**👩‍🏫 Docentes**")
        with st.form("add_docente", clear_on_submit=True):
            novo_docente = st.text_input("Nome do Docente")
            if st.form_submit_button("Adicionar"):
                if novo_docente:
                    novo_docente_limpo = novo_docente.strip().upper()
                    lista_docentes = carregar_lista_auxiliar("Docentes")
                    
                    if any(novo_docente_limpo.lower() == item.lower() for item in lista_docentes):
                        st.warning(f"⚠️ '{novo_docente_limpo}' já está cadastrado!")
                    else:
                        ss = conectar_google_sheets()
                        try:
                            ws = ss.worksheet("Docentes")
                            ws.append_row([novo_docente_limpo])
                            st.success("Docente salvo com sucesso!")
                            carregar_lista_auxiliar.clear()
                            import time; time.sleep(1.5)
                            st.rerun() 
                        except Exception as e: 
                            st.error(f"Erro ao salvar: {e}")
    
    # --- CADASTRO DE TURMAS ---
    with col_b:
        st.markdown("**🎓 Turmas**")
        with st.form("add_turma", clear_on_submit=True):
            nova_turma = st.text_input("Nome da Turma")
            if st.form_submit_button("Adicionar"):
                if nova_turma:
                    nova_turma_limpa = nova_turma.strip().upper()
                    lista_turmas = carregar_lista_auxiliar("Turmas")
                    
                    if any(nova_turma_limpa.lower() == item.lower() for item in lista_turmas):
                        st.warning(f"⚠️ '{nova_turma_limpa}' já está cadastrada!")
                    else:
                        ss = conectar_google_sheets()
                        try:
                            ws = ss.worksheet("Turmas")
                            ws.append_row([nova_turma_limpa])
                            st.success("Turma salva com sucesso!")
                            carregar_lista_auxiliar.clear()
                            import time; time.sleep(1.5)
                            st.rerun()
                        except Exception as e: 
                            st.error(f"Erro ao salvar: {e}")

    # --- CADASTRO DE SALAS ---
    with col_c:
        st.markdown("**🏫 Ambientes**")
        with st.form("add_sala", clear_on_submit=True):
            nova_sala = st.text_input("Nome da Sala")
            if st.form_submit_button("Adicionar"):
                if nova_sala:
                    nova_sala_limpa = nova_sala.strip().upper()
                    lista_salas = carregar_lista_auxiliar("Salas")
                    
                    if any(nova_sala_limpa.lower() == item.lower() for item in lista_salas):
                        st.warning(f"⚠️ '{nova_sala_limpa}' já está cadastrada!")
                    else:
                        ss = conectar_google_sheets()
                        try:
                            ws = ss.worksheet("Salas")
                            ws.append_row([nova_sala_limpa])
                            st.success("Sala salva com sucesso!")
                            carregar_lista_auxiliar.clear()
                            import time; time.sleep(1.5)
                            st.rerun()
                        except Exception as e: 
                            st.error(f"Erro ao salvar: {e}")
    
    st.markdown("---")
    
    if st.checkbox("Visualizar listas cadastradas"):
        ld = carregar_lista_auxiliar("Docentes")
        lt = carregar_lista_auxiliar("Turmas")
        ls = carregar_lista_auxiliar("Salas")
        c1, c2, c3 = st.columns(3)
        c1.write(ld); c2.write(lt); c3.write(ls)

# TAB 4: DASHBOARD INTERATIVO

if menu_selecionado == "Dashboard":
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 1. FILTROS (Lado a Lado)
    c_dash1, c_dash2, c_dash3 = st.columns([1, 1, 1])
    
    with c_dash1:
        data_dash = st.date_input("Selecione a Data", datetime.today(), key="data_dash")
    with c_dash2:
        turno_dash = st.selectbox("Filtrar por Turno", ["Todos", "Manhã", "Tarde", "Noite", "Integral"], key="turno_dash")
    
    df_dash = carregar_dados()
    
    if not df_dash.empty:
        df_dash['data'] = df_dash['data'].astype(str)
        df_dia = df_dash[df_dash['data'] == str(data_dash)]
        
        # Filtragem inicial por turno se não for "Todos"
        if turno_dash != "Todos":
            df_dia = df_dia[df_dia['turno'] == turno_dash]
        
        if not df_dia.empty:
            st.markdown("---")
            
            # --- 2. INDICADORES (KPIs) ---
            kpi1, kpi2, kpi3 = st.columns(3)
            total_alunos = int(df_dia['qtd_alunos'].sum())
            uso_chrome = int(df_dia['qtd_chromebooks'].sum())
            uso_note = int(df_dia['qtd_notebooks'].sum())
            
            kpi1.metric("👥 Total de Alunos Atendidos", total_alunos)
            kpi2.metric("💻 Chromebooks Reservados", f"{uso_chrome} / {TOTAL_CHROMEBOOKS}")
            kpi3.metric("🖥️ Notebooks Reservados", f"{uso_note} / {TOTAL_NOTEBOOKS}")
            
            st.markdown("<br><br>", unsafe_allow_html=True)
            
            # --- 3. GRÁFICOS INTERATIVOS ---
            col_graf1, col_graf2 = st.columns(2)
            
            with col_graf1:
                
                st.markdown(
                    "<p style='font-size: 14px; color: #555; background-color: #f8f9fa; padding: 8px; border-radius: 5px; border-left: 4px solid #2b78c5;'>"
                    "💡 <b>Dica de Navegação:</b> Passe o mouse sobre as salas para ver os detalhes. "
                    "Se você clicar sem querer e a imagem der zoom, <b>clique na faixa do topo</b> para voltar."
                    "</p>", 
                    unsafe_allow_html=True
                )
                
                
                lista_salas_todas = carregar_lista_auxiliar("Salas")
                
                dados_status = []
                
                for s in lista_salas_todas:
                    bookings_da_sala = df_dia[df_dia['sala'] == s]
                    
                    if not bookings_da_sala.empty:
                        status_sala = '🔴 Ocupadas'
                        linhas_detalhe = []
                        
                        for _, row in bookings_da_sala.iterrows():
                            t_atual = row.get('turno', 'N/A')
                            turma_atual = row.get('turma', 'N/A')
                            
                            docente_atual = row.get('professor', 'N/A')
                            
                            linhas_detalhe.append(
                                f"<b>⏱ Turno:</b> {t_atual}<br>"
                                f"<b>Turma:</b> {turma_atual}<br>"
                                f"<b>Docente:</b> {docente_atual}"
                            )
                        
                        detalhes_string = "<br>------------------------<br>".join(linhas_detalhe)
                    else:
                        status_sala = '🟢 Livres'
                        detalhes_string = "<b>Totalmente Disponível</b><br>Nenhum agendamento para este período."
                        
                    dados_status.append({
                        'Visão Geral': '⬅️ CLIQUE AQUI PARA VOLTAR', 
                        'Ambiente': s,
                        'Status': status_sala,
                        'Detalhes': detalhes_string,
                        'Valor': 1
                    })
                    
                df_status = pd.DataFrame(dados_status)
                
                if not df_status.empty:
                    titulo_mapa = f"Visão de Ambientes ({turno_dash})" if turno_dash != "Todos" else "Visão de Ambientes (Dia Completo)"
                    
                    fig_status = px.treemap(
                        df_status, 
                        path=['Visão Geral', 'Status', 'Ambiente'], 
                        values='Valor',
                        color='Status', 
                        
                        color_discrete_map={'🔴 Ocupadas': '#e94d16', '🟢 Livres': '#198754', '(?)': '#e9ecef'},
                        title=titulo_mapa,
                        hover_data=['Detalhes'] 
                    )
                    
                    fig_status.update_layout(paper_bgcolor="rgba(0,0,0,0)", margin=dict(t=40, l=10, r=10, b=10))
                    fig_status.data[0].textinfo = 'label' 
                    
                    
                    fig_status.update_traces(
                        root=dict(color="#e9ecef"),
                        hovertemplate="<b>📍 %{label}</b><br><br>%{customdata[0]}<extra></extra>"
                    )
                    
                    st.plotly_chart(fig_status, use_container_width=True)
                else:
                    st.warning("⚠️ Nenhuma sala cadastrada no sistema ainda.")

            with col_graf2:
                
                alunos_turno = df_dia.groupby('turno')['qtd_alunos'].sum().reset_index()
                
                fig_turnos = px.pie(
                    alunos_turno, names='turno', values='qtd_alunos', 
                    title="Distribuição de Alunos por Turno",
                    hole=0.4, 
                    color_discrete_sequence=['#2b78c5', '#e94d16', '#198754', '#ffc107']
                )
                fig_turnos.update_layout(paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_turnos, use_container_width=True)
                
        else:
            if turno_dash != "Todos":
                st.info(f"Nenhum agendamento registrado para o turno da **{turno_dash}** nesta data.")
            else:
                st.info("Nenhum agendamento registrado para esta data.")
    else:
        st.info("O banco de dados está vazio.")