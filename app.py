import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, time
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import io
import json

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Gestão de Salas", layout="wide")

# --- ESTOQUE TOTAL DE RECURSOS ---
TOTAL_CHROMEBOOKS = 34
TOTAL_NOTEBOOKS = 11

# --- CSS RESPONSIVO PARA SIDEBAR ---
st.markdown("""
<style>
[data-testid="stSidebar"] { background-color: #d3d3d3; }
@media (min-width: 769px) { [data-testid="stSidebar"] { width: 380px !important; } }
@media (max-width: 768px) { [data-testid="stSidebar"] { width: 100% !important; } }
.sidebar-logo { margin-top: -20px; margin-bottom: 20px; }
.sidebar-img { margin-bottom: 12px; }
</style>
""", unsafe_allow_html=True)

# --- LISTAS DE DADOS ---
LISTA_SALAS = sorted([
    "SALA DE AULA 24", "SALA DE AULA 25", "SALA DE AULA 49", "SALA DE AULA 55", 
    "SALA DE AULA 56", "SALA DE AULA 61", "SALA DE AULA 62", "SALA DE AULA 63", 
    "SALA DE AULA 73", "SALA DE AULA 72", "SALA DE AULA 71", 
    "LAB. DE INFORMÁTICA 31", "LAB. DE INFORMÁTICA 48", "LAB. DE INFORMÁTICA 74", 
    "LAB. DE INFORMÁTICA 75", "LAB. DE REDES DE DISTRIBUIÇÃO 84", 
    "GALPÃO DE EDIFICAÇÕES 51", "GALPÃO DE ELÉTRICA 52", 
    "GALPÃO DE ENERGIA RENOVÁVEL 53", "SALA DE ACOLHIMENTO 60"
])

HORARIOS_TURNO = {
    "Manhã": { "Completo": (time(7, 0), time(12, 0)), "1º Horário": (time(7, 0), time(9, 30)), "2º Horário": (time(9, 30), time(12, 0)) },
    "Tarde": { "Completo": (time(13, 0), time(17, 30)), "1º Horário": (time(13, 0), time(15, 15)), "2º Horário": (time(15, 15), time(17, 30)) },
    "Noite": { "Completo": (time(18, 0), time(22, 0)), "1º Horário": (time(18, 0), time(20, 0)), "2º Horário": (time(20, 0), time(22, 0)) }
}

# --- CONEXÃO COM GOOGLE SHEETS (ESTRATÉGIA JSON COMPLETO) ---
@st.cache_resource
def conectar_google_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # 1. Tenta conectar via Streamlit Cloud (Segredos)
    if "gcp_service_account" in st.secrets:
        try:
            # Pega o conteúdo JSON inteiro que colaremos nos segredos
            json_conteudo = st.secrets["gcp_service_account"]["json_file"]
            
            # Transforma o texto em dicionário Python
            creds_dict = json.loads(json_conteudo)
            
            # Cria as credenciais
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        except Exception as e:
            st.error(f"Erro ao ler o segredo JSON: {e}")
            st.stop()
            
    # 2. Se falhar (ou estiver local), tenta o arquivo físico
    else:
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        
    client = gspread.authorize(creds)
    return client.open("sistema_ensalamento_db").sheet1 

# --- FUNÇÕES LÓGICAS ---
def carregar_dados():
    # CORREÇÃO: Chama a conexão AQUI dentro para não dar erro de variável inexistente
    try:
        sheet = conectar_google_sheets()
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        
        colunas_esperadas = ['data', 'turno', 'situacao', 'hora_inicio', 'hora_fim', 'sala', 'professor', 'turma', 'data_registro', 'qtd_chromebooks', 'qtd_notebooks']
        
        if df.empty: return pd.DataFrame(columns=colunas_esperadas)
        
        for col in colunas_esperadas:
            if col not in df.columns: df[col] = 0 if 'qtd' in col else '-'
            
        df['qtd_chromebooks'] = pd.to_numeric(df['qtd_chromebooks'], errors='coerce').fillna(0)
        df['qtd_notebooks'] = pd.to_numeric(df['qtd_notebooks'], errors='coerce').fillna(0)
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()

def verificar_conflito_sala(df, sala, data_agendamento, inicio_novo, fim_novo):
    if df.empty: return False, ""
    df['data'] = df['data'].astype(str)
    conflitos = df[(df['sala'] == sala) & (df['data'] == str(data_agendamento))]
    for _, row in conflitos.iterrows():
        try:
            ini_exist = datetime.strptime(str(row['hora_inicio'])[0:5], "%H:%M").time()
            fim_exist = datetime.strptime(str(row['hora_fim'])[0:5], "%H:%M").time()
            if (inicio_novo < fim_exist) and (fim_novo > ini_exist):
                return True, f"Sala ocupada por {row['professor']} ({row['hora_inicio']}-{row['hora_fim']})"
        except: continue
    return False, ""

