import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, time
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import io

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Gestão de Salas", layout="wide")

# --- ESTOQUE TOTAL DE RECURSOS ---
TOTAL_CHROMEBOOKS = 34
TOTAL_NOTEBOOKS = 11

# --- CSS RESPONSIVO PARA SIDEBAR ---
st.markdown("""
<style>
/* ===== SIDEBAR GERAL ===== */
[data-testid="stSidebar"] { background-color: #87cefa; }

/* ===== DESKTOP ===== */
@media (min-width: 769px) {
    [data-testid="stSidebar"] { width: 380px !important; }
}
/* ===== MOBILE ===== */
@media (max-width: 768px) {
    [data-testid="stSidebar"] { width: 100% !important; }
}

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
    "Manhã": { "Turno Inteiro": (time(7, 0), time(12, 0)), "1º Horário": (time(7, 0), time(9, 30)), "2º Horário": (time(9, 30), time(12, 0)) },
    "Tarde": { "Turno Inteiro": (time(13, 0), time(17, 30)), "1º Horário": (time(13, 0), time(15, 15)), "2º Horário": (time(15, 15), time(17, 30)) },
    "Noite": { "Turno Inteiro": (time(18, 0), time(22, 0)), "1º Horário": (time(18, 0), time(20, 0)), "2º Horário": (time(20, 0), time(22, 0)) },
    "Integral": { "Turno Inteiro": (time(7, 0), time(17, 30)), "1º Horário": (time(7, 0), time(12, 0)), "2º Horário": (time(13, 0), time(17, 30)) }
}

# --- CONEXÃO COM GOOGLE SHEETS (FORÇA BRUTA) ---
@st.cache_resource
def conectar_google_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    if "gcp_service_account" in st.secrets:
        try:
            creds_dict = dict(st.secrets["gcp_service_account"])
            if "private_key" in creds_dict:
                creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            client = gspread.authorize(creds)
            return client.open("sistema_ensalamento_db").sheet1
        except Exception as e:
            st.error(f"Erro ao ler Segredos: {e}")
            st.stop()

    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        client = gspread.authorize(creds)
        return client.open("sistema_ensalamento_db").sheet1
    except:
        st.error("⚠️ ERRO CRÍTICO: Credenciais não encontradas.")
        st.stop()

# --- FUNÇÕES LÓGICAS ---
def carregar_dados():
    try:
        sheet = conectar_google_sheets()
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        
        if not df.empty:
            df.columns = df.columns.str.lower().str.strip()

        colunas_esperadas = [
            'data', 'turno', 'situacao', 'hora_inicio', 'hora_fim', 
            'sala', 'professor', 'turma', 'data_registro',
            'qtd_chromebooks', 'qtd_notebooks', 'inicio_intervalo', 'fim_intervalo'
        ]
        
        if df.empty:
            return pd.DataFrame(columns=colunas_esperadas)
        
        for col in colunas_esperadas:
            if col not in df.columns:
                df[col] = 0 if 'qtd' in col else ''
                
        df['qtd_chromebooks'] = pd.to_numeric(df['qtd_chromebooks'], errors='coerce').fillna(0)
        df['qtd_notebooks'] = pd.to_numeric(df['qtd_notebooks'], errors='coerce').fillna(0)
                
        return df
    except Exception as e:
        return pd.DataFrame()

def verificar_conflito_sala(df, sala, data_agendamento, inicio_novo, fim_novo):
    if df.empty: return False, ""
    df['data'] = df['data'].astype(str)
    conflitos = df[(df['sala'] == sala) & (df['data'] == str(data_agendamento))]
    
    for _, row in conflitos.iterrows():
        try:
            str_ini = str(row['hora_inicio'])[0:5]
            str_fim = str(row['hora_fim'])[0:5]
            ini_exist = datetime.strptime(str_ini, "%H:%M").time()
            fim_exist = datetime.strptime(str_fim, "%H:%M").time()
            
            if (inicio_novo < fim_exist) and (fim_novo > ini_exist):
                return True, f"Sala ocupada por {row['professor']} ({str_ini}-{str_fim})"
        except: continue
    return False, ""

def verificar_disponibilidade_recursos(df, data_agendamento, inicio_novo, fim_novo, qtd_chrome, qtd_note):
    if qtd_chrome == 0 and qtd_note == 0:
        return True, ""
    if df.empty: return True, ""
    
    df['data'] = df['data'].astype(str)
    agendamentos_dia = df[df['data'] == str(data_agendamento)]
    
    chrome_em_uso = 0
    note_em_uso = 0
    
    for _, row in agendamentos_dia.iterrows():
        try:
            str_ini = str(row['hora_inicio'])[0:5]
            str_fim = str(row['hora_fim'])[0:5]
            ini_exist = datetime.strptime(str_ini, "%H:%M").time()
            fim_exist = datetime.strptime(str_fim, "%H:%M").time()
            
            if (inicio_novo < fim_exist) and (fim_novo > ini_exist):
                chrome_em_uso += int(row['qtd_chromebooks'])
                note_em_uso += int(row['qtd_notebooks'])
        except: continue
        
    saldo_chrome = TOTAL_CHROMEBOOKS - chrome_em_uso
    saldo_note = TOTAL_NOTEBOOKS - note_em_uso
    
    msg_erro = []
    if qtd_chrome > saldo_chrome:
        msg_erro.append(f"Faltam Chromebooks! (Estoque: {TOTAL_CHROMEBOOKS}, Em uso: {chrome_em_uso}, Disponível: {saldo_chrome})")
    if qtd_note > saldo_note:
        msg_erro.append(f"Faltam Notebooks! (Estoque: {TOTAL_NOTEBOOKS}, Em uso: {note_em_uso}, Disponível: {saldo_note})")
        
    if msg_erro:
        return False, " | ".join(msg_erro)
        
    return True, ""

# --- GERADOR DE IMAGEM HD (LAYOUT ATUALIZADO: SEM HORAS, COM SITUAÇÃO E RECURSOS) ---
def gerar_imagem_ensalamento(df_filtrado, data_selecionada):
    plt.rcParams['font.family'] = 'DejaVu Sans'

    df_img = df_filtrado.copy()
    
    def formatar_intervalo(row):
        i = str(row['inicio_intervalo'])
        f = str(row['fim_intervalo'])
        if i and f and i != 'nan' and i != '0':
             return f"{i} - {f}"
        return "-"

    df_img['intervalo_fmt'] = df_img.apply(formatar_intervalo, axis=1)

    # --- DEFINIÇÃO DAS COLUNAS PARA A IMAGEM ---
    # Substituído hora_inicio/hora_fim pela 'situacao'
    # Adicionado qtd_chromebooks e qtd_notebooks
    colunas = ['turno', 'situacao', 'sala', 'professor', 'turma', 'intervalo_fmt', 'qtd_chromebooks', 'qtd_notebooks']
    df_final = df_img[colunas].copy()

    df_final.rename(columns={
        'turno': 'Turno',
        'situacao': 'Horário/Situação', # Nome mais descritivo
        'sala': 'Ambiente',
        'professor': 'Docente',
        'turma': 'Turma',
        'intervalo_fmt': 'Intervalo',
        'qtd_chromebooks': 'Chromes', # Abreviação para caber
        'qtd_notebooks': 'Notes'      # Abreviação para caber
    }, inplace=True)

    # Ajuste das larguras (Soma deve ser próxima de 1.0)
    # Turno: 0.08 | Situação: 0.12 | Sala: 0.20 | Prof: 0.20 | Turma: 0.15 | Intervalo: 0.11 | Chromes: 0.07 | Notes: 0.07
    col_widths = [0.08, 0.12, 0.20, 0.20, 0.15, 0.11, 0.07, 0.07]

    linhas = len(df_final)
    altura = max(6, 2.8 + linhas * 0.55)

    fig = plt.figure(figsize=(16, altura), dpi=300) # Aumentei largura para 16 para caber tudo

    ax_header = fig.add_axes([0.04, 0.80, 0.92, 0.18])
    ax_header.axis("off")

    try:
        logo = mpimg.imread("logo.png")
        ax_logo = fig.add_axes([0.04, 0.82, 0.28, 0.24])  
        ax_logo.imshow(logo)
        ax_logo.axis("off")
    except:
        pass

    data_str = data_selecionada.strftime('%d/%m/%Y')

    ax_header.text(0.55, 0.62, "ENSALAMENTO DIÁRIO", ha="center", va="center", fontsize=18, fontweight="bold", color="#004587")
    ax_header.text(0.55, 0.30, f"Data: {data_str}", ha="center", va="center", fontsize=13, color="#555555")

    ax_table = fig.add_axes([0.04, 0.10, 0.92, 0.62])
    ax_table.axis("off")

    tabela = ax_table.table(cellText=df_final.values, colLabels=df_final.columns, colWidths=col_widths, loc="upper center", cellLoc="center")
    tabela.auto_set_font_size(False)
    tabela.set_fontsize(9) # Fonte levemente menor para caber as 8 colunas
    tabela.scale(1, 1.4)

    for (r, c), cell in tabela.get_celld().items():
        cell.set_edgecolor("#c0c0c0")
        cell.set_linewidth(0.5)
        if r == 0:
            cell.set_facecolor("#005CAA")
            cell.set_text_props(color="white", weight="bold")
        else:
            # PINTURA DE INTERVALO
            try:
                # Docente agora é a coluna index 3 (0=Turno, 1=Sit, 2=Sala, 3=Prof...)
                nome_professor = str(df_final.iloc[r-1]['Docente']).upper()
                if "INTERVALO" in nome_professor:
                    cell.set_facecolor("#FFFACD") # Amarelo Claro
                    cell.set_text_props(weight='bold', color="#555")
                else:
                    cell.set_facecolor("#f5f7fa" if r % 2 == 0 else "white")
            except:
                cell.set_facecolor("white")

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
st.markdown("---")

tab1, tab2, tab3 = st.tabs(["Novo Agendamento", "Visualizar Agenda", "🔐 Coordenação"])

# --- TAB 1: AGENDAMENTO PADRÃO ---
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
            turno = st.selectbox("Turno", ["Manhã", "Tarde", "Noite", "Integral"])
            situacao = st.radio("Ocupação do Turno", ["Turno Inteiro", "1º Horário", "2º Horário"], horizontal=True)
            
            try:
                h_padrao_ini, h_padrao_fim = HORARIOS_TURNO[turno][situacao]
            except:
                h_padrao_ini, h_padrao_fim = time(0,0), time(0,0)
                
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
        btn_agendar = st.form_submit_button("Salvar Agendamento", use_container_width=True)

        if btn_agendar:
            if not professor or not turma:
                st.warning("⚠️ Preencha Professor e Turma.")
            else:
                df_atual = carregar_dados()
                conflito_sala, msg_sala = verificar_conflito_sala(df_atual, sala, data, hora_inicio, hora_fim)
                tem_recurso, msg_recurso = verificar_disponibilidade_recursos(df_atual, data, hora_inicio, hora_fim, qtd_chrome, qtd_note)
                
                if conflito_sala:
                    st.error(f"❌ {msg_sala}")
                elif not tem_recurso:
                    st.error(f"❌ {msg_recurso}")
                else:
                    nova_linha = [str(data), turno, situacao, str(hora_inicio)[0:5], str(hora_fim)[0:5], sala, professor, turma, str(datetime.now()), qtd_chrome, qtd_note, "", ""]
                    sheet = conectar_google_sheets()
                    sheet.append_row(nova_linha)
                    st.success(f"✅ Agendado com Sucesso!")
                    st.cache_data.clear()

# --- TAB 2: VISUALIZAÇÃO (ATUALIZADO) ---
with tab2:
    st.subheader("Quadro de Horários")
    c1, c2, c3 = st.columns(3)
    filtro_data = c1.date_input("Filtrar Data", value=datetime.today())
    
    opcoes_filtro = ["Manhã", "Tarde", "Noite", "Integral"]
    filtro_turno = c2.multiselect("Filtrar Turno", options=opcoes_filtro, default=opcoes_filtro)
    
    if c3.button("🔄 Atualizar"): st.cache_data.clear()

    df = carregar_dados()
    if not df.empty:
        df['data'] = df['data'].astype(str)
        df_view = df[df['data'] == str(filtro_data)]
        
        if filtro_turno:
            df_view = df_view[df_view['turno'].isin(filtro_turno)]
            
        if not df_view.empty:
            df_view = df_view.sort_values(by='hora_inicio')
            
            # --- ATUALIZAÇÃO DA TABELA NA TELA ---
            # Adicionado 'situacao', 'qtd_chromebooks', 'qtd_notebooks'
            # Mantive hora_inicio/fim aqui pois na tela cabe e é útil para detalhes
            cols = ['hora_inicio', 'hora_fim', 'situacao', 'turno', 'sala', 'professor', 'turma', 'inicio_intervalo', 'fim_intervalo', 'qtd_chromebooks', 'qtd_notebooks']
            df_visualizacao = df_view[cols].copy()
            df_visualizacao.rename(columns={
                'hora_inicio': 'Início', 'hora_fim': 'Fim', 'situacao': 'Situação', 'turno': 'Turno', 'sala': 'Ambiente', 
                'professor': 'Docente', 'turma': 'Turma', 
                'inicio_intervalo': 'Ini. Intervalo', 'fim_intervalo': 'Fim Intervalo',
                'qtd_chromebooks': 'Chromebooks', 'qtd_notebooks': 'Notebooks'
            }, inplace=True)
            
            st.dataframe(df_visualizacao, use_container_width=True, hide_index=True)
            
            st.markdown("###")
            col_d1, col_d2 = st.columns([1, 4])
            with st.spinner("Gerando imagem HD..."):
                imagem_buffer = gerar_imagem_ensalamento(df_view, filtro_data)
            col_d1.download_button("Baixar Relatorio (PNG)", data=imagem_buffer, file_name=f"Ensalamento_{filtro_data}.png", mime="image/png")
            
            # Totalizadores simples no rodapé da tabela
            total_c = df_view['qtd_chromebooks'].sum()
            total_n = df_view['qtd_notebooks'].sum()
            if total_c > 0 or total_n > 0:
                st.caption(f"📊 Total Reservado no dia: {total_c} Chromebooks e {total_n} Notebooks.")

        else: st.info("Nenhum agendamento para os turnos selecionados.")
    else: st.info("Banco de dados vazio.")

# --- TAB 3: ÁREA RESTRICTA (COORDENAÇÃO) ---
with tab3:
    st.header("Área Restrita da Coordenação - Definição de Intervalos")
    
    if 'coord_logado' not in st.session_state:
        st.session_state['coord_logado'] = False

    if not st.session_state['coord_logado']:
        senha_input = st.text_input("Digite a Senha de Acesso:", type="password")
        if st.button("Acessar Painel"):
            if senha_input == "#ESS2026":
                st.session_state['coord_logado'] = True
                st.rerun()
            else:
                st.error("Senha Incorreta.")
    else:
        st.success("🔓 Modo Coordenação Ativo")
        if st.button("Sair"):
            st.session_state['coord_logado'] = False
            st.rerun()
            
        st.markdown("---")
        st.subheader("Atribuir Intervalo à Aula Existente")
        
        coord_data = st.date_input("Selecione a Data da Aula", key="data_coord_edit")
        
        df_coord = carregar_dados()
        
        if not df_coord.empty:
            df_coord['data'] = df_coord['data'].astype(str)
            aulas_dia = df_coord[df_coord['data'] == str(coord_data)]
            
            if aulas_dia.empty:
                st.info("Não há aulas agendadas para esta data.")
            else:
                opcoes_aulas = []
                for index, row in aulas_dia.iterrows():
                    label = f"{row['sala']} | Prof. {row['professor']} ({row['hora_inicio']} - {row['hora_fim']})"
                    opcoes_aulas.append({'label': label, 'index': index})
                
                aula_selecionada = st.selectbox(
                    "Selecione a Aula:", 
                    options=opcoes_aulas, 
                    format_func=lambda x: x['label']
                )
                
                st.info(f"Definindo intervalo para: **{aula_selecionada['label']}**")
                
                with st.form("form_intervalo_update"):
                    c_h1, c_h2 = st.columns(2)
                    int_ini = c_h1.time_input("Início Intervalo", value=time(9,30))
                    int_fim = c_h2.time_input("Fim Intervalo", value=time(9,50))
                    
                    btn_save_interval = st.form_submit_button("Salvar Intervalo na Aula")
                    
                    if btn_save_interval:
                        try:
                            sheet = conectar_google_sheets()
                            linha_para_editar = aula_selecionada['index'] + 2
                            
                            headers = sheet.row_values(1)
                            headers = [h.lower().strip() for h in headers]
                            
                            if 'inicio_intervalo' in headers and 'fim_intervalo' in headers:
                                col_idx_ini = headers.index('inicio_intervalo') + 1
                                col_idx_fim = headers.index('fim_intervalo') + 1
                                
                                sheet.update_cell(linha_para_editar, col_idx_ini, str(int_ini)[0:5])
                                sheet.update_cell(linha_para_editar, col_idx_fim, str(int_fim)[0:5])
                                
                                st.success("✅ Intervalo atualizado com sucesso!")
                                st.cache_data.clear()
                            else:
                                st.error("ERRO: Colunas 'inicio_intervalo' e 'fim_intervalo' não encontradas. Adicione-as na planilha.")
                            
                        except Exception as e:
                            st.error(f"Erro ao atualizar: {e}")