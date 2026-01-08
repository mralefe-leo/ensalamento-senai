import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, time
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import io


# CONFIGURAÇÃO DA PÁGINA

st.set_page_config(
    page_title="Gestão de Salas | SENAI",
    page_icon="logo.png",
    layout="wide",
    initial_sidebar_state="expanded"
)


# CONSTANTES DE ESTOQUE

TOTAL_CHROMEBOOKS = 34
TOTAL_NOTEBOOKS = 11


# CSS – IDENTIDADE VISUAL SENAI

st.markdown("""
<style>
     
            
    /* 1. LAYOUT */    
    /* Sobe o conteúdo para o topo */
    div.block-container {
        padding-top: 2rem !important;
        padding-bottom: 3rem !important;
    }
    
    /* Remove o fundo do cabeçalho padrão */
    header[data-testid="stHeader"] {
        background: transparent !important;
    }

    /* Garante fundo transparente nas abas */
    .stTabs [data-baseweb="tab-list"], 
    .stTabs [data-baseweb="tab"],
    [data-baseweb="tab-panel"] {
        background-color: transparent !important;
    }

    /* 2. ESTILOS DO SEU TEMA */

    /* Fonte base */
    html, body, [class*="css"] {
        font-family: 'Segoe UI', 'Roboto', Arial, sans-serif;
    }

    /* Sidebar - Mantendo seu Azul e Texto Preto */
    [data-testid="stSidebar"] {
        background: #fffff; 
    }
    [data-testid="stSidebar"] * {
        color: #e94d16 !important;
        font-color: #fffff; 
    }

    /* Header Personalizado */
    .header-senai {
        background: #2b78c5;
        padding: 24px 32px;
        border-radius: 12px;
        margin-bottom: 24px;
        color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .header-senai h1 { margin: 0; font-size: 2.2rem; font-weight: 700; }
    .header-senai p { margin-top: 5px; font-size: 1.1rem; opacity: 0.9; }

    
    [data-testid="stForm"] {
        background-color: var(--secondary-background-color); /* Adapta cor automaticamente */
        padding: 24px;
        border-radius: 12px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        border: 1px solid rgba(128,128,128, 0.2);
    }

    /* Ajuste de Botões */
    div.stButton > button {
        background-color: #2b78c5; 
        color: white;
        border: none;
        font-weight: bold;
        width: 100%;
        border-radius: 6px;
        padding: 0.5rem 1rem;
        transition: all 0.3s;
    }
    div.stButton > button:hover {
        background-color: #e0e0e0;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        color: #2b78c5; 
    }

    /* Tabelas */
    [data-testid="stDataFrame"] {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
    }

    /* CONFIGURAÇÃO DAS TABS (ABAS) */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    
    .stTabs [data-baseweb="tab"] {
        height: auto;
        white-space: pre-wrap;
        background-color: transparent !important; 
        gap: 1px;
        padding: 10px 25px;
        color: #2b78c5;
        font-size: 20px !important; 
        font-weight: bold;
        border: 1px solid rgba(128,128,128, 0.2);
        border-bottom: none;
        border-radius: 8px 8px 0 0;
    }

    /* Aba Selecionada */
    .stTabs [aria-selected="true"] {
        background-color: #2b78c5 !important;
        color: white !important;
    }

    /* FIX BOTÃO IMAGEM (Mantendo o Vermelho apenas aqui para destaque, ou mude para azul se preferir) */
    [data-testid="stSidebar"] [data-testid="stImage"] button {
        background-color: white !important;
        border: 2px solid #2b78c5 !important; /* Mudei para seu Azul */
        border-radius: 50% !important;
        width: 32px !important;
        height: 32px !important;
        opacity: 1 !important;
    }
    /* Ícone Azul */
    [data-testid="stSidebar"] [data-testid="stImage"] button svg {
        /* Filtro para gerar cor azul aproximada */
        filter: invert(33%) sepia(99%) saturate(1637%) hue-rotate(193deg) brightness(91%) contrast(90%) !important;
        transform: scale(0.9);
    }
</style>
""", unsafe_allow_html=True)


