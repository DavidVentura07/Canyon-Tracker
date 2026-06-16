"""
Canyon MX Price & Availability Tracker
Modelo: Endurace AllRoad — Silver Mercury — Talla S
"""

import json
import os
import re
import smtplib
import sys
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# ─── Configuración ────────────────────────────────────────────────────────────

PRODUCT_URL = "https://www.canyon.com/es-mx/bicicletas-de-carretera/gran-fondo/endurace/allroad/endurace-allroad/4164.html"
TARGET_COLOR = "Silver Mercury"
TARGET_SIZE  = "S"

HISTORY_FILE = Path("price_history.json")

# Umbral: solo notificar si el precio baja más de este % respecto al último registrado
NOTIFY_THRESHOLD_PCT = 1.0   # 1% o más de bajada

# ─── Helpers ──────────────────────────────────────────────────────────────────

def load_history() -> list[dict]:
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_history(history: list[dict]) -> None:
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def send_alert(subject: str, body: str) -> None:
    """Envía email vía Gmail SMTP (credenciales en GitHub Secrets)."""
    gmail_user     = os.environ.get("GMAIL_USER", "")
    gmail_password = os.environ.get("GMAIL_APP_PASSWORD", "")
    recipient      = os.environ.get("ALERT_EMAIL", gmail_user)

    if not gmail_user or not gmail_password:
        print("⚠️  Credenciales de email no configuradas — omitiendo notificación.")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = gmail_user
    msg["To"]      = recipient
    msg.attach(MIMEText(body, "html", "utf-8"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_user, gmail_password)
            server.sendmail(gmail_user, recipient, msg.as_string())
        print(f"✅ Alerta enviada a {recipient}")
    except Exception as e:
        print(f"❌ Error enviando email: {e}")


def build_email_body(entry: dict, prev_price: float | None, size_available: bool) -> tuple[str, str]:
    """Devuelve (subject, html_body)."""
    price     = entry["price_usd"]
    timestamp = entry["timestamp"]

    if prev_price and price < prev_price:
        diff      = prev_price - price
        pct       = (diff / prev_price) * 100
        subject   = f"🚨 Canyon Endurace AllRoad bajó ${diff:.0f} USD ({pct:.1f}%)"
        price_msg = (
            f"<p>El precio <strong>bajó de <del>${prev_price:.0f}</del> → ${price:.0f} USD</strong> "
            f"(ahorro de ${diff:.0f} = {pct:.1f}%).</p>"
        )
    else:
        subject   = f"✅ Canyon Tracker — talla S disponible — ${price:.0f} USD"
        price_msg = f"<p>Precio actual: <strong>${price:.0f} USD</strong></p>"

    size_msg = (
        "<p>🟢 <strong>Talla S en stock</strong></p>"
        if size_available
        else "<p>🔴 Talla S <strong>sin stock</strong></p>"
    )

    body = f"""
    <html><body style="font-family:sans-serif;max-width:500px;margin:auto">
      <h2 style="color:#1a1a2e">Canyon Endurace AllRoad — Silver Mercury</h2>
      {price_msg}
      {size_msg}
      <p style="color:#666;font-size:12px">Revisado: {timestamp}</p>
      <a href="{PRODUCT_URL}" style="background:#e63946;color:#fff;padding:10px 20px;
         border-radius:6px;text-decoration:none;display:inline-block;margin-top:8px">
         Ver en Canyon MX →
      </a>
    </body></html>
    """
    return subject, body


# ─── Scraper ──────────────────────────────────────────────────────────────────

def scrape() -> dict:
    """
    Abre la página con Playwright, selecciona el color y extrae precio + tallas.
    Devuelve un dict con keys: price_usd, size_available, timestamp, url.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            locale="es-MX",
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()

        print(f"🌐 Abriendo {PRODUCT_URL}")
        page.goto(PRODUCT_URL, wait_until="domcontentloaded", timeout=60_000)

        # Espera inicial para que cargue el banner de cookies
        page.wait_for_timeout(3_000)

        # ── 0. Cerrar banner de cookies ──────────────────────────────────────
        # Canyon usa OneTrust — intentamos varios selectores posibles
        cookie_selectors = [
            "#onetrust-accept-btn-handler",          # botón estándar OneTrust
            "button#onetrust-accept-btn-handler",
            "[id*='accept'][id*='cookie']",
            "button:has-text('Aceptar todas')",
            "button:has-text('Aceptar todo')",
            "button:has-text('Accept all')",
            "button:has-text('Aceptar')",
            ".js-cookie-accept",
            "[data-testid='cookie-accept']",
        ]
        cookie_dismissed = False
        for sel in cookie_selectors:
            try:
                btn = page.locator(sel).first
                if btn.is_visible(timeout=2_000):
                    btn.click()
                    page.wait_for_timeout(1_500)
                    print(f"🍪 Banner de cookies cerrado (selector: {sel})")
                    cookie_dismissed = True
                    break
            except Exception:
                continue

        if not cookie_dismissed:
            print("⚠️  No se encontró banner de cookies — continuando de todas formas")

        # Espera a que cargue el precio principal (ahora sin el banner)
        try:
            page.wait_for_selector("[data-test-id='product-price'], .productConfiguration__price, .js-product-price", timeout=20_000)
        except PlaywrightTimeoutError:
            print("⚠️  Selector de precio no encontrado; intentando con texto genérico...")

        # Espera adicional para JS
        page.wait_for_timeout(4_000)

        # ── 1. Seleccionar color Silver Mercury ──────────────────────────────
        try:
            color_btn = page.locator(
                f"[aria-label*='{TARGET_COLOR}'], "
                f"[title*='{TARGET_COLOR}'], "
                f"button:has-text('{TARGET_COLOR}')"
            ).first
            if color_btn.is_visible():
                color_btn.click()
                page.wait_for_timeout(2_000)
                print(f"🎨 Color '{TARGET_COLOR}' seleccionado")
            else:
                print(f"⚠️  Botón de color '{TARGET_COLOR}' no visible — continuando sin seleccionar")
        except Exception as e:
            print(f"⚠️  No se pudo seleccionar color: {e}")

        # ── 2. Extraer precio ────────────────────────────────────────────────
        price_usd = None
        price_selectors = [
            "[data-test-id='product-price']",
            ".productConfiguration__price",
            ".js-product-price",
            "[class*='price']",
        ]
        for sel in price_selectors:
            els = page.locator(sel).all()
            for el in els:
                txt = el.inner_text().strip()
                match = re.search(r"[\d,]+(?:\.\d+)?", txt.replace(",", ""))
                if match:
                    candidate = float(match.group())
                    # Los precios de Canyon MX están en rango ~$500–$10,000 USD
                    if 300 < candidate < 15_000:
                        price_usd = candidate
                        print(f"💵 Precio encontrado: ${price_usd} USD  (selector: {sel})")
                        break
            if price_usd:
                break

        if not price_usd:
            # Fallback: buscar en todo el texto de la página
            body_text = page.inner_text("body")
            matches   = re.findall(r"\$\s*([\d,]+(?:\.\d+)?)\s*(?:US\$|USD)?", body_text)
            for m in matches:
                candidate = float(m.replace(",", ""))
                if 300 < candidate < 15_000:
                    price_usd = candidate
                    print(f"💵 Precio encontrado (fallback): ${price_usd} USD")
                    break

        if not price_usd:
            raise ValueError("No se pudo extraer el precio de la página")

        # ── 3. Verificar disponibilidad talla S ──────────────────────────────
        size_available = False
        size_selectors = [
            f"[aria-label*='Talla {TARGET_SIZE}']",
            f"[aria-label*='Size {TARGET_SIZE}']",
            f"button:has-text('{TARGET_SIZE}')",
            f"[data-size='{TARGET_SIZE}']",
            f"[value='{TARGET_SIZE}']",
            f"label:has-text('{TARGET_SIZE}')",
        ]
        for sel in size_selectors:
            els = page.locator(sel).all()
            for el in els:
                txt = el.inner_text().strip()
                aria = el.get_attribute("aria-label") or ""
                classes = el.get_attribute("class") or ""
                is_disabled = (
                    "disabled" in classes.lower()
                    or el.get_attribute("disabled") is not None
                    or "unavailable" in classes.lower()
                    or "agotado" in txt.lower()
                )
                if txt == TARGET_SIZE or aria.strip() == TARGET_SIZE:
                    size_available = not is_disabled
                    status = "✅ disponible" if size_available else "❌ sin stock"
                    print(f"📐 Talla {TARGET_SIZE}: {status}")
                    break
            if size_available is not False:
                break

        # Si no encontramos el botón de talla, reportamos como desconocido
        if not size_available:
            print(f"⚠️  No se pudo confirmar disponibilidad de talla {TARGET_SIZE}")

        # ── 4. Screenshot de evidencia ────────────────────────────────────────
        # Scroll al área del precio para que sea visible en el screenshot
        try:
            price_el = page.locator(
                "[data-test-id='product-price'], "
                ".productConfiguration__price, "
                "[class*='price']"
            ).first
            if price_el.is_visible():
                price_el.scroll_into_view_if_needed()
                page.wait_for_timeout(600)
        except Exception:
            pass
        page.screenshot(path="last_check.png", full_page=False)
        print("📸 Screenshot guardado como last_check.png")

        browser.close()

    return {
        "price_usd":      price_usd,
        "size_available": size_available,
        "timestamp":      datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "url":            PRODUCT_URL,
        "color":          TARGET_COLOR,
        "size_target":    TARGET_SIZE,
    }


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "="*55)
    print(f"  Canyon Tracker — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("="*55)

    history = load_history()
    prev    = history[-1] if history else None

    try:
        entry = scrape()
    except Exception as e:
        print(f"❌ Error en scraping: {e}")
        sys.exit(1)

    history.append(entry)
    save_history(history)
    print(f"\n📝 Historial guardado ({len(history)} registros)")

    # ── Lógica de notificación ──────────────────────────────────────────────
    should_notify = False
    reason        = ""

    if prev is None:
        # Primera vez: solo notificar si talla disponible
        if entry["size_available"]:
            should_notify = True
            reason        = "primera revisión y talla disponible"
    else:
        prev_price    = prev.get("price_usd", 0)
        price_dropped = entry["price_usd"] < prev_price
        drop_pct      = ((prev_price - entry["price_usd"]) / prev_price * 100) if prev_price else 0

        if price_dropped and drop_pct >= NOTIFY_THRESHOLD_PCT:
            should_notify = True
            reason        = f"precio bajó {drop_pct:.1f}%"

        # Talla recién disponible (antes no estaba, ahora sí)
        was_unavailable = not prev.get("size_available", False)
        if entry["size_available"] and was_unavailable:
            should_notify = True
            reason        = reason + (" + " if reason else "") + "talla S recién disponible"

    print(f"\n🔔 Notificación: {'SÍ — ' + reason if should_notify else 'No (sin cambios relevantes)'}")

    if should_notify:
        prev_price = prev["price_usd"] if prev else None
        subject, body = build_email_body(entry, prev_price, entry["size_available"])
        send_alert(subject, body)

    # Resumen final
    print(f"\n📊 Resumen:")
    print(f"   Precio   : ${entry['price_usd']:.0f} USD")
    print(f"   Talla S  : {'✅ Disponible' if entry['size_available'] else '❌ Sin stock'}")
    print(f"   Timestamp: {entry['timestamp']}")
    print()


if __name__ == "__main__":
    main()
