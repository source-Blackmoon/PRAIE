"""
Módulo de integración con Shopify Admin API — PRAIE
Sincroniza carritos abandonados y consulta el catálogo de productos.
"""

import os
import re
import logging
from datetime import datetime, timedelta, timezone

import httpx

from agent.memory import guardar_checkout, marcar_checkout_completado

logger = logging.getLogger("agentkit.shopify")

SHOPIFY_STORE_URL = os.getenv("SHOPIFY_STORE_URL", "")
SHOPIFY_ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN", "")
API_VERSION = "2024-10"


def _headers() -> dict:
    return {
        "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json",
    }


def _base_url() -> str:
    store = SHOPIFY_STORE_URL.rstrip("/")
    if not store.startswith("http"):
        store = f"https://{store}"
    return f"{store}/admin/api/{API_VERSION}"


def _formatear_telefono(telefono: str) -> str:
    """Normaliza a formato Colombia: 57XXXXXXXXXX."""
    limpio = "".join(filter(str.isdigit, telefono))
    if len(limpio) == 10 and limpio.startswith("3"):
        limpio = "57" + limpio
    return limpio


def _formatear_precio_cop(valor: float) -> str:
    """Formatea un precio en pesos colombianos: $164.900 COP"""
    return f"${valor:,.0f}".replace(",", ".") + " COP"


def _formatear_total(total: str) -> str:
    try:
        return _formatear_precio_cop(float(total))
    except Exception:
        return total


def _parsear_checkout(checkout: dict) -> dict | None:
    """Extrae campos relevantes de un checkout de Shopify."""
    # Teléfono — varios campos posibles
    telefono = (
        checkout.get("phone") or
        checkout.get("billing_address", {}).get("phone") or
        checkout.get("shipping_address", {}).get("phone") or
        (checkout.get("customer") or {}).get("phone") or ""
    )
    if not telefono:
        return None

    telefono = _formatear_telefono(telefono)

    nombre = (
        checkout.get("customer", {}).get("first_name") or
        checkout.get("billing_address", {}).get("first_name") or
        "amiga"
    )

    items = checkout.get("line_items", [])
    productos = ", ".join(
        f"{it.get('title', 'producto')} (x{it.get('quantity', 1)})"
        for it in items[:3]
    ) or "tu vestido de baño"

    total = _formatear_total(checkout.get("total_price", ""))

    url_carrito = checkout.get("abandoned_checkout_url") or "https://praie.co/checkout"

    checkout_id = str(checkout.get("id") or checkout.get("token", ""))

    return {
        "checkout_id": checkout_id,
        "telefono": telefono,
        "nombre": nombre,
        "productos": productos,
        "total": total,
        "url_carrito": url_carrito,
        "completado": checkout.get("completed_at") is not None,
    }


GRAPHQL_QUERY = """
query ObtenerCarritosAbandonados($filtro: String!) {
  abandonedCheckouts(first: 250, query: $filtro) {
    edges {
      node {
        id
        createdAt
        completedAt
        abandonedCheckoutUrl
        totalPriceSet {
          shopMoney { amount currencyCode }
        }
        customer {
          firstName
          phone
        }
        billingAddress {
          firstName
          phone
        }
        shippingAddress {
          firstName
          phone
        }
        lineItems(first: 5) {
          edges {
            node { title quantity }
          }
        }
      }
    }
  }
}
"""


def _parsear_checkout_graphql(node: dict) -> dict | None:
    """Extrae campos relevantes de un nodo GraphQL de checkout."""
    telefono = (
        (node.get("customer") or {}).get("phone") or
        (node.get("billingAddress") or {}).get("phone") or
        (node.get("shippingAddress") or {}).get("phone") or ""
    )
    if not telefono:
        return None

    telefono = _formatear_telefono(telefono)

    nombre = (
        (node.get("customer") or {}).get("firstName") or
        (node.get("billingAddress") or {}).get("firstName") or
        (node.get("shippingAddress") or {}).get("firstName") or
        "amiga"
    )

    items = [e["node"] for e in node.get("lineItems", {}).get("edges", [])]
    productos = ", ".join(
        f"{it.get('title', 'producto')} (x{it.get('quantity', 1)})"
        for it in items[:3]
    ) or "tu vestido de baño"

    precio = node.get("totalPriceSet", {}).get("shopMoney", {})
    total = _formatear_total(precio.get("amount", ""))

    checkout_id = node.get("id", "").split("/")[-1]

    return {
        "checkout_id": checkout_id,
        "telefono": telefono,
        "nombre": nombre,
        "productos": productos,
        "total": total,
        "url_carrito": node.get("abandonedCheckoutUrl") or "https://praie.co/checkout",
        "completado": node.get("completedAt") is not None,
    }