def verificar_disponibilidade_recursos(df, data_agendamento, inicio_novo, fim_novo, qtd_chrome, qtd_note):
    if qtd_chrome == 0 and qtd_note == 0: return True, ""
    if df.empty: return True, ""
    df['data'] = df['data'].astype(str)
    agendamentos_dia = df[df['data'] == str(data_agendamento)]
    chrome_em_uso = 0
    note_em_uso = 0
    for _, row in agendamentos_dia.iterrows():
        try:
            ini_exist = datetime.strptime(str(row['hora_inicio'])[0:5], "%H:%M").time()
            fim_exist = datetime.strptime(str(row['hora_fim'])[0:5], "%H:%M").time()
            if (inicio_novo < fim_exist) and (fim_novo > ini_exist):
                chrome_em_uso += int(row['qtd_chromebooks'])
                note_em_uso += int(row['qtd_notebooks'])
        except: continue
    saldo_chrome = TOTAL_CHROMEBOOKS - chrome_em_uso
    saldo_note = TOTAL_NOTEBOOKS - note_em_uso
    msg_erro = []
    if qtd_chrome > saldo_chrome: msg_erro.append(f"Faltam Chromebooks! (Disp: {saldo_chrome})")
    if qtd_note > saldo_note: msg_erro.append(f"Faltam Notebooks! (Disp: {saldo_note})")
    if msg_erro: return False, " | ".join(msg_erro)
    return True, ""

# --- GERADOR DE IMAGEM HD ---
def gerar_imagem_ensalamento(df_filtrado, data_selecionada):
    plt.rcParams['font.family'] = 'DejaVu Sans'
    colunas = ['hora_inicio', 'hora_fim', 'sala', 'professor', 'turma', 'situacao']
    df = df_filtrado[colunas].copy()
    df.rename(columns={'hora_inicio': 'Início', 'hora_fim': 'Fim', 'sala': 'Ambiente', 'professor': 'Docente', 'turma': 'Turma', 'situacao': 'Detalhe'}, inplace=True)
    col_widths = [0.10, 0.10, 0.26, 0.22, 0.20, 0.12]
    linhas = len(df)
    altura = 2.6 + linhas * 0.5
    fig = plt.figure(figsize=(12, altura), dpi=300)
    ax_header = fig.add_axes([0.04, 0.80, 0.92, 0.18])
    ax_header.axis("off")
    try:
        logo = mpimg.imread("logo.png")
        h, w, _ = logo.shape
        proporcao = w / h
        altura_logo = 0.75
        largura_logo = altura_logo * proporcao
        ax_header.imshow(logo, extent=[0.0, largura_logo, 0.15, 0.15 + altura_logo], aspect='equal')
    except: pass
    data_str = data_selecionada.strftime('%d/%m/%Y')
    ax_header.text(0.55, 0.62, "ENSALAMENTO DIÁRIO", ha="center", va="center", fontsize=18, fontweight="bold", color="#004587")
    ax_header.text(0.55, 0.30, f"Data: {data_str}", ha="center", va="center", fontsize=13, color="#555555")
    ax_table = fig.add_axes([0.04, 0.05, 0.92, 0.70])
    ax_table.axis("off")
    tabela = ax_table.table(cellText=df.values, colLabels=df.columns, colWidths=col_widths, loc="upper center", cellLoc="center")
    tabela.auto_set_font_size(False)
    tabela.set_fontsize(11)
    tabela.scale(1, 1.4)
    for (r, c), cell in tabela.get_celld().items():
        cell.set_edgecolor("#c0c0c0")
        cell.set_linewidth(0.5)
        if r == 0:
            cell.set_facecolor("#005CAA")
            cell.set_text_props(color="white", weight="bold")
        else:
            cell.set_facecolor("#f5f7fa" if r % 2 == 0 else "white")
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=300, pad_inches=0.2)
    buf.seek(0)
    plt.close(fig)
    return buf

# --- INTERFACE ---
with st.sidebar:
    st.markdown('<div class="sidebar-logo">', unsafe_allow_html=True)
    try: st.image("logo.png", use_container_width=True)
    except: st.warning("Logo não encontrada")
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("---")
    try:
        st.image("1.png", use_container_width=True)
        st.image("2.png", use_container_width=True)
        st.image("3.png", use_container_width=True)
    except: pass

st.title("Gestão de Salas")
msg_placeholder = st.empty()
st.markdown("---")

tab1, tab2 = st.tabs(["📝 Novo Agendamento", "📊 Visualizar Agenda"])

