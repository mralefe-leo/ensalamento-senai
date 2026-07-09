import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import io
import textwrap

def gerar_imagem_ensalamento(df_filtrado, data_selecionada):
    plt.rcParams['font.family'] = 'DejaVu Sans'

    df_img = df_filtrado.copy()

    if 'inicio_intervalo' in df_img.columns:
        df_img = df_img.sort_values(by=['inicio_intervalo', 'hora_inicio'], ascending=[True, True])

    df_img['intervalo_fmt'] = df_img.apply(
        lambda r: f"{str(r['inicio_intervalo'])}-{str(r['fim_intervalo'])}" if r['inicio_intervalo'] and str(r['inicio_intervalo']).strip() != "" else "-",
        axis=1
    )

    df_img['recursos'] = df_img.apply(
        lambda r: f"C:{int(r['qtd_chromebooks'])} | N:{int(r['qtd_notebooks'])}",
        axis=1
    )

    width_docente = 18
    width_turma = 25
    width_ambiente = 25

    def advanced_wrap_indent(text, width, pad="   "):
        lines = textwrap.wrap(str(text), width=width)
        if not lines: return ""
        padded_lines = [f"{pad}{line}" for line in lines]
        return "\n".join(padded_lines)

    df_img['turma'] = df_img['turma'].apply(lambda x: advanced_wrap_indent(x, width_turma))
    df_img['professor'] = df_img['professor'].apply(lambda x: advanced_wrap_indent(x, width_docente))
    df_img['sala'] = df_img['sala'].apply(lambda x: advanced_wrap_indent(x, width_ambiente))

    colunas_map = {
        'turno': 'Turno', 'sala': 'Ambiente', 'professor': 'Docente',
        'turma': 'Turma', 'qtd_alunos': 'Alunos', 'intervalo_fmt': 'Intervalo',
        'recursos': 'Recursos'
    }

    cols_to_use = [c for c in colunas_map.keys() if c in df_img.columns]
    df_final = df_img[cols_to_use].rename(columns=colunas_map)

    num_linhas = len(df_final)
    altura_cabecalho = 2.2 
    altura_linha = 0.45    
    altura_tabela = (num_linhas + 1) * altura_linha 
    fig_height = max(5.0, altura_cabecalho + altura_tabela + 0.3) 
    
    fig = plt.figure(figsize=(11.5, fig_height), dpi=300)
    
    ax_logo = fig.add_axes([0, 1.0 - (0.9 / fig_height), 1, 0.7 / fig_height])
    ax_logo.axis('off')
    try:
        logo = mpimg.imread("assets/logo.png") # Caminho já atualizado!
        ax_logo.imshow(logo)
    except:
        ax_logo.text(0.5, 0.5, "SENAI HUB", fontsize=24, ha="center", va="center", weight="bold")

    ax_titulo = fig.add_axes([0, 1.0 - (1.5 / fig_height), 1, 0.5 / fig_height])
    ax_titulo.axis('off')
    ax_titulo.text(0.5, 0.5, "ENSALAMENTO DIÁRIO", fontsize=20, fontweight="bold", ha="center", va="center", color="#004587")

    ax_data = fig.add_axes([0, 1.0 - (1.95 / fig_height), 1, 0.35 / fig_height])
    ax_data.axis('off')
    ax_data.text(0.5, 0.5, f"Data: {data_selecionada.strftime('%d/%m/%Y')}", fontsize=14, ha="center", va="center", color="#444")

    margem_inferior = 0.05 / fig_height
    altura_tab_frac = (altura_tabela + 0.1) / fig_height
    ax_tab = fig.add_axes([0.02, margem_inferior, 0.96, altura_tab_frac])
    ax_tab.axis('off')

    tabela = ax_tab.table(
        cellText=df_final.values, colLabels=df_final.columns, loc='center', cellLoc='center', bbox=[0, 0, 1, 1] 
    )

    tabela.auto_set_font_size(False)
    tabela.set_fontsize(11)

    larguras = {
        'Turno': 0.07, 'Ambiente': 0.22, 'Docente': 0.20, 'Turma': 0.25, 
        'Alunos': 0.06, 'Intervalo': 0.09, 'Recursos': 0.09
    }

    for (r, c), cell in tabela.get_celld().items():
        try:
            col_name = df_final.columns[c]
            if col_name in larguras: cell.set_width(larguras[col_name])
        except: pass

        cell.set_linewidth(0.5)
        cell.set_edgecolor("#cccccc")

        if r == 0:
            cell.set_facecolor("#004587")
            cell.set_text_props(color="white", weight="bold", fontsize=12)
            cell.get_text().set_ha('center') 
        else:
            cell.set_facecolor("#E6F0FA" if r % 2 == 0 else "white")
            if col_name in ['Ambiente', 'Docente', 'Turma']: cell.get_text().set_ha('left')

    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight", pad_inches=0.1) 
    buf.seek(0)
    plt.close(fig)

    return buf