# LISTAS DE DADOS

LISTA_SALAS = sorted([
    "SALA DE AULA 24","SALA DE AULA 25","SALA DE AULA 49","SALA DE AULA 55",
    "SALA DE AULA 56","SALA DE AULA 61","SALA DE AULA 62","SALA DE AULA 63",
    "SALA DE AULA 71","SALA DE AULA 72","SALA DE AULA 73",
    "LAB. DE INFORMÁTICA 31","LAB. DE INFORMÁTICA 48","LAB. DE INFORMÁTICA 74",
    "LAB. DE INFORMÁTICA 75","LAB. DE REDES DE DISTRIBUIÇÃO 84",
    "GALPÃO DE EDIFICAÇÕES 51","GALPÃO DE ELÉTRICA 52",
    "GALPÃO DE ENERGIA RENOVÁVEL 53","SALA DE ACOLHIMENTO 60"
])

HORARIOS_TURNO = {
    "Manhã": { "Turno Inteiro": (time(7,0), time(12,0)), "1º Horário": (time(7,0), time(9,30)), "2º Horário": (time(9,30), time(12,0)) },
    "Tarde": { "Turno Inteiro": (time(13,0), time(17,30)), "1º Horário": (time(13,0), time(15,15)), "2º Horário": (time(15,15), time(17,30)) },
    "Noite": { "Turno Inteiro": (time(18,0), time(22,0)), "1º Horário": (time(18,0), time(20,0)), "2º Horário": (time(20,0), time(22,0)) },
    "Integral": { "Turno Inteiro": (time(7,0), time(17,30)), "1º Horário": (time(7,0), time(12,0)), "2º Horário": (time(13,0), time(17,30)) }
}


# CONEXÃO E DADOS

@st.cache_resource
def conectar_google_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    if "gcp_service_account" in st.secrets:
        try:
            creds_dict = dict(st.secrets["gcp_service_account"])
            if "private_key" in creds_dict: creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            return gspread.authorize(creds).open("sistema_ensalamento_db").sheet1
        except: st.stop()
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        return gspread.authorize(creds).open("sistema_ensalamento_db").sheet1
    except: st.error("Erro de credenciais"); st.stop()

def carregar_dados():
    try:
        sheet = conectar_google_sheets()
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        if not df.empty: df.columns = df.columns.str.lower().str.strip()
        
        colunas = ['data', 'turno', 'situacao', 'hora_inicio', 'hora_fim', 'sala', 'professor', 'turma', 'data_registro', 'qtd_chromebooks', 'qtd_notebooks', 'inicio_intervalo', 'fim_intervalo']
        if df.empty: return pd.DataFrame(columns=colunas)
        
        for col in colunas:
            if col not in df.columns: df[col] = 0 if 'qtd' in col else ''
            
        df['qtd_chromebooks'] = pd.to_numeric(df['qtd_chromebooks'], errors='coerce').fillna(0)
        df['qtd_notebooks'] = pd.to_numeric(df['qtd_notebooks'], errors='coerce').fillna(0)
        return df
    except: return pd.DataFrame()


# LÓGICA DE NEGÓCIO

def verificar_conflito_sala(df, sala, data_agendamento, inicio_novo, fim_novo):
    if df.empty: return False, ""
    df['data'] = df['data'].astype(str)
    conflitos = df[(df['sala'] == sala) & (df['data'] == str(data_agendamento))]
    for _, row in conflitos.iterrows():
        try:
            str_ini, str_fim = str(row['hora_inicio'])[:5], str(row['hora_fim'])[:5]
            ini_exist = datetime.strptime(str_ini, "%H:%M").time()
            fim_exist = datetime.strptime(str_fim, "%H:%M").time()
            if (inicio_novo < fim_exist) and (fim_novo > ini_exist):
                return True, f"Sala ocupada por {row['professor']} ({str_ini}-{str_fim})"
        except: continue
    return False, ""

