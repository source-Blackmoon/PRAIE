import os
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Text, DateTime, select, Integer, Boolean, func, update
from dotenv import load_dotenv

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


async def inicializar_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def guardar_mensaje(telefono: str, role: str, content: str):
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
