import streamlit as st
import pandas as pd
import io
from datetime import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="KPIs Cabify Aeropuerto", layout="wide", page_icon="🟣")

# --- COLORES CABIFY (Referencia) ---
CABIFY_PURPLE = '#7145D6'
CABIFY_WHITE = '#FFFFFF'

# --- FUNCIONES AUXILIARES ---
def limpiar_nombre_desde_email(email):
    if not isinstance(email, str):
        return "Desconocido"
    user_part = email.split('@')[0]
    name_parts = user_part.split('.')
    clean_name = " ".join([part.capitalize() for part in name_parts])
    return clean_name

def generar_excel_cabify(df_supervisores, df_anfitriones):
    """Genera un archivo Excel con formato y colores corporativos"""
    output = io.BytesIO()
    workbook = st.writer = pd.ExcelWriter(output, engine='xlsxwriter')
    
    # Formatos
    wb = workbook.book
    header_fmt = wb.add_format({
        'bold': True,
        'font_color': CABIFY_WHITE,
        'bg_color': CABIFY_PURPLE,
        'border': 1,
        'align': 'center',
        'valign': 'vcenter'
    })
    body_fmt = wb.add_format({'border': 1, 'align': 'center'})
    text_fmt = wb.add_format({'border': 1, 'align': 'left'})
    
    # --- HOJA 1: RESUMEN GENERAL ---
    sheet_name1 = "Resumen Supervisores"
    df_supervisores.to_excel(workbook, sheet_name=sheet_name1, index=False, startrow=1)
    ws1 = workbook.sheets[sheet_name1]
    
    # Aplicar formatos Hoja 1
    ws1.set_column('A:A', 35, text_fmt) # Columna Supervisor ancha
    ws1.set_column('B:B', 20, body_fmt) # Numeros
    # Escribir headers manualmente para dar formato
    for col_num, value in enumerate(df_supervisores.columns.values):
        ws1.write(0, col_num, value, header_fmt)

    # --- HOJA 2: DETALLE ANFITRIONES ---
    sheet_name2 = "Detalle Anfitriones"
    df_anfitriones.to_excel(workbook, sheet_name=sheet_name2, index=False, startrow=1)
    ws2 = workbook.sheets[sheet_name2]
    
    # Aplicar formatos Hoja 2
    ws2.set_column('A:A', 35, text_fmt) # Supervisor
    ws2.set_column('B:B', 30, text_fmt) # Anfitrion
    ws2.set_column('C:C', 15, body_fmt) # Inspecciones
    # Escribir headers
    for col_num, value in enumerate(df_anfitriones.columns.values):
        ws2.write(0, col_num, value, header_fmt)
        
    workbook.close()
    return output.getvalue()

# --- INICIALIZACIÓN DE ESTADO ---
if 'lista_supervisores' not in st.session_state:
    st.session_state['lista_supervisores'] = [
        "LUIS LEONARDO ALARCON MEDRANO",
        "ANA ESTEFANIA JIMENEZ LEZAMA",
        "GERALDINE CRISTINA GUTIERREZ BRICENO"
    ]
if 'mapa_anfitriones' not in st.session_state:
    st.session_state['mapa_anfitriones'] = {}
# Nuevos estados para filtros y unificación
if 'excluidos' not in st.session_state:
    st.session_state['excluidos'] = []
if 'unificaciones' not in st.session_state:
    st.session_state['unificaciones'] = {} # { 'Nombre Viejo': 'Nombre Nuevo' }

# --- BARRA LATERAL ---
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/e/e3/Cabify_Logo.svg/2560px-Cabify_Logo.svg.png", width=150)
st.sidebar.title("Configuración")

uploaded_file = st.sidebar.file_uploader("1. Cargar Reporte (CSV/XLSX)", type=['csv', 'xlsx'])