async def obtener_checkouts_shopify(horas_atras: int = 48, horas_minimo: int = 2) -> list[dict]:
    """
    Consulta la API GraphQL de Shopify y retorna checkouts abandonados.
    Solo retorna los que tienen teléfono, NO están completados, y tienen
    al menos `horas_minimo` horas de abandono.
    """
    if not SHOPIFY_ACCESS_TOKEN or SHOPIFY_ACCESS_TOKEN.startswith("REEMPLAZAR"):
        logger.warning("SHOPIFY_ACCESS_TOKEN no configurado — saltando sincronización")
        return []

    ahora = datetime.now(timezone.utc)
    desde = (ahora - timedelta(hours=horas_atras)).strftime("%Y-%m-%dT%H:%M:%SZ")
    hasta = (ahora - timedelta(hours=horas_minimo)).strftime("%Y-%m-%dT%H:%M:%SZ")

    url = f"{_base_url()}/graphql.json"
    payload = {
        "query": GRAPHQL_QUERY,
        "variables": {"filtro": f"created_at:>{desde} AND created_at:<{hasta}"},
    }
    logger.info(f"Sincronizando carritos abandonados entre {horas_minimo}h y {horas_atras}h atrás")

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.post(url, json=payload, headers=_headers())
            if r.status_code == 401:
                logger.error("Shopify 401 — verifica SHOPIFY_ACCESS_TOKEN")
                return []
            if r.status_code != 200:
                logger.error(f"Shopify error {r.status_code}: {r.text[:200]}")
                return []

            data = r.json()
            if "errors" in data:
                for e in data["errors"]:
                    logger.warning(f"Shopify GraphQL warning: {e.get('message')}")
                # Solo abortar si no hay datos en absoluto
                if not data.get("data"):
                    return []

            edges = (
                data.get("data", {})
                    .get("abandonedCheckouts", {})
                    .get("edges", [])
            )
            logger.info(f"Shopify retornó {len(edges)} checkouts")

            resultado = []
            for edge in edges:
                parsed = _parsear_checkout_graphql(edge["node"])
                if parsed:
                    resultado.append(parsed)

            logger.info(f"Checkouts con teléfono: {len(resultado)}")
            return resultado

    except httpx.TimeoutException:
        logger.error("Timeout al conectar con Shopify")
        return []
    except Exception as e:
        logger.error(f"Error inesperado Shopify: {e}")
        return []


async def sincronizar_checkouts() -> dict:
    """
    Sincroniza carritos abandonados de Shopify a la base de datos local.
    Retorna resumen: {nuevos, completados, sin_telefono, errores}
    """
    checkouts = await obtener_checkouts_shopify(horas_atras=48, horas_minimo=2)

    nuevos = 0
    completados = 0

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
            except Exception as e:
                logger.error(f"Error guardando checkout {c['checkout_id']}: {e}")

    resumen = {"nuevos": nuevos, "completados_marcados": completados, "total": len(checkouts)}
    logger.info(f"Sincronización Shopify: {resumen}")
    return resumen


# ── Webhooks ──────────────────────────────────────────────

# Tópicos válidos en Shopify API 2022-07+
# checkouts/create y checkouts/update fueron eliminados — se usa polling via GraphQL
WEBHOOK_TOPICS = [
    {"topic": "orders/paid",    "path": "/shopify/orden"},
    {"topic": "orders/create",  "path": "/shopify/orden"},
]


