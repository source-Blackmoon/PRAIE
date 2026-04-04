"""
Dashboard de administración — Laura (PRAIE)
Ejecutar: .venv/bin/streamlit run dashboard.py
"""

import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter
import subprocess
import sys
import os
import asyncio
import httpx

# ── Configuración de la página ─────────────────────────────
st.set_page_config(
    page_title="Laura — Panel PRAIE",
    page_icon="👙",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Estilos ────────────────────────────────────────────────
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.2rem; border-radius: 12px; color: white; text-align: center;
    }
    .metric-number { font-size: 2.2rem; font-weight: 800; margin: 0; }
    .metric-label  { font-size: 0.85rem; opacity: 0.85; margin: 0; }
    .alert-card {
        background: #fff3cd; border-left: 4px solid #ffc107;
        padding: 0.8rem 1rem; border-radius: 6px; margin: 0.4rem 0;
    }
    .ok-card {
        background: #d4edda; border-left: 4px solid #28a745;
        padding: 0.8rem 1rem; border-radius: 6px; margin: 0.4rem 0;
    }
    [data-testid="stSidebar"] { background: #1a1a2e; }
    [data-testid="stSidebar"] * { color: white !important; }
</style>
""", unsafe_allow_html=True)

DB_PATH = "agentkit.db"
KNOWLEDGE_DIR = Path("knowledge")
API_URL = os.getenv("API_URL", "http://localhost:8000")
REPORTS_DIR = Path("tools/reportes")
SEÑALES_PROBLEMA = ["no tengo esa información", "déjame consultarlo",
                    "no entendí", "problemas técnicos", "no sé", "disculpa"]

# ── Helpers de base de datos ───────────────────────────────
@st.cache_data(ttl=30)
def cargar_mensajes(dias: int = 30) -> pd.DataFrame:
    if not Path(DB_PATH).exists():
        return pd.DataFrame()
    desde = datetime.utcnow() - timedelta(days=dias)
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT * FROM mensajes WHERE timestamp >= ? ORDER BY timestamp DESC",
        conn, params=[desde.isoformat()],
    )
    conn.close()
    if df.empty:
        return df
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["fecha"] = df["timestamp"].dt.date
    df["hora"] = df["timestamp"].dt.hour
    return df


def calcular_metricas(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"conversaciones": 0, "mensajes": 0, "clientas": 0,
                "problemas": 0, "tasa_problema": 0}
    clientas = df[df["role"] == "user"]["telefono"].nunique()
    total = len(df)
    problemas = df[df["role"] == "assistant"]["content"].str.lower().apply(
        lambda x: any(s in x for s in SEÑALES_PROBLEMA)
    ).sum()
    resp_agente = len(df[df["role"] == "assistant"])
    return {
        "conversaciones": df["telefono"].nunique(),
        "mensajes": total,
        "clientas": clientas,
        "problemas": int(problemas),
        "tasa_problema": round(problemas / resp_agente * 100, 1) if resp_agente > 0 else 0,
    }


def top_palabras(df: pd.DataFrame, n: int = 10) -> list[tuple]:
    stopwords = {"que", "de", "el", "la", "en", "un", "una", "me", "si", "no",
                 "se", "con", "por", "mi", "es", "y", "a", "los", "las", "le",
                 "su", "al", "del", "hola", "buenas", "gracias", "ok", "bien",
                 "para", "lo", "les", "nos", "pero", "más", "como", "qué"}
    msgs = df[df["role"] == "user"]["content"].str.lower().str.split()
    palabras = [p for lista in msgs for p in lista if len(p) > 3 and p not in stopwords]
    return Counter(palabras).most_common(n)


# ── Sidebar ────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 👙 Laura — PRAIE")
    st.markdown("Panel de administración")
    st.divider()

    pagina = st.radio("Navegación", [
        "📊 Dashboard",
        "🛒 Carritos Abandonados",
        "💬 Conversaciones",
        "📚 Knowledge Base",
        "🔍 Análisis con IA",
        "⚙️ Configuración",
    ])

    st.divider()
    dias = st.select_slider("Período", options=[1, 3, 7, 14, 30], value=7)
    st.caption(f"Mostrando últimos {dias} días")

    st.divider()
    estado_servidor = "🟢 Servidor activo" if Path("agentkit.db").exists() else "🔴 Sin datos"
    st.caption(estado_servidor)


# ══════════════════════════════════════════════════════════════
# PÁGINA 1 — DASHBOARD
# ══════════════════════════════════════════════════════════════
if pagina == "📊 Dashboard":
    st.title("📊 Dashboard — Laura PRAIE")
    st.caption(f"Actualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    df = cargar_mensajes(dias)
    m = calcular_metricas(df)

    # ── Tarjetas de métricas ──
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""<div class="metric-card">
            <p class="metric-number">{m['conversaciones']}</p>
            <p class="metric-label">Conversaciones</p>
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div class="metric-card">
            <p class="metric-number">{m['clientas']}</p>
            <p class="metric-label">Clientas únicas</p>
        </div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""<div class="metric-card">
            <p class="metric-number">{m['mensajes']}</p>
            <p class="metric-label">Mensajes totales</p>
        </div>""", unsafe_allow_html=True)
    with col4:
        color = "#dc3545" if m['tasa_problema'] > 20 else "#28a745"
        st.markdown(f"""<div style="background:linear-gradient(135deg,{color},{color}cc);
            padding:1.2rem;border-radius:12px;color:white;text-align:center">
            <p class="metric-number">{m['tasa_problema']}%</p>
            <p class="metric-label">Respuestas a mejorar</p>
        </div>""", unsafe_allow_html=True)

    st.divider()

    if df.empty:
        st.info("Aún no hay conversaciones. Cuando las clientas escriban por WhatsApp, aparecerán aquí.")
    else:
        col_izq, col_der = st.columns([2, 1])

        with col_izq:
            # Mensajes por día
            msgs_dia = df.groupby(["fecha", "role"]).size().reset_index(name="count")
            fig = px.bar(msgs_dia, x="fecha", y="count", color="role",
                         color_discrete_map={"user": "#764ba2", "assistant": "#667eea"},
                         labels={"fecha": "Fecha", "count": "Mensajes", "role": ""},
                         title="Mensajes por día")
            fig.update_layout(legend=dict(orientation="h"),
                              plot_bgcolor="rgba(0,0,0,0)", height=300)
            fig.for_each_trace(lambda t: t.update(
                name="Clientas" if t.name == "user" else "Laura"))
            st.plotly_chart(fig, use_container_width=True)

        with col_der:
            # Temas más buscados
            palabras = top_palabras(df, 8)
            if palabras:
                df_palabras = pd.DataFrame(palabras, columns=["Tema", "Veces"])
                fig2 = px.bar(df_palabras, x="Veces", y="Tema", orientation="h",
                              title="Temas más preguntados",
                              color="Veces", color_continuous_scale="Purples")
                fig2.update_layout(showlegend=False, height=300,
                                   plot_bgcolor="rgba(0,0,0,0)",
                                   yaxis=dict(autorange="reversed"))
                st.plotly_chart(fig2, use_container_width=True)

        # Actividad por hora
        col_a, col_b = st.columns(2)
        with col_a:
            msgs_hora = df[df["role"] == "user"].groupby("hora").size().reset_index(name="count")
            fig3 = px.area(msgs_hora, x="hora", y="count",
                           title="Horario de mayor actividad",
                           labels={"hora": "Hora del día", "count": "Mensajes"},
                           color_discrete_sequence=["#764ba2"])
            fig3.update_layout(plot_bgcolor="rgba(0,0,0,0)", height=250)
            st.plotly_chart(fig3, use_container_width=True)

        with col_b:
            # Distribución usuario vs agente
            dist = df["role"].value_counts().reset_index()
            dist.columns = ["Rol", "Mensajes"]
            dist["Rol"] = dist["Rol"].map({"user": "Clientas", "assistant": "Laura"})
            fig4 = px.pie(dist, values="Mensajes", names="Rol",
                          title="Distribución de mensajes",
                          color_discrete_sequence=["#764ba2", "#667eea"])
            fig4.update_layout(height=250)
            st.plotly_chart(fig4, use_container_width=True)

        # Alertas
        st.subheader("⚠️ Respuestas que necesitan revisión")
        problemas_df = df[df["role"] == "assistant"][
            df[df["role"] == "assistant"]["content"].str.lower().apply(
                lambda x: any(s in x for s in SEÑALES_PROBLEMA)
            )
        ]
        if problemas_df.empty:
            st.markdown('<div class="ok-card">✅ No se detectaron respuestas problemáticas este período.</div>',
                        unsafe_allow_html=True)
        else:
            for _, row in problemas_df.head(5).iterrows():
                st.markdown(f'<div class="alert-card">⚠️ <b>{row["timestamp"].strftime("%d/%m %H:%M")}</b> — {row["content"][:150]}...</div>',
                            unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# PÁGINA 2 — CARRITOS ABANDONADOS
# ══════════════════════════════════════════════════════════════
elif pagina == "🛒 Carritos Abandonados":
    st.title("🛒 Carritos Abandonados")

    # ── Helpers directos Shopify (sin servidor) ────────────
    def _sync_directo(horas: int = 168) -> dict:
        """Sincroniza desde Shopify directamente al SQLite local."""
        sys.path.insert(0, str(Path(__file__).parent))
        from agent.shopify import obtener_checkouts_shopify, verificar_credenciales
        from agent.memory import inicializar_db, guardar_checkout, marcar_checkout_completado

        async def _run():
            await inicializar_db()
            checkouts = await obtener_checkouts_shopify(horas_atras=horas)
            nuevos = completados = 0
            for c in checkouts:
                if c["completado"]:
                    await marcar_checkout_completado(c["checkout_id"])
                    completados += 1
                else:
                    try:
                        await guardar_checkout(
                            checkout_id=c["checkout_id"],
                            telefono=c["telefono"],
                            nombre=c["nombre"],
                            productos=c["productos"],
                            total=c["total"],
                            url_carrito=c["url_carrito"],
                        )
                        nuevos += 1
                    except Exception:
                        pass
            return {"nuevos": nuevos, "completados_marcados": completados, "total": len(checkouts)}

        return asyncio.run(_run())

    def _verificar_shopify() -> dict:
        sys.path.insert(0, str(Path(__file__).parent))
        from agent.shopify import verificar_credenciales
        return asyncio.run(verificar_credenciales())

    def _enviar_whatsapp(checkout_id: str, telefono: str, nombre: str,
                          productos: str, total: str, url_carrito: str) -> bool:
        sys.path.insert(0, str(Path(__file__).parent))
        from agent.providers import obtener_proveedor
        from agent.carrito import construir_mensaje
        from agent.memory import marcar_mensaje_enviado

        async def _run():
            proveedor = obtener_proveedor()
            mensaje = construir_mensaje(nombre, productos, total, url_carrito)
            enviado = await proveedor.enviar_mensaje(telefono, mensaje)
            if enviado:
                await marcar_mensaje_enviado(checkout_id)
            return enviado, mensaje

        return asyncio.run(_run())

    # ── Barra de estado y acciones ─────────────────────────
    col_sh1, col_sh2, col_sh3 = st.columns([2, 1, 1])
    with col_sh1:
        try:
            creds = _verificar_shopify()
            if creds.get("ok"):
                st.success(f"🟢 Shopify conectado — **{creds.get('tienda', '')}** ({creds.get('dominio', '')})")
            else:
                st.warning(f"🔴 Shopify no conectado: {creds.get('error', 'Token inválido')}")
        except Exception as e:
            st.error(f"Error verificando Shopify: {e}")

    with col_sh2:
        horas_sync = st.selectbox("Período", [24, 48, 72, 168], index=1,
                                   format_func=lambda h: f"Últimas {h}h" if h < 168 else "Última semana")
        if st.button("🔄 Sincronizar con Shopify", type="primary"):
            with st.spinner("Consultando Shopify..."):
                try:
                    res = _sync_directo(horas=horas_sync)
                    st.success(f"✅ {res['nuevos']} nuevos · {res['completados_marcados']} completados · {res['total']} total")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    with col_sh3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔃 Actualizar lista"):
            st.cache_data.clear()
            st.rerun()

    st.divider()

    # ── Métricas superiores ────────────────────────────────
    @st.cache_data(ttl=10)
    def cargar_carritos():
        if not Path(DB_PATH).exists():
            return pd.DataFrame()
        conn = sqlite3.connect(DB_PATH)
        try:
            df = pd.read_sql_query(
                "SELECT * FROM checkouts_abandonados ORDER BY timestamp DESC", conn
            )
        except Exception:
            df = pd.DataFrame()
        conn.close()
        if not df.empty:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df

    df_carritos = cargar_carritos()

    if df_carritos.empty:
        st.info("Aún no hay carritos registrados. Cuando una clienta deje un carrito en praie.co aparecerá aquí.")
    else:
        total = len(df_carritos)
        pendientes = len(df_carritos[(df_carritos["mensaje_enviado"] == 0) & (df_carritos["completado"] == 0)])
        enviados = len(df_carritos[df_carritos["mensaje_enviado"] == 1])
        recuperados = len(df_carritos[df_carritos["completado"] == 1])

        col1, col2, col3, col4 = st.columns(4)
        col1.markdown(f"""<div class="metric-card">
            <p class="metric-number">{total}</p>
            <p class="metric-label">Total carritos</p>
        </div>""", unsafe_allow_html=True)
        col2.markdown(f"""<div style="background:linear-gradient(135deg,#f6c90e,#e0a800);
            padding:1.2rem;border-radius:12px;color:white;text-align:center">
            <p class="metric-number">{pendientes}</p>
            <p class="metric-label">Sin mensaje</p>
        </div>""", unsafe_allow_html=True)
        col3.markdown(f"""<div style="background:linear-gradient(135deg,#667eea,#764ba2);
            padding:1.2rem;border-radius:12px;color:white;text-align:center">
            <p class="metric-number">{enviados}</p>
            <p class="metric-label">Mensaje enviado</p>
        </div>""", unsafe_allow_html=True)
        col4.markdown(f"""<div style="background:linear-gradient(135deg,#28a745,#1e7e34);
            padding:1.2rem;border-radius:12px;color:white;text-align:center">
            <p class="metric-number">{recuperados}</p>
            <p class="metric-label">Recuperados</p>
        </div>""", unsafe_allow_html=True)

        st.divider()

        # ── Filtros ────────────────────────────────────────
        col_f1, col_f2 = st.columns([2, 1])
        with col_f1:
            filtro = st.radio("Mostrar:", ["Todos", "Sin mensaje", "Mensaje enviado", "Recuperados"], horizontal=True)
        with col_f2:
            auto_refresh = st.checkbox("Auto-actualizar cada 30s", value=False)
            if auto_refresh:
                import time; time.sleep(30); st.rerun()

        # Aplicar filtro
        df_filtrado = df_carritos.copy()
        if filtro == "Sin mensaje":
            df_filtrado = df_carritos[(df_carritos["mensaje_enviado"] == 0) & (df_carritos["completado"] == 0)]
        elif filtro == "Mensaje enviado":
            df_filtrado = df_carritos[df_carritos["mensaje_enviado"] == 1]
        elif filtro == "Recuperados":
            df_filtrado = df_carritos[df_carritos["completado"] == 1]

        st.markdown(f"**{len(df_filtrado)} carritos**")
        st.divider()

        # ── Tarjetas de carrito ────────────────────────────
        for _, row in df_filtrado.iterrows():
            # Estado visual
            if row["completado"]:
                estado_color = "#28a745"
                estado_icon = "✅"
                estado_texto = "Recuperado"
            elif row["mensaje_enviado"]:
                estado_color = "#764ba2"
                estado_icon = "📨"
                estado_texto = "Mensaje enviado"
            else:
                estado_color = "#f6c90e"
                estado_icon = "⏳"
                estado_texto = "Pendiente"

            # Tiempo transcurrido
            ahora = datetime.utcnow()
            delta = ahora - row["timestamp"].to_pydatetime().replace(tzinfo=None)
            if delta.seconds < 3600:
                tiempo = f"hace {delta.seconds // 60} min"
            elif delta.days == 0:
                tiempo = f"hace {delta.seconds // 3600}h"
            else:
                tiempo = f"hace {delta.days}d"

            with st.container():
                st.markdown(f"""
                <div style="border:1px solid #e0e0e0; border-left: 5px solid {estado_color};
                    border-radius:8px; padding:1rem 1.2rem; margin:0.5rem 0;
                    background:white">
                    <div style="display:flex; justify-content:space-between; align-items:center">
                        <div>
                            <span style="font-size:1.1rem; font-weight:600">
                                {estado_icon} {row['nombre'] or 'Clienta'} — {row['telefono']}
                            </span>
                            <span style="background:{estado_color}22; color:{estado_color};
                                font-size:0.75rem; padding:2px 8px; border-radius:12px;
                                margin-left:8px; font-weight:600">{estado_texto}</span>
                        </div>
                        <span style="color:#888; font-size:0.85rem">{tiempo}</span>
                    </div>
                    <div style="margin-top:0.5rem; color:#555; font-size:0.9rem">
                        🛍️ <b>{row['productos'] or 'Producto desconocido'}</b>
                        {'— ' + row['total'] if row['total'] else ''}
                    </div>
                    <div style="margin-top:0.3rem; font-size:0.8rem; color:#888">
                        🔗 {row['url_carrito'][:60]}{'...' if len(str(row['url_carrito'])) > 60 else ''}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Botón de acción
                col_btn, col_prev, _ = st.columns([1, 2, 3])
                with col_btn:
                    if not row["completado"]:
                        btn_label = "📤 Reenviar" if row["mensaje_enviado"] else "📲 Enviar por WhatsApp"
                        if st.button(btn_label, key=f"btn_{row['checkout_id']}", type="primary"):
                            with st.spinner("Enviando por WhatsApp..."):
                                try:
                                    enviado, msg = _enviar_whatsapp(
                                        checkout_id=row["checkout_id"],
                                        telefono=row["telefono"],
                                        nombre=row["nombre"] or "amiga",
                                        productos=row["productos"] or "tu vestido de baño",
                                        total=row["total"] or "",
                                        url_carrito=row["url_carrito"] or "https://praie.co",
                                    )
                                    if enviado:
                                        st.success(f"✅ Mensaje enviado a {row['telefono']}")
                                        st.cache_data.clear()
                                        st.rerun()
                                    else:
                                        st.error("Error al enviar — verifica WHAPI_TOKEN y conexión")
                                except Exception as e:
                                    st.error(f"Error: {e}")
                    else:
                        st.success("Compra completada")

                with col_prev:
                    with st.expander("Ver mensaje"):
                        nombre = row["nombre"] or "amiga"
                        productos = row["productos"] or "tu vestido de baño"
                        total = row["total"] or ""
                        url = row["url_carrito"] or "https://praie.co"
                        total_str = f" por {total}" if total else ""
                        st.info(
                            f"¡Hola {nombre.capitalize()}! 👋\n\n"
                            f"Vimos que dejaste {productos} en tu carrito de PRAIE{total_str} ♡\n\n"
                            f"¿Tienes alguna duda sobre la talla, el color o el envío? "
                            f"Aquí estoy para ayudarte 😊\n\n"
                            f"👉 Completa tu compra aquí:\n{url}\n\n"
                            f"Recuerda que puedes pagar contraentrega ♡"
                        )

        if df_filtrado.empty:
            st.info(f"No hay carritos con estado: {filtro}")

    # ── Panel de Webhooks Shopify ──────────────────────────
    st.divider()
    st.subheader("⚙️ Webhooks de Shopify")
    st.caption("Los webhooks permiten que Shopify avise en tiempo real cuando alguien abandona un carrito o completa una compra.")

    col_wb1, col_wb2 = st.columns([3, 1])
    with col_wb1:
        webhook_url = st.text_input(
            "URL pública del servidor (localtunnel o Railway)",
            placeholder="https://praie-laura.loca.lt  ó  https://tu-app.up.railway.app",
            help="Corre localtunnel con: npx localtunnel --port 8000 --subdomain praie-laura",
        )

    with col_wb2:
        st.markdown("<br>", unsafe_allow_html=True)
        registrar_btn = st.button("📡 Registrar webhooks", type="primary")

    if registrar_btn:
        if not webhook_url:
            st.error("Ingresa la URL pública primero")
        else:
            with st.spinner("Registrando en Shopify..."):
                try:
                    r = httpx.post(
                        f"{API_URL}/api/shopify/webhooks/registrar",
                        json={"base_url": webhook_url},
                        timeout=20,
                    )
                    if r.status_code == 200:
                        res = r.json()
                        if res.get("registrados"):
                            st.success(f"✅ Registrados: {', '.join(res['registrados'])}")
                        if res.get("ya_existian"):
                            st.info(f"ℹ️ Ya existían: {', '.join(res['ya_existian'])}")
                        if res.get("errores"):
                            st.error(f"Errores: {'; '.join(res['errores'])}")
                    else:
                        st.error(f"Error {r.status_code}: {r.text[:200]}")
                except Exception as e:
                    st.error(f"Sin conexión al servidor: {e}")

    # Listar webhooks actuales
    with st.expander("Ver webhooks activos en Shopify"):
        try:
            r = httpx.get(f"{API_URL}/api/shopify/webhooks", timeout=10)
            if r.status_code == 200:
                webhooks = r.json().get("webhooks", [])
                if not webhooks:
                    st.info("No hay webhooks registrados aún")
                else:
                    for wh in webhooks:
                        col_a, col_b, col_c = st.columns([2, 3, 1])
                        col_a.code(wh.get("topic", ""))
                        col_b.caption(wh.get("address", ""))
                        if col_c.button("🗑️", key=f"del_wh_{wh['id']}", help="Eliminar"):
                            d = httpx.delete(f"{API_URL}/api/shopify/webhooks/{wh['id']}", timeout=10)
                            if d.status_code == 200:
                                st.success("Eliminado")
                                st.rerun()
            else:
                st.warning("No se pudo consultar los webhooks")
        except Exception as e:
            st.caption(f"Servidor no disponible: {e}")

# ══════════════════════════════════════════════════════════════
# PÁGINA 3 — CONVERSACIONES
# ══════════════════════════════════════════════════════════════
elif pagina == "💬 Conversaciones":
    st.title("💬 Conversaciones")

    df = cargar_mensajes(dias)

    if df.empty:
        st.info("No hay conversaciones en este período.")
    else:
        # Lista de conversaciones
        resumen = (df.groupby("telefono")
                   .agg(mensajes=("id", "count"),
                        ultimo=("timestamp", "max"),
                        primer_msg=("content", "first"))
                   .reset_index()
                   .sort_values("ultimo", ascending=False))
        resumen["numero"] = resumen["telefono"].apply(
            lambda x: f"...{x[-8:]}" if len(x) > 8 else x)
        resumen["ultimo"] = resumen["ultimo"].dt.strftime("%d/%m %H:%M")
        resumen["preview"] = resumen["primer_msg"].str[:60] + "..."

        col1, col2 = st.columns([1, 2])

        with col1:
            st.subheader(f"{len(resumen)} conversaciones")
            seleccion = st.radio(
                "Selecciona una conversación:",
                options=resumen["telefono"].tolist(),
                format_func=lambda x: f"📱 {resumen[resumen['telefono']==x]['numero'].values[0]} — {resumen[resumen['telefono']==x]['mensajes'].values[0]} msgs",
            )

        with col2:
            if seleccion:
                conv = df[df["telefono"] == seleccion].sort_values("timestamp")
                st.subheader(f"Conversación — {seleccion[-8:]}")
                st.caption(f"{len(conv)} mensajes")

                for _, msg in conv.iterrows():
                    hora = msg["timestamp"].strftime("%H:%M")
                    if msg["role"] == "user":
                        st.markdown(f"""
                        <div style="text-align:right;margin:8px 0">
                            <span style="background:#e3e3e3;padding:8px 12px;
                            border-radius:12px 12px 0 12px;display:inline-block;
                            max-width:80%;font-size:0.9rem">{msg['content']}</span>
                            <br><small style="color:#888">{hora} · Clienta</small>
                        </div>""", unsafe_allow_html=True)
                    else:
                        tiene_problema = any(s in msg["content"].lower() for s in SEÑALES_PROBLEMA)
                        borde = "#ffc107" if tiene_problema else "#764ba2"
                        st.markdown(f"""
                        <div style="text-align:left;margin:8px 0">
                            <span style="background:#f3f0ff;padding:8px 12px;
                            border-radius:12px 12px 12px 0;display:inline-block;
                            max-width:80%;font-size:0.9rem;border-left:3px solid {borde}">
                            {msg['content']}</span>
                            <br><small style="color:#888">{hora} · Laura {'⚠️' if tiene_problema else '✅'}</small>
                        </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# PÁGINA 3 — KNOWLEDGE BASE
# ══════════════════════════════════════════════════════════════
elif pagina == "📚 Knowledge Base":
    st.title("📚 Knowledge Base")
    st.caption("Edita lo que Laura sabe. Los cambios se aplican al reiniciar el servidor.")

    archivos = list(KNOWLEDGE_DIR.glob("*.txt")) + [Path("config/prompts.yaml")]
    nombres = [f.name for f in archivos]

    col1, col2 = st.columns([1, 3])
    with col1:
        archivo_sel = st.radio("Archivos:", nombres)

    with col2:
        ruta = next(f for f in archivos if f.name == archivo_sel)
        contenido_actual = ruta.read_text(encoding="utf-8")

        st.subheader(f"📄 {archivo_sel}")
        st.caption(f"Tamaño: {len(contenido_actual):,} caracteres | Líneas: {contenido_actual.count(chr(10))}")

        contenido_nuevo = st.text_area(
            "Contenido:", value=contenido_actual,
            height=450, label_visibility="collapsed"
        )

        col_btn1, col_btn2, _ = st.columns([1, 1, 3])
        with col_btn1:
            if st.button("💾 Guardar", type="primary"):
                ruta.write_text(contenido_nuevo, encoding="utf-8")
                st.success("✅ Guardado. Reinicia el servidor para aplicar los cambios.")
                st.cache_data.clear()
        with col_btn2:
            if st.button("↩️ Restaurar"):
                st.rerun()

    # Agregar entrada rápida
    st.divider()
    st.subheader("➕ Agregar pregunta rápida")
    col_p, col_r = st.columns(2)
    with col_p:
        nueva_pregunta = st.text_input("Pregunta de clienta:")
    with col_r:
        nueva_respuesta = st.text_input("Respuesta de Laura:")

    if st.button("Agregar al knowledge base") and nueva_pregunta and nueva_respuesta:
        archivo_preguntas = KNOWLEDGE_DIR / "preguntas_reales.txt"
        contenido = archivo_preguntas.read_text(encoding="utf-8")
        nueva_linea = f"\n{nueva_pregunta} → {nueva_respuesta}"
        archivo_preguntas.write_text(contenido + nueva_linea, encoding="utf-8")
        st.success(f"✅ Agregado: '{nueva_pregunta}'")
        st.cache_data.clear()
        st.rerun()


# ══════════════════════════════════════════════════════════════
# PÁGINA 4 — ANÁLISIS CON IA
# ══════════════════════════════════════════════════════════════
elif pagina == "🔍 Análisis con IA":
    st.title("🔍 Análisis con IA")
    st.caption("Claude analiza las conversaciones reales y sugiere mejoras concretas.")

    col1, col2 = st.columns([2, 1])
    with col1:
        dias_analisis = st.select_slider("Analizar conversaciones de los últimos:", [3, 7, 14, 30], value=7)
        aplicar = st.checkbox("Aplicar mejoras automáticamente al knowledge base", value=True)

    with col2:
        st.metric("Costo estimado", "~$0.05 USD", help="Costo aproximado del análisis con Claude API")

    if st.button("🚀 Ejecutar análisis ahora", type="primary"):
        with st.spinner("Claude está analizando las conversaciones..."):
            cmd = [
                sys.executable, "tools/analisis_semanal.py",
                "--dias", str(dias_analisis),
            ]
            if aplicar:
                cmd.append("--aplicar")

            result = subprocess.run(cmd, capture_output=True, text=True, cwd=".")

        if result.returncode == 0:
            st.success("✅ Análisis completado")
            if aplicar:
                st.info("💡 Knowledge base actualizado. Reinicia el servidor para aplicar los cambios.")
        else:
            st.error(f"Error: {result.stderr[:500]}")

    # Reportes anteriores
    st.divider()
    st.subheader("📋 Reportes anteriores")

    REPORTS_DIR.mkdir(exist_ok=True)
    reportes = sorted(REPORTS_DIR.glob("*.md"), reverse=True)

    if not reportes:
        st.info("Aún no hay reportes. Ejecuta el primer análisis arriba.")
    else:
        for reporte in reportes[:5]:
            fecha = reporte.stem.replace("reporte_", "")
            with st.expander(f"📄 Reporte del {fecha}"):
                st.markdown(reporte.read_text(encoding="utf-8"))


# ══════════════════════════════════════════════════════════════
# PÁGINA 5 — CONFIGURACIÓN
# ══════════════════════════════════════════════════════════════
elif pagina == "⚙️ Configuración":
    st.title("⚙️ Configuración del agente")

    tab1, tab2 = st.tabs(["🖥️ Estado del servidor", "🔑 Variables de entorno"])

    with tab1:
        st.subheader("Comandos del servidor")

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("▶️ Iniciar servidor", use_container_width=True):
                subprocess.Popen(
                    [sys.executable, "-m", "uvicorn", "agent.main:app",
                     "--port", "8000"],
                    stdout=open("/tmp/praie-server.log", "w"),
                    stderr=subprocess.STDOUT,
                )
                st.success("Servidor iniciando en puerto 8000...")

        with col2:
            if st.button("⏹️ Detener servidor", use_container_width=True):
                subprocess.run(["kill", "$(lsof -ti:8000)"], shell=True)
                st.warning("Servidor detenido.")

        with col3:
            if st.button("🔄 Reiniciar servidor", use_container_width=True):
                subprocess.run("kill $(lsof -ti:8000) 2>/dev/null; sleep 1", shell=True)
                subprocess.Popen(
                    [sys.executable, "-m", "uvicorn", "agent.main:app", "--port", "8000"],
                    stdout=open("/tmp/praie-server.log", "w"),
                    stderr=subprocess.STDOUT,
                )
                st.success("✅ Servidor reiniciado.")

        st.divider()
        st.subheader("Logs en tiempo real")
        if st.button("🔍 Ver últimas 20 líneas del log"):
            log_path = Path("/tmp/praie-server.log")
            if log_path.exists():
                lineas = log_path.read_text().split("\n")[-20:]
                st.code("\n".join(lineas), language="bash")
            else:
                st.info("No hay logs disponibles. Inicia el servidor primero.")

        st.divider()
        st.subheader("Estadísticas de la base de datos")
        if Path(DB_PATH).exists():
            conn = sqlite3.connect(DB_PATH)
            total = pd.read_sql_query("SELECT COUNT(*) as total FROM mensajes", conn).iloc[0, 0]
            clientas = pd.read_sql_query(
                "SELECT COUNT(DISTINCT telefono) as total FROM mensajes WHERE role='user'", conn
            ).iloc[0, 0]
            conn.close()
            col_a, col_b = st.columns(2)
            col_a.metric("Total mensajes guardados", f"{total:,}")
            col_b.metric("Clientas únicas", f"{clientas:,}")
        else:
            st.info("Base de datos no encontrada. El servidor debe haber corrido al menos una vez.")

    with tab2:
        env_path = Path(".env")
        if env_path.exists():
            st.warning("⚠️ Las API keys son sensibles. No compartas ni publiques este archivo.")
            env_content = env_path.read_text(encoding="utf-8")
            # Enmascarar keys
            lineas_seguras = []
            for linea in env_content.split("\n"):
                if "=" in linea and not linea.startswith("#"):
                    clave, valor = linea.split("=", 1)
                    if len(valor) > 8:
                        valor = valor[:4] + "****" + valor[-4:]
                    lineas_seguras.append(f"{clave}={valor}")
                else:
                    lineas_seguras.append(linea)
            st.code("\n".join(lineas_seguras), language="bash")
        else:
            st.error("Archivo .env no encontrado.")