def verificar_disponibilidade_recursos(df, data_agendamento, inicio_novo, fim_novo, qtd_chrome, qtd_note):
    if qtd_chrome == 0 and qtd_note == 0: return True, ""
    if df.empty: return True, ""
    df['data'] = df['data'].astype(str)
    agendamentos = df[df['data'] == str(data_agendamento)]
    chrome_uso, note_uso = 0, 0
    for _, row in agendamentos.iterrows():
        try:
            str_ini, str_fim = str(row['hora_inicio'])[:5], str(row['hora_fim'])[:5]
            ini_exist = datetime.strptime(str_ini, "%H:%M").time()
            fim_exist = datetime.strptime(str_fim, "%H:%M").time()
            if (inicio_novo < fim_exist) and (fim_novo > ini_exist):
                chrome_uso += int(row['qtd_chromebooks'])
                note_uso += int(row['qtd_notebooks'])
        except: continue
    
    if qtd_chrome > (TOTAL_CHROMEBOOKS - chrome_uso): return False, f"Falta Chromebooks (Disp: {TOTAL_CHROMEBOOKS - chrome_uso})"
    if qtd_note > (TOTAL_NOTEBOOKS - note_uso): return False, f"Falta Notebooks (Disp: {TOTAL_NOTEBOOKS - note_uso})"
    return True, ""

def gerar_imagem_ensalamento(df_filtrado, data_selecionada):
    plt.rcParams['font.family'] = 'DejaVu Sans'

    df_img = df_filtrado.copy()
    df_img['intervalo_fmt'] = df_img.apply(
        lambda r: f"{str(r['inicio_intervalo'])}-{str(r['fim_intervalo'])}" if r['inicio_intervalo'] else "-",
        axis=1
    )

    colunas_map = {
        'turno': 'Turno',
        'situacao': 'Situação',
        'sala': 'Ambiente',
        'professor': 'Docente',
        'turma': 'Turma',
        'intervalo_fmt': 'Intervalo',
        'qtd_chromebooks': 'Chromebooks',
        'qtd_notebooks': 'Notebooks'
    }

    cols_to_use = [c for c in colunas_map.keys() if c in df_img.columns]
    df_final = df_img[cols_to_use].rename(columns=colunas_map)

    # -------- FIGURA BASE --------
    linhas = len(df_final) + 6
    fig = plt.figure(figsize=(16, max(6, 2.5 + len(df_final) * 0.55)), dpi=300)

    
    #  BLOCO 1 – LOGO CENTRALIZADA
    
    ax_logo = fig.add_axes([0, 0.80, 1, 0.18])

    ax_logo.axis('off')
    try:
        logo = mpimg.imread("logo.png")
        ax_logo.imshow(logo)
    except:
        ax_logo.text(0.5, 0.5, "SENAI", fontsize=22, ha="center", va="center")

    
    #  BLOCO 2 – TÍTULO
   
    ax_titulo = fig.add_axes([0, 0.74, 1, 0.08])
    ax_titulo.axis('off')
    ax_titulo.text(0.5, 0.5, "ENSALAMENTO DIÁRIO", fontsize=18, fontweight="bold",
                   ha="center", va="center", color="#004587")

   
    #  BLOCO 3 – DATA
    
    ax_data = fig.add_axes([0, 0.68, 1, 0.06])
    ax_data.axis('off')
    ax_data.text(0.5, 0.5,
                 f"Data: {data_selecionada.strftime('%d/%m/%Y')}",
                 fontsize=12,
                 ha="center", va="center", color="#444")

    
    #  BLOCO 4 – TABELA
    
    ax_tab = fig.add_axes([0.03, 0.05, 0.94, 0.60])
    ax_tab.axis('off')

    tabela = ax_tab.table(
        cellText=df_final.values,
        colLabels=df_final.columns,
        loc='upper center',
        cellLoc='center'
    )

    tabela.auto_set_font_size(False)
    tabela.set_fontsize(9)
    tabela.scale(1, 1.4)

    for (r, c), cell in tabela.get_celld().items():
        cell.set_linewidth(0.5)
        cell.set_edgecolor("#cccccc")

        if r == 0:
            cell.set_facecolor("#004587")
            cell.set_text_props(color="white", weight="bold")
        else:
            cell.set_facecolor("#F7F9FC" if r % 2 == 0 else "white")

    
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    plt.close(fig)

    return buf