with tab1:
    with st.form("form_agendamento"):
        st.subheader("Dados da Aula")
        col_a, col_b = st.columns(2)
        with col_a:
            professor = st.text_input("Nome do Professor")
            turma = st.text_input("Turma/Curso")
            sala = st.selectbox("Ambiente / Sala", LISTA_SALAS)
            data = st.date_input("Data da Aula")
        with col_b:
            turno = st.selectbox("Turno", ["Manhã", "Tarde", "Noite"])
            situacao = st.radio("Ocupação do Turno", ["Completo", "1º Horário", "2º Horário"], horizontal=True)
            h_padrao_ini, h_padrao_fim = HORARIOS_TURNO[turno][situacao]
            col_h1, col_h2 = st.columns(2)
            hora_inicio = col_h1.time_input("Início", value=h_padrao_ini)
            hora_fim = col_h2.time_input("Fim", value=h_padrao_fim)

        st.markdown("---")
        st.subheader("Recursos Móveis (Opcional)")
        st.info(f"Estoque Total: {TOTAL_CHROMEBOOKS} Chromebooks | {TOTAL_NOTEBOOKS} Notebooks")
        col_r1, col_r2 = st.columns(2)
        qtd_chrome = col_r1.number_input("Qtd. Chromebooks", min_value=0, max_value=TOTAL_CHROMEBOOKS, step=1)
        qtd_note = col_r2.number_input("Qtd. Notebooks (Prof)", min_value=0, max_value=TOTAL_NOTEBOOKS, step=1)
        
        st.markdown("---")
        btn_agendar = st.form_submit_button("💾 Salvar Agendamento", use_container_width=True)

        if btn_agendar:
            msg_placeholder.empty()
            if not professor or not turma:
                msg_placeholder.warning("⚠️ Preencha Professor e Turma.")
                st.toast("Preencha os campos obrigatórios!", icon="⚠️")
            else:
                # Carrega dados chamando a conexão diretamente
                df_atual = carregar_dados()
                conflito_sala, msg_sala = verificar_conflito_sala(df_atual, sala, data, hora_inicio, hora_fim)
                tem_recurso, msg_recurso = verificar_disponibilidade_recursos(df_atual, data, hora_inicio, hora_fim, qtd_chrome, qtd_note)
                if conflito_sala:
                    msg_placeholder.error(f"❌ {msg_sala}")
                    st.toast("Conflito de Sala!", icon="🚫")
                elif not tem_recurso:
                    msg_placeholder.error(f"❌ {msg_recurso}")
                    st.toast("Recursos Insuficientes!", icon="💻")
                else:
                    nova_linha = [str(data), turno, situacao, str(hora_inicio)[0:5], str(hora_fim)[0:5], sala, professor, turma, str(datetime.now()), qtd_chrome, qtd_note]
                    
                    # Conecta novamente apenas para garantir a gravação
                    sheet = conectar_google_sheets()
                    sheet.append_row(nova_linha)
                    
                    msg_placeholder.success(f"✅ Agendamento Confirmado! {professor} - {sala}")
                    st.toast("Salvo com sucesso!", icon="🎉")
                    st.cache_data.clear()

with tab2:
    st.subheader("📅 Quadro de Horários")
    c1, c2, c3 = st.columns(3)
    filtro_data = c1.date_input("Filtrar Data", value=datetime.today())
    filtro_turno = c2.selectbox("Filtrar Turno", ["Todos", "Manhã", "Tarde", "Noite"])
    if c3.button("🔄 Atualizar"): st.cache_data.clear()

    df = carregar_dados()
    if not df.empty:
        df['data'] = df['data'].astype(str)
        df_view = df[df['data'] == str(filtro_data)]
        if filtro_turno != "Todos": df_view = df_view[df_view['turno'] == filtro_turno]
        if not df_view.empty:
            df_view = df_view.sort_values(by='hora_inicio')
            
            st.markdown("###")
            col_d1, col_d2 = st.columns([1, 4])
            with st.spinner("Gerando imagem HD..."):
                imagem_buffer = gerar_imagem_ensalamento(df_view, filtro_data)
            col_d1.download_button("📥 Baixar Imagem", data=imagem_buffer, file_name=f"Ensalamento_{filtro_data}.png", mime="image/png")

            cols = ['hora_inicio', 'hora_fim', 'sala', 'professor', 'situacao', 'turma', 'qtd_chromebooks', 'qtd_notebooks']
            df_vis = df_view[cols].copy()
            df_vis.rename(columns={'hora_inicio': '🕒 Início', 'hora_fim': '🕒 Fim', 'sala': '🏫 Ambiente', 'professor': '👨‍🏫 Docente', 'situacao': '📌 Detalhe', 'turma': '🎓 Turma', 'qtd_chromebooks': '💻 Chromebooks', 'qtd_notebooks': '💻 Notebooks'}, inplace=True)
            st.dataframe(df_vis, use_container_width=True, hide_index=True)
            
            total_c = df_view['qtd_chromebooks'].sum()
            total_n = df_view['qtd_notebooks'].sum()
            if total_c > 0 or total_n > 0: st.caption(f"📊 Total reservado: {total_c} Chromebooks e {total_n} Notebooks.")
        else: st.info("Nenhum agendamento.")
    else: st.info("Banco de dados vazio.")