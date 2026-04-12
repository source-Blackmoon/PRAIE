"""Tests para el funnel de conversion (Feature 4) y utilidades."""
import asyncio
import pytest
from datetime import datetime, timedelta

# Configurar DB en memoria para tests
import os
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from agent.memory import (
    inicializar_db, registrar_evento_funnel, obtener_funnel,
    TipoEventoFunnel, MetadataEvento,
    crear_escalacion, obtener_escalaciones, resolver_escalacion,
    asignar_variante_ab,
)
from agent.utils import normalizar_telefono_e164


@pytest.fixture(autouse=True)
async def setup_db():
    await inicializar_db()
    yield


# ── Tests normalizar_telefono_e164 ───────────────────────

class TestNormalizarTelefono:
    def test_ya_e164(self):
        assert normalizar_telefono_e164("+573001234567") == "+573001234567"

    def test_sin_plus(self):
        assert normalizar_telefono_e164("573001234567") == "+573001234567"

    def test_local_colombiano(self):
        assert normalizar_telefono_e164("3001234567") == "+573001234567"

    def test_formato_twilio(self):
        assert normalizar_telefono_e164("whatsapp:+573001234567") == "+573001234567"

    def test_vacio(self):
        assert normalizar_telefono_e164("") == ""

    def test_con_espacios(self):
        assert normalizar_telefono_e164(" 300 123 4567 ") == "+573001234567"


# ── Tests funnel events ──────────────────────────────────

@pytest.mark.asyncio
class TestFunnelEvents:
    async def test_registrar_evento_simple(self):
        await registrar_evento_funnel(
            "+573001234567", TipoEventoFunnel.MENSAJE_RECIBIDO,
        )
        funnel = await obtener_funnel(
            datetime.utcnow() - timedelta(hours=1),
            datetime.utcnow() + timedelta(hours=1),
        )
        paso = next(s for s in funnel["funnel"] if s["paso"] == "mensaje_recibido")
        assert paso["eventos"] == 1
        assert paso["clientas_unicas"] == 1

    async def test_registrar_con_metadata(self):
        meta = MetadataEvento(query="bikini", productos=["Bikini Tropical"])
        await registrar_evento_funnel(
            "+573001234567", TipoEventoFunnel.PRODUCTO_CONSULTADO, meta,
        )
        funnel = await obtener_funnel(
            datetime.utcnow() - timedelta(hours=1),
            datetime.utcnow() + timedelta(hours=1),
        )
        paso = next(s for s in funnel["funnel"] if s["paso"] == "producto_consultado")
        assert paso["eventos"] == 1

    async def test_metadata_validacion_query_vacio(self):
        meta = MetadataEvento(query="")
        assert meta.query is None  # field_validator convierte "" a None

    async def test_funnel_periodo_vacio(self):
        funnel = await obtener_funnel(
            datetime.utcnow() - timedelta(days=30),
            datetime.utcnow() - timedelta(days=29),
        )
        assert all(s["eventos"] == 0 for s in funnel["funnel"])

    async def test_multiples_clientas(self):
        for i in range(3):
            await registrar_evento_funnel(
                f"+5730012345{i:02d}", TipoEventoFunnel.MENSAJE_RECIBIDO,
            )
        funnel = await obtener_funnel(
            datetime.utcnow() - timedelta(hours=1),
            datetime.utcnow() + timedelta(hours=1),
        )
        paso = next(s for s in funnel["funnel"] if s["paso"] == "mensaje_recibido")
        assert paso["eventos"] == 3
        assert paso["clientas_unicas"] == 3


# ── Tests escalaciones con debounce ──────────────────────

@pytest.mark.asyncio
class TestEscalaciones:
    async def test_crear_escalacion(self):
        esc = await crear_escalacion("+573001234567", "pedido no llego", "clienta espera desde hace 5 dias")
        assert esc is not None
        assert esc.estado == "pendiente"

    async def test_debounce_30min(self):
        esc1 = await crear_escalacion("+573009999999", "primera", "resumen 1")
        assert esc1 is not None
        esc2 = await crear_escalacion("+573009999999", "segunda", "resumen 2")
        assert esc2 is None  # debounce: no crear duplicado

    async def test_resolver_escalacion(self):
        esc = await crear_escalacion("+573008888888", "test", "test resumen")
        assert esc is not None
        ok = await resolver_escalacion(esc.id)
        assert ok is True
        escalaciones = await obtener_escalaciones("pendiente")
        assert all(e.id != esc.id for e in escalaciones)

    async def test_resolver_no_existente(self):
        ok = await resolver_escalacion(99999)
        assert ok is False


# ── Tests A/B assignment deterministico ──────────────────

class TestABAssignment:
    def test_deterministic(self):
        v1 = asignar_variante_ab("+573001234567", 1)
        v2 = asignar_variante_ab("+573001234567", 1)
        assert v1 == v2  # mismo telefono + test = misma variante

    def test_different_phones(self):
        results = set()
        for i in range(100):
            v = asignar_variante_ab(f"+57300{i:07d}", 1)
            results.add(v)
        assert results == {"a", "b"}  # ambas variantes deben aparecer

    def test_different_tests(self):
        v1 = asignar_variante_ab("+573001234567", 1)
        v2 = asignar_variante_ab("+573001234567", 2)
        # Puede o no ser diferente, pero no debe dar error
        assert v1 in ("a", "b")
        assert v2 in ("a", "b")