async def listar_webhooks() -> list[dict]:
    """Retorna los webhooks actualmente registrados en Shopify."""
    if not SHOPIFY_ACCESS_TOKEN or SHOPIFY_ACCESS_TOKEN.startswith("REEMPLAZAR"):
        return []
    url = f"{_base_url()}/webhooks.json"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url, headers=_headers())
            if r.status_code == 200:
                return r.json().get("webhooks", [])
            logger.error(f"Shopify listar webhooks {r.status_code}: {r.text[:200]}")
            return []
    except Exception as e:
        logger.error(f"Error listando webhooks: {e}")
        return []


async def registrar_webhooks(base_url: str) -> dict:
    """
    Registra los webhooks necesarios en Shopify apuntando a base_url.
    Omite los que ya existen. Retorna {registrados, existentes, errores}.
    """
    base_url = base_url.rstrip("/")
    existentes = await listar_webhooks()
    topics_existentes = {w["topic"] for w in existentes}

    registrados = []
    errores = []

    async with httpx.AsyncClient(timeout=15.0) as client:
        for wh in WEBHOOK_TOPICS:
            topic = wh["topic"]
            endpoint = f"{base_url}{wh['path']}"

            if topic in topics_existentes:
                logger.info(f"Webhook ya existe: {topic}")
                continue

            payload = {
                "webhook": {
                    "topic": topic,
                    "address": endpoint,
                    "format": "json",
                }
            }
            try:
                r = await client.post(
                    f"{_base_url()}/webhooks.json",
                    json=payload,
                    headers=_headers(),
                )
                if r.status_code in (200, 201):
                    registrados.append(topic)
                    logger.info(f"Webhook registrado: {topic} → {endpoint}")
                else:
                    errores.append(f"{topic}: HTTP {r.status_code} — {r.text[:100]}")
                    logger.error(f"Error registrando {topic}: {r.status_code}")
            except Exception as e:
                errores.append(f"{topic}: {e}")

    return {
        "registrados": registrados,
        "ya_existian": [t for t in topics_existentes if t in {w["topic"] for w in WEBHOOK_TOPICS}],
        "errores": errores,
    }


async def eliminar_webhook(webhook_id: int) -> bool:
    """Elimina un webhook por ID."""
    url = f"{_base_url()}/webhooks/{webhook_id}.json"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.delete(url, headers=_headers())
            return r.status_code == 200
    except Exception:
        return False


GRAPHQL_BUSCAR_PRODUCTOS = """
query BuscarProductos($query: String!, $first: Int!) {
  products(first: $first, query: $query) {
    edges {
      node {
        title
        handle
        status
        descriptionHtml
        variants(first: 30) {
          edges {
            node {
              title
              price
              compareAtPrice
              availableForSale
              inventoryQuantity
            }
          }
        }
        featuredImage {
          url
        }
      }
    }
  }
}
"""


def _strip_html(text: str) -> str:
    return re.sub(r'<[^>]+>', ' ', text or '').strip()


