import os
import json
import hashlib
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Text, DateTime, Index, select, Integer, Boolean, Float, func, update
from dotenv import load_dotenv

logger = logging.getLogger("agentkit")

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./agentkit.db")

if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Mensaje(Base):
    __tablename__ = "mensajes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telefono: Mapped[str] = mapped_column(String(50), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CheckoutAbandonado(Base):
    __tablename__ = "checkouts_abandonados"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    checkout_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    telefono: Mapped[str] = mapped_column(String(50), index=True)
    nombre: Mapped[str] = mapped_column(String(100), default="")
    productos: Mapped[str] = mapped_column(Text, default="")
    total: Mapped[str] = mapped_column(String(30), default="")
    url_carrito: Mapped[str] = mapped_column(Text, default="")
    mensaje_enviado: Mapped[bool] = mapped_column(Boolean, default=False)
    completado: Mapped[bool] = mapped_column(Boolean, default=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ConfiguracionSistema(Base):
    """Tabla de configuración clave-valor para parámetros del sistema."""
    __tablename__ = "configuracion"

    clave: Mapped[str] = mapped_column(String(100), primary_key=True)
    valor: Mapped[str] = mapped_column(Text, default="")
    actualizado: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Conversion(Base):
    """Venta cerrada atribuida a una conversación de WhatsApp con Laura."""
    __tablename__ = "conversiones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telefono: Mapped[str] = mapped_column(String(50), index=True)
    order_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    order_total: Mapped[str] = mapped_column(String(50), default="")
    productos: Mapped[str] = mapped_column(Text, default="")
    # "chat" = solo hubo chat, "carrito" = solo carrito abandonado, "ambos" = los dos
    fuente: Mapped[str] = mapped_column(String(20), default="chat")
    dias_desde_chat: Mapped[int] = mapped_column(Integer, default=0)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ── Funnel Analytics ──────────────────────────────────────

class TipoEventoFunnel(str, Enum):
    MENSAJE_RECIBIDO = "mensaje_recibido"
    PRODUCTO_CONSULTADO = "producto_consultado"
    CARRITO_CREADO = "carrito_creado"
    COMPRA_REALIZADA = "compra_realizada"


class MetadataEvento(BaseModel):
    """Validacion Pydantic para metadata de eventos del funnel."""
    query: Optional[str] = None
    productos: Optional[list[str]] = None
    total: Optional[str] = None
    order_id: Optional[str] = None
    checkout_id: Optional[str] = None
    fuente: Optional[str] = None

    @field_validator("query")
    @classmethod
    def query_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            return None
        return v


class EventoFunnel(Base):
    """Evento del funnel de conversion: mensaje → producto → carrito → compra."""
    __tablename__ = "eventos_funnel"
    __table_args__ = (
        Index("ix_funnel_tipo_timestamp", "tipo_evento", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telefono: Mapped[str] = mapped_column(String(50), index=True)
    tipo_evento: Mapped[str] = mapped_column(String(30))
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ── Escalaciones ─────────────────────────────────────────

class Escalacion(Base):
    """Escalada de conversacion a un humano del equipo."""
    __tablename__ = "escalaciones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telefono: Mapped[str] = mapped_column(String(50), index=True)
    razon: Mapped[str] = mapped_column(Text, default="")
    resumen: Mapped[str] = mapped_column(Text, default="")
    estado: Mapped[str] = mapped_column(String(20), default="pendiente")  # pendiente, resuelta
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ── A/B Testing ──────────────────────────────────────────

class TestAB(Base):
    """Test A/B para mensajes de carrito abandonado."""
    __tablename__ = "tests_ab"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(100))
    variante_a: Mapped[str] = mapped_column(Text)
    variante_b: Mapped[str] = mapped_column(Text)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    fecha_inicio: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AsignacionAB(Base):
    """Asignacion deterministica de variante A/B por telefono."""
    __tablename__ = "asignaciones_ab"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telefono: Mapped[str] = mapped_column(String(50), index=True)
    test_id: Mapped[int] = mapped_column(Integer, index=True)
    variante: Mapped[str] = mapped_column(String(1))  # "a" o "b"
    resultado: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # null, "converted"
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


def asignar_variante_ab(telefono: str, test_id: int) -> str:
    """Asignacion deterministica: hash(telefono + test_id) % 2."""
    h = hashlib.md5(f"{telefono}-{test_id}".encode()).hexdigest()
    return "a" if int(h, 16) % 2 == 0 else "b"


async def inicializar_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


MAX_MENSAJE_LENGTH = 4096


async def guardar_mensaje(telefono: str, role: str, content: str):
    # Truncar mensajes excesivamente largos para evitar abuso de DB
    if len(content) > MAX_MENSAJE_LENGTH:
        content = content[:MAX_MENSAJE_LENGTH] + "... [truncado]"
    async with async_session() as session:
        session.add(Mensaje(telefono=telefono, role=role, content=content))
        await session.commit()


async def obtener_historial(telefono: str, limite: int = 20) -> list[dict]:
    async with async_session() as session:
        query = (
            select(Mensaje)
            .where(Mensaje.telefono == telefono)
            .order_by(Mensaje.timestamp.desc())
            .limit(limite)
        )
        result = await session.execute(query)
        mensajes = list(reversed(result.scalars().all()))
        return [{"role": m.role, "content": m.content} for m in mensajes]


async def guardar_checkout(checkout_id: str, telefono: str, nombre: str,
                           productos: str, total: str, url_carrito: str):
    async with async_session() as session:
        existente = await session.execute(
            select(CheckoutAbandonado).where(CheckoutAbandonado.checkout_id == checkout_id)
        )
        if existente.scalar_one_or_none():
            return
        session.add(CheckoutAbandonado(
            checkout_id=checkout_id, telefono=telefono, nombre=nombre,
            productos=productos, total=total, url_carrito=url_carrito,
        ))
        await session.commit()


async def obtener_checkouts_pendientes(minutos_espera: int = 60) -> list:
    limite = datetime.utcnow() - timedelta(minutes=minutos_espera)
    async with async_session() as session:
        query = (
            select(CheckoutAbandonado)
            .where(CheckoutAbandonado.mensaje_enviado == False)
            .where(CheckoutAbandonado.completado == False)
            .where(CheckoutAbandonado.timestamp <= limite)
        )
        result = await session.execute(query)
        return result.scalars().all()


async def marcar_mensaje_enviado(checkout_id: str):
    async with async_session() as session:
        result = await session.execute(
            select(CheckoutAbandonado).where(CheckoutAbandonado.checkout_id == checkout_id)
        )
        checkout = result.scalar_one_or_none()
        if checkout:
            checkout.mensaje_enviado = True
            await session.commit()


async def marcar_checkout_completado(checkout_id: str):
    async with async_session() as session:
        result = await session.execute(
            select(CheckoutAbandonado).where(CheckoutAbandonado.checkout_id == checkout_id)
        )
        checkout = result.scalar_one_or_none()
        if checkout:
            checkout.completado = True
            await session.commit()


async def tuvo_conversacion_reciente(telefono: str, dias: int = 7) -> int:
    """
    Retorna los días transcurridos desde el último mensaje con este teléfono.
    Retorna -1 si no hubo conversación en el período indicado.
    """
    limite = datetime.utcnow() - timedelta(days=dias)
    async with async_session() as session:
        result = await session.execute(
            select(func.max(Mensaje.timestamp))
            .where(Mensaje.telefono == telefono)
            .where(Mensaje.timestamp >= limite)
        )
        ultimo = result.scalar_one_or_none()
        if not ultimo:
            return -1
        return (datetime.utcnow() - ultimo).days


async def registrar_conversion(
    telefono: str,
    order_id: str,
    order_total: str = "",
    productos: str = "",
    fuente: str = "chat",
    dias_desde_chat: int = 0,
):
    """Registra una venta cerrada atribuida a una conversación de WhatsApp."""
    async with async_session() as session:
        existente = await session.execute(
            select(Conversion).where(Conversion.order_id == order_id)
        )
        if existente.scalar_one_or_none():
            return  # Ya registrada
        session.add(Conversion(
            telefono=telefono,
            order_id=order_id,
            order_total=order_total,
            productos=productos,
            fuente=fuente,
            dias_desde_chat=dias_desde_chat,
        ))
        await session.commit()


async def obtener_conversiones(dias: int = 30) -> list:
    """Retorna las conversiones registradas en los últimos N días."""
    limite = datetime.utcnow() - timedelta(days=dias)
    async with async_session() as session:
        result = await session.execute(
            select(Conversion)
            .where(Conversion.timestamp >= limite)
            .order_by(Conversion.timestamp.desc())
        )
        return result.scalars().all()


async def obtener_config(clave: str, default: str = "") -> str:
    """Lee un valor de configuración por clave. Retorna default si no existe."""
    async with async_session() as session:
        result = await session.execute(
            select(ConfiguracionSistema).where(ConfiguracionSistema.clave == clave)
        )
        row = result.scalar_one_or_none()
        return row.valor if row else default


async def guardar_config(clave: str, valor: str):
    """Guarda o actualiza un valor de configuración."""
    async with async_session() as session:
        result = await session.execute(
            select(ConfiguracionSistema).where(ConfiguracionSistema.clave == clave)
        )
        row = result.scalar_one_or_none()
        if row:
            row.valor = valor
            row.actualizado = datetime.utcnow()
        else:
            session.add(ConfiguracionSistema(clave=clave, valor=valor))
        await session.commit()


async def limpiar_historial(telefono: str):
    async with async_session() as session:
        result = await session.execute(select(Mensaje).where(Mensaje.telefono == telefono))
        for m in result.scalars().all():
            await session.delete(m)
        await session.commit()


# ── SEC-014: Retencion automatica de datos ──────────────────

RETENCION_MENSAJES_DIAS = int(os.getenv("RETENCION_MENSAJES_DIAS", "90"))
RETENCION_EVENTOS_DIAS = int(os.getenv("RETENCION_EVENTOS_DIAS", "180"))


async def purgar_datos_antiguos():
    """Elimina mensajes y eventos mas antiguos que el periodo de retencion."""
    ahora = datetime.utcnow()
    limite_mensajes = ahora - timedelta(days=RETENCION_MENSAJES_DIAS)
    limite_eventos = ahora - timedelta(days=RETENCION_EVENTOS_DIAS)

    from sqlalchemy import delete

    async with async_session() as session:
        # Purgar mensajes antiguos
        result_msg = await session.execute(
            delete(Mensaje).where(Mensaje.timestamp < limite_mensajes)
        )
        # Purgar eventos de funnel antiguos
        result_ev = await session.execute(
            delete(EventoFunnel).where(EventoFunnel.timestamp < limite_eventos)
        )
        # Purgar escalaciones resueltas antiguas
        result_esc = await session.execute(
            delete(Escalacion).where(
                Escalacion.timestamp < limite_mensajes,
                Escalacion.estado == "resuelta",
            )
        )
        await session.commit()
        total = result_msg.rowcount + result_ev.rowcount + result_esc.rowcount
        if total > 0:
            logger.info(
                f"Purga de datos: {result_msg.rowcount} mensajes, "
                f"{result_ev.rowcount} eventos, {result_esc.rowcount} escalaciones eliminadas"
            )
        return total


async def derecho_al_olvido(telefono: str) -> dict:
    """SEC-015: Elimina TODOS los datos asociados a un numero de telefono."""
    from sqlalchemy import delete

    conteos = {}
    async with async_session() as session:
        r = await session.execute(delete(Mensaje).where(Mensaje.telefono == telefono))
        conteos["mensajes"] = r.rowcount
        r = await session.execute(delete(EventoFunnel).where(EventoFunnel.telefono == telefono))
        conteos["eventos_funnel"] = r.rowcount
        r = await session.execute(delete(Escalacion).where(Escalacion.telefono == telefono))
        conteos["escalaciones"] = r.rowcount
        r = await session.execute(delete(CheckoutAbandonado).where(CheckoutAbandonado.telefono == telefono))
        conteos["checkouts"] = r.rowcount
        r = await session.execute(delete(Conversion).where(Conversion.telefono == telefono))
        conteos["conversiones"] = r.rowcount
        r = await session.execute(delete(AsignacionAB).where(AsignacionAB.telefono == telefono))
        conteos["asignaciones_ab"] = r.rowcount
        await session.commit()

    logger.info(f"Derecho al olvido ejecutado — registros eliminados: {conteos}")
    return conteos


# ── Funnel Analytics functions ────────────────────────────

async def registrar_evento_funnel(
    telefono: str,
    tipo_evento: TipoEventoFunnel,
    metadata: MetadataEvento | None = None,
):
    """Registra un evento en el funnel de conversion con validacion Pydantic."""
    meta_json = metadata.model_dump_json(exclude_none=True) if metadata else "{}"
    async with async_session() as session:
        session.add(EventoFunnel(
            telefono=telefono,
            tipo_evento=tipo_evento.value,
            metadata_json=meta_json,
        ))
        await session.commit()


async def obtener_funnel(fecha_inicio: datetime, fecha_fin: datetime) -> dict:
    """
    Retorna conteos del funnel agrupados por tipo de evento.
    Usa el indice compuesto (tipo_evento, timestamp).
    """
    async with async_session() as session:
        result = await session.execute(
            select(EventoFunnel.tipo_evento, func.count(EventoFunnel.id))
            .where(EventoFunnel.timestamp >= fecha_inicio)
            .where(EventoFunnel.timestamp <= fecha_fin)
            .group_by(EventoFunnel.tipo_evento)
        )
        conteos = {row[0]: row[1] for row in result.all()}

    # Calcular valor total de compras
    valor_total = 0.0
    if conteos.get(TipoEventoFunnel.COMPRA_REALIZADA.value, 0) > 0:
        async with async_session() as session:
            result = await session.execute(
                select(EventoFunnel.metadata_json)
                .where(EventoFunnel.tipo_evento == TipoEventoFunnel.COMPRA_REALIZADA.value)
                .where(EventoFunnel.timestamp >= fecha_inicio)
                .where(EventoFunnel.timestamp <= fecha_fin)
            )
            for (meta_str,) in result.all():
                try:
                    meta = json.loads(meta_str)
                    total_str = meta.get("total", "0")
                    valor = float(
                        total_str.replace("$", "").replace(".", "").replace(",", ".").split()[0]
                    )
                    valor_total += valor
                except (ValueError, IndexError, AttributeError):
                    pass

    # Clientas unicas por paso
    async with async_session() as session:
        result = await session.execute(
            select(EventoFunnel.tipo_evento, func.count(func.distinct(EventoFunnel.telefono)))
            .where(EventoFunnel.timestamp >= fecha_inicio)
            .where(EventoFunnel.timestamp <= fecha_fin)
            .group_by(EventoFunnel.tipo_evento)
        )
        clientas_unicas = {row[0]: row[1] for row in result.all()}

    orden = [e.value for e in TipoEventoFunnel]
    return {
        "periodo": {
            "inicio": fecha_inicio.isoformat(),
            "fin": fecha_fin.isoformat(),
        },
        "funnel": [
            {
                "paso": paso,
                "eventos": conteos.get(paso, 0),
                "clientas_unicas": clientas_unicas.get(paso, 0),
            }
            for paso in orden
        ],
        "valor_total_compras": valor_total,
    }


# ── Escalaciones functions ────────────────────────────────

async def crear_escalacion(telefono: str, razon: str, resumen: str) -> Escalacion | None:
    """
    Crea una escalacion con debounce: solo 1 por telefono cada 30 minutos.
    Retorna la escalacion creada o None si hay una reciente.
    """
    limite = datetime.utcnow() - timedelta(minutes=30)
    async with async_session() as session:
        result = await session.execute(
            select(Escalacion)
            .where(Escalacion.telefono == telefono)
            .where(Escalacion.estado == "pendiente")
            .where(Escalacion.timestamp >= limite)
        )
        if result.scalar_one_or_none():
            logger.info(f"Escalacion duplicada ignorada para {telefono} (debounce 30min)")
            return None

        escalacion = Escalacion(
            telefono=telefono,
            razon=razon,
            resumen=resumen,
        )
        session.add(escalacion)
        await session.commit()
        await session.refresh(escalacion)
        return escalacion


async def obtener_escalaciones(estado: str | None = None) -> list:
    """Retorna escalaciones, opcionalmente filtradas por estado."""
    async with async_session() as session:
        query = select(Escalacion).order_by(Escalacion.timestamp.desc())
        if estado:
            query = query.where(Escalacion.estado == estado)
        result = await session.execute(query)
        return result.scalars().all()


async def resolver_escalacion(escalacion_id: int) -> bool:
    """Marca una escalacion como resuelta."""
    async with async_session() as session:
        result = await session.execute(
            select(Escalacion).where(Escalacion.id == escalacion_id)
        )
        esc = result.scalar_one_or_none()
        if not esc:
            return False
        esc.estado = "resuelta"
        await session.commit()
        return True


# ── A/B Testing CRUD ─────────────────────────────────────

async def obtener_test_ab_activo() -> TestAB | None:
    """Retorna el test A/B activo (solo 1 a la vez)."""
    async with async_session() as session:
        result = await session.execute(
            select(TestAB).where(TestAB.activo == True).limit(1)
        )
        return result.scalar_one_or_none()


async def obtener_tests_ab() -> list:
    """Retorna todos los tests A/B ordenados por fecha."""
    async with async_session() as session:
        result = await session.execute(
            select(TestAB).order_by(TestAB.fecha_inicio.desc())
        )
        return list(result.scalars().all())


async def crear_test_ab(nombre: str, variante_a: str, variante_b: str) -> TestAB:
    """Crea un test A/B. Desactiva cualquier test activo previo."""
    async with async_session() as session:
        # Desactivar tests activos
        await session.execute(
            update(TestAB).where(TestAB.activo == True).values(activo=False)
        )
        test = TestAB(nombre=nombre, variante_a=variante_a, variante_b=variante_b)
        session.add(test)
        await session.commit()
        await session.refresh(test)
        return test


async def pausar_test_ab(test_id: int) -> bool:
    """Pausa (desactiva) un test A/B."""
    async with async_session() as session:
        result = await session.execute(select(TestAB).where(TestAB.id == test_id))
        test = result.scalar_one_or_none()
        if not test:
            return False
        test.activo = False
        await session.commit()
        return True


async def registrar_asignacion_ab(telefono: str, test_id: int, variante: str):
    """Guarda la asignacion de variante para un telefono."""
    async with async_session() as session:
        session.add(AsignacionAB(telefono=telefono, test_id=test_id, variante=variante))
        await session.commit()


async def marcar_conversion_ab(telefono: str):
    """Marca como convertida la ultima asignacion A/B de un telefono."""
    async with async_session() as session:
        result = await session.execute(
            select(AsignacionAB)
            .where(AsignacionAB.telefono == telefono, AsignacionAB.resultado == None)
            .order_by(AsignacionAB.timestamp.desc())
            .limit(1)
        )
        asig = result.scalar_one_or_none()
        if asig:
            asig.resultado = "converted"
            await session.commit()


async def obtener_resultados_ab(test_id: int) -> dict:
    """Retorna resultados del test A/B: envios y conversiones por variante."""
    async with async_session() as session:
        result = await session.execute(
            select(AsignacionAB).where(AsignacionAB.test_id == test_id)
        )
        asignaciones = list(result.scalars().all())

    stats = {"a": {"envios": 0, "conversiones": 0}, "b": {"envios": 0, "conversiones": 0}}
    for a in asignaciones:
        if a.variante in stats:
            stats[a.variante]["envios"] += 1
            if a.resultado == "converted":
                stats[a.variante]["conversiones"] += 1

    total = stats["a"]["envios"] + stats["b"]["envios"]
    return {
        "test_id": test_id,
        "total_envios": total,
        "significancia": total >= 100,
        "variantes": stats,
    }
