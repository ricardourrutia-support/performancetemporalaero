import streamlit as st
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="KPIs Anfitriones Aeropuerto", layout="wide")

# --- FUNCIONES AUXILIARES ---
def limpiar_nombre_desde_email(email):
    """
    Convierte 'nombre.apellido@cabify.com' en 'Nombre Apellido'.
    """
    if not isinstance(email, str):
        return "Desconocido"
    user_part = email.split('@')[0]
    name_parts = user_part.split('.')
    clean_name = " ".join([part.capitalize() for part in name_parts])
    return clean_name

# --- INICIALIZACIÓN DE ESTADO (SESSION STATE) ---
# Esto permite que la app recuerde los supervisores y asignaciones mientras interactúas.

# 1. Lista de Supervisores Iniciales
if 'lista_supervisores' not in st.session_state:
    st.session_state['lista_supervisores'] = [
        "LUIS LEONARDO ALARCON MEDRANO",
        "ANA ESTEFANIA JIMENEZ LEZAMA",
        "GERALDINE CRISTINA GUTIERREZ BRICENO"
    ]

# 2. Diccionario para guardar la relación Anfitrión -> Supervisor
if 'mapa_anfitriones' not in st.session_state:
    st.session_state['mapa_anfitriones'] = {}

# --- BARRA LATERAL (SIDEBAR) ---
st.sidebar.title("Configuración")

# A. Carga de Archivo
uploaded_file = st.sidebar.file_uploader("1. Cargar Reporte de Inspecciones (CSV)", type=['csv', 'xlsx'])

# B. Gestión de Supervisores
st.sidebar.markdown("---")
st.sidebar.header("Gestión de Supervisores")

# Mostrar lista actual y permitir eliminar
supervisores_a_borrar = st.sidebar.multiselect(
    "Quitar Supervisor existente:", 
    st.session_state['lista_supervisores']
)
if supervisores_a_borrar:
    if st.sidebar.button("Eliminar seleccionados"):
        for sup in supervisores_a_borrar:
            if sup in st.session_state['lista_supervisores']:
                st.session_state['lista_supervisores'].remove(sup)
        st.rerun()

# Permitir agregar nuevo
nuevo_supervisor = st.sidebar.text_input("Agregar nuevo Supervisor:")
if st.sidebar.button("Agregar Supervisor"):
    if nuevo_supervisor and nuevo_supervisor not in st.session_state['lista_supervisores']:
        st.session_state['lista_supervisores'].append(nuevo_supervisor.upper())
        st.rerun()

# --- LÓGICA PRINCIPAL ---
st.title("✈️ KPI Anfitriones Aeropuerto - Resumen de Inspecciones")