async def buscar_productos_shopify(query: str, limit: int = 2) -> list[dict]:
    """
    Busca productos activos en Shopify por término de búsqueda.
    Retorna lista con título, precio, tallas disponibles, URL e imagen.
    """
    if not SHOPIFY_ACCESS_TOKEN or SHOPIFY_ACCESS_TOKEN.startswith("REEMPLAZAR"):
        logger.warning("SHOPIFY_ACCESS_TOKEN no configurado — no se puede buscar productos")
        return []

    limit = max(1, min(limit, 5))
    # Siempre filtrar productos activos desde Shopify
    query_completa = f"{query} status:active".strip() if query else "status:active"
    url = f"{_base_url()}/graphql.json"
    payload = {
        "query": GRAPHQL_BUSCAR_PRODUCTOS,
        "variables": {"query": query_completa, "first": limit + 5},  # pedir extra para filtrar sin inventario
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(url, json=payload, headers=_headers())
            if r.status_code != 200:
                logger.error(f"Shopify productos {r.status_code}: {r.text[:200]}")
                return []

            data = r.json()
            logger.info(f"Shopify productos raw: {str(data)[:500]}")
            if "errors" in data and not data.get("data"):
                logger.error(f"Shopify GraphQL error: {data['errors']}")
                return []

            edges = data.get("data", {}).get("products", {}).get("edges", [])
            resultado = []

            for edge in edges:
                p = edge["node"]

                # Ignorar productos no activos (doble verificación)
                if p.get("status", "ACTIVE") != "ACTIVE":
                    continue

                variantes = [e["node"] for e in p.get("variants", {}).get("edges", [])]

                # Tallas con stock disponible (availableForSale=True e inventoryQuantity>0)
                tallas = [
                    v["title"] for v in variantes
                    if v.get("availableForSale")
                    and v.get("inventoryQuantity", 1) > 0
                    and v.get("title") != "Default Title"
                ]

                # Si ninguna talla tiene stock, omitir el producto
                if not tallas and any(v.get("title") != "Default Title" for v in variantes):
                    logger.info(f"Producto sin stock omitido: {p.get('title')}")
                    continue

                precios = sorted(set(float(v["price"]) for v in variantes if v.get("price")))
                if len(precios) == 1:
                    precio_str = _formatear_precio_cop(precios[0])
                elif len(precios) > 1:
                    precio_str = f"{_formatear_precio_cop(precios[0])} – {_formatear_precio_cop(precios[-1])}"
                else:
                    precio_str = "Consultar"

                if len(resultado) >= limit:
                    break

                imagen = (p.get("featuredImage") or {}).get("url", "")

                resultado.append({
                    "titulo": p.get("title", ""),
                    "precio": precio_str,
                    "tallas": tallas,
                    "url": f"https://praie.co/products/{p.get('handle', '')}",
                    "imagen": imagen,
                    "descripcion": _strip_html(p.get("descriptionHtml", ""))[:200],
                })

            logger.info(f"Shopify productos encontrados: {len(resultado)} para query '{query}'")
            return resultado

    except httpx.TimeoutException:
        logger.error("Timeout buscando productos en Shopify")
        return []
    except Exception as e:
        logger.error(f"Error buscando productos: {e}")
        return []


async def buscar_ofertas_shopify(limit: int = 3) -> list[dict]:
    """
    Busca productos en oferta (con precio rebajado) en Shopify.
    Estrategia 1: query con tag:sale o tag:oferta.
    Estrategia 2: filtrar client-side por compareAtPrice > price.
    """
    if not SHOPIFY_ACCESS_TOKEN or SHOPIFY_ACCESS_TOKEN.startswith("REEMPLAZAR"):
        logger.warning("SHOPIFY_ACCESS_TOKEN no configurado")
        return []

    limit = max(1, min(limit, 5))
    url = f"{_base_url()}/graphql.json"

    # Intentar varias estrategias de búsqueda
    queries_oferta = [
        "compare_at_price:>0 status:active",
        "(tag:sale OR tag:oferta OR tag:descuento) status:active",
        "tag:sale status:active",
    ]

    for q in queries_oferta:
        payload = {
            "query": GRAPHQL_BUSCAR_PRODUCTOS,
            "variables": {"query": q, "first": 20},
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.post(url, json=payload, headers=_headers())
                if r.status_code != 200:
                    continue
                data = r.json()
                edges = data.get("data", {}).get("products", {}).get("edges", [])
        except Exception as e:
            logger.error(f"Error buscando ofertas ({q}): {e}")
            continue

        resultado = []
        for edge in edges:
            p = edge["node"]
            if p.get("status") != "ACTIVE":
                continue

            variantes = [e["node"] for e in p.get("variants", {}).get("edges", [])]

            # Filtrar variantes con stock y con descuento real
            variantes_oferta = [
                v for v in variantes
                if v.get("availableForSale")
                and v.get("inventoryQuantity", 1) > 0
                and v.get("compareAtPrice")
                and float(v["compareAtPrice"]) > float(v["price"])
            ]

            # Si ninguna variante tiene descuento, omitir el producto
            if not variantes_oferta:
                continue

            tallas = [
                v["title"] for v in variantes_oferta
                if v.get("title") != "Default Title"
            ]

            precios = sorted(set(float(v["price"]) for v in variantes_oferta))
            precios_antes = sorted(set(float(v["compareAtPrice"]) for v in variantes_oferta))

            precio_str = _formatear_precio_cop(precios[0]) if precios else "Consultar"
            precio_antes_str = _formatear_precio_cop(precios_antes[-1]) if precios_antes else ""

            resultado.append({
                "titulo": p.get("title", ""),
                "precio": precio_str,
                "precio_antes": precio_antes_str,
                "tallas": tallas,
                "url": f"https://praie.co/products/{p.get('handle', '')}",
                "imagen": (p.get("featuredImage") or {}).get("url", ""),
            })

            if len(resultado) >= limit:
                break

        if resultado:
            logger.info(f"Shopify ofertas encontradas: {len(resultado)} (query: {q})")
            return resultado

    logger.info("No se encontraron productos en oferta en Shopify")
    return []


GRAPHQL_CONSULTAR_PEDIDOS = """
query ConsultarPedidos($query: String!) {
  orders(first: 3, query: $query, sortKey: CREATED_AT, reverse: true) {
    edges {
      node {
        name
        createdAt
        displayFinancialStatus
        displayFulfillmentStatus
        totalPriceSet {
          shopMoney { amount currencyCode }
        }
        fulfillments(first: 5) {
          trackingInfo(first: 5) {
            company
            number
            url
          }
          status
        }
        lineItems(first: 5) {
          edges {
            node { title quantity }
          }
        }
      }
    }
  }
}
"""

_STATUS_FINANCIERO = {
    "PAID": "Pagado",
    "PENDING": "Pendiente de pago",
    "PARTIALLY_PAID": "Parcialmente pagado",
    "REFUNDED": "Reembolsado",
    "PARTIALLY_REFUNDED": "Parcialmente reembolsado",
    "VOIDED": "Anulado",
    "AUTHORIZED": "Autorizado",
}

_STATUS_ENVIO = {
    "FULFILLED": "Enviado",
    "UNFULFILLED": "En preparación",
    "PARTIALLY_FULFILLED": "Parcialmente enviado",
    "IN_PROGRESS": "En proceso",
    "ON_HOLD": "En espera",
    "SCHEDULED": "Programado",
}


def _extraer_tracking(fulfillments: list[dict]) -> list[dict]:
    """Extrae todas las entradas de tracking de los fulfillments de un pedido."""
    entries = []
    for ful in fulfillments:
        status = ful.get("status", "")
        for info in ful.get("trackingInfo", []):
            company = info.get("company", "")
            number = info.get("number", "")
            url = info.get("url", "")
            if number or company:
                entries.append({
                    "transportadora": company or "Otro",
                    "numero": number,
                    "url": url,
                    "estado_fulfillment": status,
                })
    return entries


async def consultar_pedido_shopify(telefono: str) -> list[dict]:
    """
    Consulta los últimos pedidos de una clienta por teléfono.
    Retorna lista con nombre del pedido, estado, tracking, productos.
    """
    if not SHOPIFY_ACCESS_TOKEN or SHOPIFY_ACCESS_TOKEN.startswith("REEMPLAZAR"):
        logger.warning("SHOPIFY_ACCESS_TOKEN no configurado")
        return []

    from agent.utils import normalizar_telefono_e164
    telefono_e164 = normalizar_telefono_e164(telefono)
    if not telefono_e164:
        return []

    url = f"{_base_url()}/graphql.json"
    payload = {
        "query": GRAPHQL_CONSULTAR_PEDIDOS,
        "variables": {"query": f"phone:{telefono_e164}"},
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(url, json=payload, headers=_headers())
            if r.status_code != 200:
                logger.error(f"Shopify pedidos {r.status_code}: {r.text[:200]}")
                return []

            data = r.json()
            if "errors" in data and not data.get("data"):
                logger.error(f"Shopify GraphQL error pedidos: {data['errors']}")
                return []

            edges = data.get("data", {}).get("orders", {}).get("edges", [])
            resultado = []

            for edge in edges:
                node = edge["node"]
                items = [e["node"] for e in node.get("lineItems", {}).get("edges", [])]
                productos = ", ".join(
                    f"{it.get('title', 'producto')} (x{it.get('quantity', 1)})"
                    for it in items[:3]
                )

                precio = node.get("totalPriceSet", {}).get("shopMoney", {})
                total = _formatear_total(precio.get("amount", ""))

                # Tracking — recolectar todos los fulfillments y tracking entries
                tracking_entries = _extraer_tracking(node.get("fulfillments", []))

                estado_financiero = _STATUS_FINANCIERO.get(
                    node.get("displayFinancialStatus", ""), node.get("displayFinancialStatus", "")
                )
                estado_envio = _STATUS_ENVIO.get(
                    node.get("displayFulfillmentStatus", ""), node.get("displayFulfillmentStatus", "")
                )

                resultado.append({
                    "nombre_pedido": node.get("name", ""),
                    "fecha": node.get("createdAt", "")[:10],
                    "estado_pago": estado_financiero,
                    "estado_envio": estado_envio,
                    "total": total,
                    "productos": productos,
                    "tracking": tracking_entries,
                })

            logger.info(f"Pedidos encontrados para {telefono_e164}: {len(resultado)}")
            return resultado

    except httpx.TimeoutException:
        logger.error("Timeout consultando pedidos en Shopify")
        return []
    except Exception as e:
        logger.error(f"Error consultando pedidos: {e}")
        return []


async def consultar_pedido_por_email_shopify(email: str) -> list[dict]:
    """
    Consulta los últimos pedidos de una clienta por email.
    Misma estructura de retorno que consultar_pedido_shopify.
    """
    if not SHOPIFY_ACCESS_TOKEN or SHOPIFY_ACCESS_TOKEN.startswith("REEMPLAZAR"):
        logger.warning("SHOPIFY_ACCESS_TOKEN no configurado")
        return []

    email = email.strip().lower()
    if not email or "@" not in email:
        return []

    url = f"{_base_url()}/graphql.json"
    payload = {
        "query": GRAPHQL_CONSULTAR_PEDIDOS,
        "variables": {"query": f"email:{email}"},
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(url, json=payload, headers=_headers())
            if r.status_code != 200:
                logger.error(f"Shopify pedidos por email {r.status_code}: {r.text[:200]}")
                return []

            data = r.json()
            if "errors" in data and not data.get("data"):
                logger.error(f"Shopify GraphQL error pedidos email: {data['errors']}")
                return []

            edges = data.get("data", {}).get("orders", {}).get("edges", [])
            resultado = []

            for edge in edges:
                node = edge["node"]
                items = [e["node"] for e in node.get("lineItems", {}).get("edges", [])]
                productos = ", ".join(
                    f"{it.get('title', 'producto')} (x{it.get('quantity', 1)})"
                    for it in items[:3]
                )

                precio = node.get("totalPriceSet", {}).get("shopMoney", {})
                total = _formatear_total(precio.get("amount", ""))

                tracking_entries = _extraer_tracking(node.get("fulfillments", []))

                estado_financiero = _STATUS_FINANCIERO.get(
                    node.get("displayFinancialStatus", ""), node.get("displayFinancialStatus", "")
                )
                estado_envio = _STATUS_ENVIO.get(
                    node.get("displayFulfillmentStatus", ""), node.get("displayFulfillmentStatus", "")
                )

                resultado.append({
                    "nombre_pedido": node.get("name", ""),
                    "fecha": node.get("createdAt", "")[:10],
                    "estado_pago": estado_financiero,
                    "estado_envio": estado_envio,
                    "total": total,
                    "productos": productos,
                    "tracking": tracking_entries,
                })

            logger.info(f"Pedidos encontrados para email {email}: {len(resultado)}")
            return resultado

    except httpx.TimeoutException:
        logger.error("Timeout consultando pedidos por email en Shopify")
        return []
    except Exception as e:
        logger.error(f"Error consultando pedidos por email: {e}")
        return []


async def verificar_credenciales() -> dict:
    """Verifica que el token de Shopify sea válido consultando la tienda."""
    if not SHOPIFY_ACCESS_TOKEN or SHOPIFY_ACCESS_TOKEN.startswith("REEMPLAZAR"):
        return {"ok": False, "error": "Token no configurado"}

    url = f"{_base_url()}/shop.json"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url, headers=_headers())
            if r.status_code == 200:
                shop = r.json().get("shop", {})
                return {
                    "ok": True,
                    "tienda": shop.get("name", ""),
                    "dominio": shop.get("domain", ""),
                    "plan": shop.get("plan_name", ""),
                }
            return {"ok": False, "error": f"HTTP {r.status_code}", "detalle": r.text[:200]}
    except Exception as e:
        return {"ok": False, "error": str(e)}
