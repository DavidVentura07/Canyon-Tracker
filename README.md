# 🚴 Canyon MX Price Tracker

Rastreador automático de precio y disponibilidad para:  
**Canyon Endurace AllRoad — Silver Mercury — Talla S**

Corre cada 6 horas en GitHub Actions y te avisa por email si el precio baja o la talla S vuelve a estar disponible.

---

## Archivos del proyecto

```
canyon-tracker/
├── scraper.py                     ← Script principal (Python + Playwright)
├── index.html                     ← Dashboard visual del historial
├── price_history.json             ← Se genera automáticamente
├── last_check.png                 ← Screenshot del último chequeo
└── .github/workflows/tracker.yml ← Workflow de GitHub Actions
```

---

## Paso a paso para instalarlo

### 1. Crear el repositorio en GitHub

1. Ve a [github.com](https://github.com) → **New repository**
2. Nombre sugerido: `canyon-tracker`
3. Visibilidad: **Private** (para que nadie vea tu email)
4. No añadas ningún archivo inicial (README, .gitignore, etc.)
5. Click en **Create repository**

---

### 2. Subir los archivos

Abre la Terminal en tu Mac y ejecuta esto en orden:

```bash
# Entra a la carpeta del proyecto
cd /ruta/donde/guardaste/canyon-tracker

# Inicializa git y sube todo
git init
git add .
git commit -m "feat: canyon price tracker inicial"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/canyon-tracker.git
git push -u origin main
```

Reemplaza `TU_USUARIO` con tu nombre de usuario de GitHub.

---

### 3. Configurar el email (Gmail)

El tracker te manda emails desde tu propia cuenta de Gmail.  
Para eso necesitas una **App Password** (contraseña de aplicación):

1. Ve a [myaccount.google.com/security](https://myaccount.google.com/security)
2. Activa **Verificación en dos pasos** si aún no la tienes
3. Busca **Contraseñas de aplicación** (App Passwords)
4. Crea una nueva: Aplicación → "Correo", Dispositivo → "Mac"
5. Copia la contraseña de 16 caracteres que te da Google

---

### 4. Agregar los Secrets en GitHub

En tu repositorio de GitHub:

1. **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Agrega estos tres secrets:

| Nombre              | Valor                              |
|---------------------|------------------------------------|
| `GMAIL_USER`        | tu-email@gmail.com                 |
| `GMAIL_APP_PASSWORD`| la contraseña de 16 caracteres     |
| `ALERT_EMAIL`       | donde quieres recibir las alertas  |

---

### 5. Activar GitHub Actions

1. En tu repositorio, ve a la pestaña **Actions**
2. Si te pide habilitar workflows, acepta
3. Verás el workflow **"Canyon Price Tracker"**
4. Haz click en **Run workflow** → **Run workflow** (para probarlo de inmediato)
5. Espera ~2-3 minutos y revisa los logs

---

### 6. Ver el dashboard

Tienes dos opciones para ver el historial visual:

**Opción A — GitHub Pages (recomendada):**
1. Settings → Pages → Source: **Deploy from branch** → `main` → `/ (root)`
2. Guarda. En ~1 minuto tendrás una URL tipo:  
   `https://TU_USUARIO.github.io/canyon-tracker/`

**Opción B — Local:**
Descarga `index.html` y `price_history.json` a la misma carpeta y ábrelo en Safari/Chrome.

---

## Frecuencia de chequeo

El tracker corre **4 veces al día** (cada 6 horas).  
Si quieres cambiarlo, edita la línea `cron` en `.github/workflows/tracker.yml`:

```yaml
# Ejemplos:
- cron: "0 */6 * * *"   # cada 6 horas (default)
- cron: "0 */4 * * *"   # cada 4 horas
- cron: "0 */12 * * *"  # cada 12 horas
- cron: "0 8 * * *"     # solo una vez al día a las 8am UTC
```

---

## Cuándo te llega email

- 🔻 El precio baja **1% o más** vs la última revisión
- 🟢 La talla S pasa de **sin stock → disponible**

Si quieres cambiar el umbral de bajada (ej. solo notificar si baja 5%),  
edita esta línea en `scraper.py`:

```python
NOTIFY_THRESHOLD_PCT = 5.0   # cambia 1.0 por 5.0
```

---

## Costos

Todo gratuito:
- GitHub Actions: 2,000 minutos/mes gratis (usas ~120/mes con 4 checks diarios)
- GitHub Pages: gratuito
- Gmail SMTP: gratuito

---

## Historial de precios

El archivo `price_history.json` se actualiza automáticamente en cada chequeo.  
Formato de cada registro:

```json
{
  "price_usd": 1099.0,
  "size_available": false,
  "timestamp": "2026-06-15 12:00 UTC",
  "url": "https://www.canyon.com/es-mx/...",
  "color": "Silver Mercury",
  "size_target": "S"
}
```