if uploaded_file is not None:
    try:
        # Detectar formato y leer
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        
        # Validar columnas necesarias
        col_email = "Dirección de correo electrónico"
        
        # Buscar columna de fecha (prioridad 'Fecha', luego 'Marca temporal')
        if 'Fecha' in df.columns:
            col_fecha = 'Fecha'
        elif 'Marca temporal' in df.columns:
            col_fecha = 'Marca temporal'
        else:
            st.error("No se encontró una columna de fecha válida ('Fecha' o 'Marca temporal').")
            st.stop()

        # Convertir fecha
        df[col_fecha] = pd.to_datetime(df[col_fecha])

        # Crear columna de Nombres limpios
        df['Anfitrión'] = df[col_email].apply(limpiar_nombre_desde_email)

        # --- FILTRO DE FECHAS ---
        st.sidebar.markdown("---")
        min_date = df[col_fecha].min().date()
        max_date = df[col_fecha].max().date()
        
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            fecha_inicio = st.date_input("Fecha Desde", min_date)
        with col_f2:
            fecha_fin = st.date_input("Fecha Hasta", max_date)

        # Filtrar el DataFrame por fechas
        mask = (df[col_fecha].dt.date >= fecha_inicio) & (df[col_fecha].dt.date <= fecha_fin)
        df_filtered = df.loc[mask]

        # --- SECCIÓN DE ASIGNACIÓN DE SUPERVISORES ---
        st.markdown("### 1. Asignación de Anfitriones a Supervisores")
        st.info("Asigna un supervisor a cada anfitrión detectado en el archivo. La aplicación recordará tu selección.")

        # Obtener lista única de anfitriones en el archivo filtrado
        anfitriones_unicos = sorted(df_filtered['Anfitrión'].unique())
        
        with st.expander("Desplegar panel de asignación", expanded=True):
            cols = st.columns(3) # Grid de 3 columnas para ahorrar espacio
            for i, anfitrion in enumerate(anfitriones_unicos):
                # Verificar si ya tiene asignación previa en session_state
                idx_seleccion = 0
                actual_sup = st.session_state['mapa_anfitriones'].get(anfitrion)
                
                if actual_sup in st.session_state['lista_supervisores']:
                    idx_seleccion = st.session_state['lista_supervisores'].index(actual_sup)
                
                # Widget de selección
                supervisor_elegido = cols[i % 3].selectbox(
                    f"Supervisor de: **{anfitrion}**", 
                    st.session_state['lista_supervisores'],
                    index=idx_seleccion,
                    key=f"sel_{anfitrion}"
                )
                
                # Guardar en el mapa
                st.session_state['mapa_anfitriones'][anfitrion] = supervisor_elegido

        # Aplicar el mapa al DataFrame
        df_filtered['Supervisor'] = df_filtered['Anfitrión'].map(st.session_state['mapa_anfitriones'])

        # --- CÁLCULOS Y RESÚMENES ---
        st.markdown("---")
        st.markdown("### 2. Resultados del Periodo")

        # Métricas generales
        total_inspecciones = len(df_filtered)
        total_anfitriones = df_filtered['Anfitrión'].nunique()
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Inspecciones", total_inspecciones)
        m2.metric("Anfitriones Activos", total_anfitriones)
        m3.metric("Supervisores", len(st.session_state['lista_supervisores']))

        # TABLA 1: Resumen por Supervisor
        st.subheader("Resumen por Supervisor")
        
        resumen_supervisor = df_filtered.groupby('Supervisor').size().reset_index(name='Total Inspecciones')
        resumen_supervisor = resumen_supervisor.sort_values('Total Inspecciones', ascending=False)
        
        # Visualización gráfica simple
        st.bar_chart(resumen_supervisor.set_index('Supervisor'))
        st.dataframe(resumen_supervisor, use_container_width=True)

        # TABLA 2: Detalle por Anfitrión (Agrupado)
        st.subheader("Detalle por Anfitrión")
        
        resumen_anfitrion = df_filtered.groupby(['Supervisor', 'Anfitrión']).size().reset_index(name='Inspecciones')
        resumen_anfitrion = resumen_anfitrion.sort_values(['Supervisor', 'Inspecciones'], ascending=[True, False])
        
        st.dataframe(resumen_anfitrion, use_container_width=True)

        # Botón de descarga
        csv = resumen_anfitrion.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Descargar Resumen en CSV",
            data=csv,
            file_name='resumen_kpi_anfitriones.csv',
            mime='text/csv',
        )

    except Exception as e:
        st.error(f"Hubo un error al procesar el archivo: {e}")
        st.warning("Asegúrate de que el archivo CSV tenga las columnas: 'Dirección de correo electrónico' y 'Fecha' o 'Marca temporal'.")

else:
    st.info("👈 Por favor, carga el archivo CSV de inspecciones en la barra lateral para comenzar.")
    
    # Mostrar instrucciones
    st.markdown("""
    ### Instrucciones:
    1. Sube el archivo `.csv` o `.xlsx` de inspecciones (Google Forms).
    2. Selecciona el rango de fechas que deseas analizar.
    3. En el panel "Gestión de Supervisores" puedes agregar o quitar jefaturas.
    4. Asigna cada anfitrión a su supervisor correspondiente en el menú desplegable.
    5. Obtén tus tablas resumen automáticamente.
    """)