# --- LÓGICA DE PROCESAMIENTO INICIAL ---
df_base = pd.DataFrame()
if uploaded_file is not None:
    # Carga de datos
    if uploaded_file.name.endswith('.csv'):
        df_base = pd.read_csv(uploaded_file)
    else:
        df_base = pd.read_excel(uploaded_file)
    
    # Normalización básica
    col_email = "Dirección de correo electrónico"
    if 'Fecha' in df_base.columns:
        col_fecha = 'Fecha'
    elif 'Marca temporal' in df_base.columns:
        col_fecha = 'Marca temporal'
    else:
        st.error("Falta columna de fecha.")
        st.stop()
        
    df_base[col_fecha] = pd.to_datetime(df_base[col_fecha])
    df_base['Anfitrión_Original'] = df_base[col_email].apply(limpiar_nombre_desde_email)
    
    # LISTA DE TODOS LOS NOMBRES DETECTADOS (para los selectores)
    todos_anfitriones = sorted(df_base['Anfitrión_Original'].unique())

    # --- GESTIÓN AVANZADA EN SIDEBAR ---
    st.sidebar.markdown("---")
    st.sidebar.header("🛠️ Limpieza de Datos")

    # 1. EXCLUIR REGISTROS
    st.sidebar.subheader("1. Eliminar/Excluir")
    excluidos_sel = st.sidebar.multiselect(
        "Selecciona personas a ignorar (Supervisores, pruebas, etc.):",
        options=todos_anfitriones,
        default=st.session_state['excluidos']
    )
    st.session_state['excluidos'] = excluidos_sel

    # 2. UNIFICAR REGISTROS
    st.sidebar.subheader("2. Agrupar/Unificar")
    st.sidebar.info("Si una persona tiene 2 correos, selecciona el secundario y agrúpalo al principal.")
    
    # Filtramos para no mostrar los ya excluidos en la unificación
    candidatos_unificar = [x for x in todos_anfitriones if x not in st.session_state['excluidos']]
    
    col_u1, col_u2 = st.sidebar.columns(2)
    origen = col_u1.selectbox("Secundario (Alias)", ["-"] + candidatos_unificar)
    destino = col_u2.selectbox("Principal (Destino)", ["-"] + candidatos_unificar)
    
    if st.sidebar.button("Unificar"):
        if origen != "-" and destino != "-" and origen != destino:
            st.session_state['unificaciones'][origen] = destino
            st.success(f"{origen} -> {destino}")
            st.rerun()

    # Mostrar unificaciones activas y permitir borrar
    if st.session_state['unificaciones']:
        st.sidebar.write("Reglas activas:")
        for k, v in list(st.session_state['unificaciones'].items()):
            c1, c2 = st.sidebar.columns([0.8, 0.2])
            c1.caption(f"{k} ➡️ {v}")
            if c2.button("❌", key=f"del_{k}"):
                del st.session_state['unificaciones'][k]
                st.rerun()

    # --- APLICACIÓN DE FILTROS AL DATAFRAME ---
    # 1. Aplicar exclusiones
    df_clean = df_base[~df_base['Anfitrión_Original'].isin(st.session_state['excluidos'])].copy()
    
    # 2. Aplicar unificaciones
    # Creamos columna final 'Anfitrión' reemplazando según el mapa
    df_clean['Anfitrión'] = df_clean['Anfitrión_Original'].replace(st.session_state['unificaciones'])

    # --- FILTRO DE FECHAS ---
    st.sidebar.markdown("---")
    min_date = df_clean[col_fecha].min().date()
    max_date = df_clean[col_fecha].max().date()
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        fecha_inicio = st.date_input("Fecha Desde", min_date)
    with col_f2:
        fecha_fin = st.date_input("Fecha Hasta", max_date)

    mask = (df_clean[col_fecha].dt.date >= fecha_inicio) & (df_clean[col_fecha].dt.date <= fecha_fin)
    df_final = df_clean.loc[mask]

# --- INTERFAZ PRINCIPAL ---
st.title("🟣 KPI Anfitriones Aeropuerto")

if uploaded_file is None:
    st.info("Carga el archivo para comenzar.")
    st.stop()

# --- ASIGNACIÓN DE SUPERVISORES (Sobre los nombres ya limpios y unificados) ---
st.markdown("### 1. Asignación de Supervisores")
anfitriones_finales = sorted(df_final['Anfitrión'].unique())

with st.expander("Panel de Asignación (Click para abrir/cerrar)", expanded=True):
    # Gestión de lista de supervisores
    new_sup = st.text_input("Añadir nuevo supervisor (opcional):")
    if st.button("Agregar") and new_sup:
        st.session_state['lista_supervisores'].append(new_sup.upper())
        st.rerun()
        
    cols = st.columns(3)
    for i, anfitrion in enumerate(anfitriones_finales):
        idx_seleccion = 0
        current = st.session_state['mapa_anfitriones'].get(anfitrion)
        if current in st.session_state['lista_supervisores']:
            idx_seleccion = st.session_state['lista_supervisores'].index(current)
            
        sup_sel = cols[i % 3].selectbox(
            f"{anfitrion}", 
            st.session_state['lista_supervisores'],
            index=idx_seleccion,
            key=f"sup_{anfitrion}"
        )
        st.session_state['mapa_anfitriones'][anfitrion] = sup_sel

# Mapear
df_final['Supervisor'] = df_final['Anfitrión'].map(st.session_state['mapa_anfitriones'])

# --- RESULTADOS ---
st.markdown("---")
st.subheader("📊 Reporte de Gestión")

# Generar tablas
resumen_supervisor = df_final.groupby('Supervisor').size().reset_index(name='Total Inspecciones').sort_values('Total Inspecciones', ascending=False)
resumen_anfitrion = df_final.groupby(['Supervisor', 'Anfitrión']).size().reset_index(name='Inspecciones').sort_values(['Supervisor', 'Inspecciones'], ascending=[True, False])

c1, c2 = st.columns(2)
with c1:
    st.write("**Por Supervisor**")
    st.dataframe(resumen_supervisor, use_container_width=True, hide_index=True)
with c2:
    st.write("**Detalle Anfitriones**")
    st.dataframe(resumen_anfitrion, use_container_width=True, hide_index=True)

# --- DESCARGA EXCEL CABIFY ---
excel_data = generar_excel_cabify(resumen_supervisor, resumen_anfitrion)

st.download_button(
    label="🟣 Descargar Reporte Excel (Diseño Cabify)",
    data=excel_data,
    file_name=f"Reporte_KPI_Aeropuerto_{datetime.now().strftime('%Y%m%d')}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