# INTERFACE SIDEBAR

with st.sidebar:
    st.markdown("<br>", unsafe_allow_html=True)
    try: st.image("logo.png", use_container_width=True)
    except: pass
    st.markdown("---")
    try:
        st.image("1.png", use_container_width=True)
        st.image("2.png", use_container_width=True)
        st.image("3.png", use_container_width=True)
    except: pass
    st.caption("Sistema de Gestão v1.0")


# HEADER

st.markdown("""
<div class="header-senai">
    <h1>Gestão de Salas</h1>
    <p>Painel de Controle de Ensalamento e Recursos</p>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["Novo Agendamento", "Visualizar Agenda", "Coordenação"])


# TAB 1: AGENDAMENTO 

with tab1:
    
    with st.form("form_agendamento"):
        st.subheader("Dados do Agendamento")
        c1, c2 = st.columns(2)
        with c1:
            professor = st.text_input("Nome do Docente")
            turma = st.text_input("Turma/Curso")
            sala = st.selectbox("Ambiente / Sala", LISTA_SALAS)
            data = st.date_input("Data da Aula")
        with c2:
            turno = st.selectbox("Turno", list(HORARIOS_TURNO.keys()))
            situacao = st.radio("Período", list(HORARIOS_TURNO[turno].keys()), horizontal=True)
            try: h_ini, h_fim = HORARIOS_TURNO[turno][situacao]
            except: h_ini, h_fim = time(0,0), time(0,0)
            
            ch1, ch2 = st.columns(2)
            hora_inicio = ch1.time_input("Início", h_ini)
            hora_fim = ch2.time_input("Fim", h_fim)

        st.markdown("---")
        st.markdown(f"**Recursos Móveis (Estoque: {TOTAL_CHROMEBOOKS} Chrome | {TOTAL_NOTEBOOKS} Note)**")
        cr1, cr2 = st.columns(2)
        qtd_chrome = cr1.number_input("Qtd. Chromebooks", 0, TOTAL_CHROMEBOOKS)
        qtd_note = cr2.number_input("Qtd. Notebooks", 0, TOTAL_NOTEBOOKS)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.form_submit_button("Confirmar Agendamento"):
            if not professor or not turma:
                st.warning("Preencha Professor e Turma.")
            else:
                df_check = carregar_dados()
                conflito, msg_c = verificar_conflito_sala(df_check, sala, data, hora_inicio, hora_fim)
                recurso_ok, msg_r = verificar_disponibilidade_recursos(df_check, data, hora_inicio, hora_fim, qtd_chrome, qtd_note)
                
                if conflito: st.error(f"❌ {msg_c}")
                elif not recurso_ok: st.error(f"❌ {msg_r}")
                else:
                    sheet = conectar_google_sheets()
                    sheet.append_row([
                        str(data), turno, situacao, str(hora_inicio)[:5], str(hora_fim)[:5],
                        sala, professor, turma, str(datetime.now()),
                        qtd_chrome, qtd_note, "", ""
                    ])
                    st.success("✅ Agendado com sucesso!")
                    st.cache_data.clear()
    


# TAB 2: VISUALIZAÇÃO (ATUALIZADO COM INTERVALO)

with tab2:
    
    c1, c2, c3 = st.columns([1,2,1])
    filtro_data = c1.date_input("Data", datetime.today())
    filtro_turno = c2.multiselect("Turno", list(HORARIOS_TURNO.keys()), default=list(HORARIOS_TURNO.keys()))
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

            
            cols_view = ['hora_inicio', 'hora_fim', 'situacao', 'sala', 'professor', 'turma', 'intervalo_tela', 'qtd_chromebooks', 'qtd_notebooks']
            
           
            st.dataframe(
                df_view[cols_view].rename(columns={
                    'hora_inicio': 'Início',
                    'hora_fim': 'Fim',
                    'situacao': 'Situação',
                    'sala': 'Ambiente',
                    'professor': 'Professor',
                    'turma': 'Turma',
                    'intervalo_tela': 'Intervalo', 
                    'qtd_chromebooks': 'Chromebooks',
                    'qtd_notebooks': 'Notebooks'
                }),
                use_container_width=True, hide_index=True
            )
            
         
            st.markdown("###")
            col_d1, _ = st.columns([1,3])
            buf = gerar_imagem_ensalamento(df_view, filtro_data)
            col_d1.download_button("📥 Baixar Relatório (PNG)", data=buf, file_name=f"Ensalamento_{filtro_data}.png", mime="image/png")
            
        
            st.caption(f"Total Reservado: {df_view['qtd_chromebooks'].sum()} Chromebooks | {df_view['qtd_notebooks'].sum()} Notebooks")
        else:
            st.info("Nenhum agendamento encontrado.")
    


# TAB 3: COORDENAÇÃO (COM SEGURANÇA NA PLANILHA)

with tab3:
    if 'coord_logado' not in st.session_state: st.session_state['coord_logado'] = False
    
    if not st.session_state['coord_logado']:
        col1, col2, col3 = st.columns([1,1,1])
  
        with col2:
            st.markdown('<div class="login-box">', unsafe_allow_html=True)
            st.markdown("### Acesso Restrito")
            pwd = st.text_input("Senha", type="password", label_visibility="collapsed")
            
            if st.button("Entrar"):
                
                try:
                    senha_secreta = st.secrets["senha_coordenacao"]
                except:
                    st.error("ERRO: Senha da coordenação não configurada nos Secrets!")
                    st.stop()

                if pwd == senha_secreta: 
                    st.session_state['coord_logado'] = True
                    st.rerun()
                else: 
                    st.error("Senha incorreta")
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        c_head1, c_head2 = st.columns([4,1])
        c_head1.subheader("Gestão de Intervalos")
        if c_head2.button("Sair"): st.session_state['coord_logado'] = False; st.rerun()
        
        d_edit = st.date_input("Data para editar", key="d_coord")
        df_c = carregar_dados()
        
        if not df_c.empty:
            df_c['data'] = df_c['data'].astype(str)
            aulas = df_c[df_c['data'] == str(d_edit)]
            if not aulas.empty:
                opcoes = {f"{r['sala']} | {r['professor']} ({r['hora_inicio']}) ({r['hora_fim']}) ": i for i, r in aulas.iterrows()}
                escolha = st.selectbox("Selecione a aula:", list(opcoes.keys()))
                
                with st.form("edit_int"):
                    ci1, ci2 = st.columns(2)
                    n_ini = ci1.time_input("Início Intervalo", time(9,30))
                    n_fim = ci2.time_input("Fim Intervalo", time(9,50))
                    if st.form_submit_button("Salvar Intervalo"):
                        idx_real = opcoes[escolha] + 2 
                        sheet = conectar_google_sheets()
                        
                        headers = [h.lower().strip() for h in sheet.row_values(1)]
                        try:
                            c_ini = headers.index('inicio_intervalo') + 1
                            c_fim = headers.index('fim_intervalo') + 1
                            sheet.update_cell(idx_real, c_ini, str(n_ini)[:5])
                            sheet.update_cell(idx_real, c_fim, str(n_fim)[:5])
                            st.success("Intervalo salvo!")
                            st.cache_data.clear()
                        except: st.error("Colunas de intervalo não encontradas na planilha.")
            else: st.info("Sem aulas nesta data.")
        st.markdown('</div>', unsafe_allow_html=True)