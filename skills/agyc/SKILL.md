---
name: agyc
description: >-
  Administrador multi-cuenta de Google AI Pro (PRO) y Google AI Ultra (ULTRA)
  para Google Antigravity 1.5.10+ (agyc v1.6). Usa esta habilidad cuando el
  usuario pregunte por el estado de sus cuentas, paneles activos EN USO, notas y
  reservas (agyc note/lock/unlock), rotación inteligente Reserva ULTRA +
  Burn-First (agyc auto [--allow-ultra]), alertas <=15% en Herdr, diagnóstico
  (agyc doctor [--fix]) o barras en vivo (agyc-statusline, agyc-titleline,
  agyc-topbar).
---

# Administrador Multi-Cuenta `agyc` (v1.6)

Esta habilidad permite al agente consultar y administrar hasta 15 cuentas (`agy01`..`agy15`) de **Google AI Pro (`PRO`)** y **Google AI Ultra (`ULTRA`)** en Google Antigravity CLI `1.5.10+`.

## Esquema Unificado de Cuotas y Panel de 131 Columnas

El consumo se consolida en **2 grupos unificados** sobre ventanas deslizantes de **5 Horas (`5H`, NO cuota diaria)** y **Semanal (`Sem`, 168h)**:
1. **Grupo `GEMINI`:** `Gemini 4 Carbon` *(exclusivo `ULTRA`)*, `Gemini 4 Argon`, `Gemini 4 Hydrogen`, `Orchestrator (Carbon/Argon)`, `Gemini 3.8 Flash`.
2. **Grupo `CLAUDE & GPT`:** `Claude Sonnet 4.6 / 5.5`, `Claude Opus 4.6 / 5.5`, `GPT-OSS 120B`.

En `agyc list` (**6 columnas / 131 caracteres de ancho**):
- **Primera línea de cada fila:** `ALIAS` | `CUENTA / EMAIL` | `PLAN` (`PRO`/`ULTRA`) | `ESTADO` (`*ACTIVA+DEF`, `EN USO`, `🔒 RESERVADA`, `LISTA`) | `GEMINI 5H` | `CLAUDE & GPT 5H`.
- **Segunda línea de cada fila:** nota/motivo bajo `CUENTA / EMAIL`, panel en vivo bajo `ESTADO` (`▶ en p1`, `▶ en p2`) y barras `Sem:` de ambos grupos.
- Muestra **`Disponible`** al 100% íntegro sin ciclo abierto, o cuenta regresiva real `(4h 25m)` / `(6d 23h)` con consumo activo.

## Comandos Disponibles (`v1.6`)

### Consulta, notas y reservas por cuenta
- `agyc` / `agyc list` (`-r` para refrescar en vivo, `--json` para salida estructurada): estado completo de cuentas, cuotas, paneles `EN USO`, notas y bloqueos.
- `agyc quota [alias]`: desglose detallado por modelo y hora exacta de reinicio.
- `agyc note <alias> "<texto>"` (o `--clear`): añade o limpia una nota descriptiva en la cuenta.
- `agyc lock <alias> "[motivo]"`: marca la cuenta como `🔒 RESERVADA` para que `agyc auto` y las sugerencias de reemplazo nunca la toquen.
- `agyc unlock <alias>`: libera la reserva de una cuenta bloqueada.

### Rotación inteligente *"Reserva ULTRA + Burn-First"* y cambio de cuenta
- `agyc auto [--allow-ultra]`: autodetecta el modelo activo en `settings.json` y elige la mejor cuenta libre aplicando:
  1. **Anti-colisión:** excluye `is_revoked`, cuentas `🔒 RESERVADA` (`locked`) y cuentas `EN USO` en otros paneles (`▶ en pX`).
  2. **Reserva ULTRA:** en `Carbon` (`agyc auto carbon` / `ultra`) exige exclusivamente `ULTRA`; en modelos estándar (`Argon`, `3.8 Flash`, `Claude`, `GPT`) prioriza cuentas **`PRO`** saludables y solo usa `ULTRA` con `--allow-ultra` o si no quedan cuentas `PRO` disponibles.
  3. **Burn-First:** prioriza quemar cuentas con ventana `5H` ya abierta (`15% < 5H < 100%`) antes de estrenar cuentas al `100% Disponible`.
- `agyc auto [gemini|claude|carbon|ultra] [--allow-ultra]`: fuerza el grupo objetivo de evaluación.
- `agyc <alias>` / `agyc switch <alias>` y `agyc default <alias>`: cambio directo o fijación de cuenta predeterminada.

### Diagnóstico, mantenimiento y tests
- `agyc doctor [--fix]`: audita y auto-repara permisos `0700`/`0600`, symlinks en `~/.agyc_homes/*`, deduplicación `.npm -> ~/.npm` y hooks TUI (`statusLine`, `title`) / Herdr.
- `agyc add [alias]` / `agyc renew <alias>`: alta o renovación OAuth en navegador.
- `agyc update` (o `agy update`): actualiza `lib/agyc_core.py`, binarios, barras y motor `agy-real`.
- `agyc rm <alias>` / `agyc wipe`: baja de cuenta o limpieza total (solo bajo orden explícita del usuario).
- Suite de tests del repositorio: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests` (núcleo en `lib/agyc_core.py`).

## Telemetría en Vivo y Alerta `≤15%` en Herdr

1. **`agyc-statusline` (Pie de `agy` + bordes Herdr + Alerta `≤15%`):**
   - Renderiza `5H → Ctx → Sem` y sincroniza `pane.report_metadata` en Herdr.
   - Al caer a **`≤15%`** (`min(5H, Sem) <= 15%`), añade el badge `⚠ ≤15%` (`⚠ AGOTADA` al `0%`), antepone `⚠` en el borde del panel y envía **1 único Toast por ciclo en Herdr** (`~/.cache/agyc/low_quota_alert_<alias>_<familia>.json`) sugiriendo la mejor cuenta libre compatible.
2. **`agyc-titleline`:** symlink a `agyc-statusline` en `"title"` de `settings.json` (`/title on|off`).
3. **`agyc-topbar`:** widget global (`<20ms`) para `[[ui.tab_bar_right]]` en `~/.config/herdr/config.toml`.

## Perfiles HOME Aislados y Pautas para el Agente

```text
Panel 1 → agy01   (HOME=~/.agyc_homes/agy01, ULTRA: dev1@gmail.com → Gemini 4 Carbon)
Panel 2 → agy02   (HOME=~/.agyc_homes/agy02, PRO:   dev2@gmail.com → Claude Sonnet 5.5)
Panel 3 → agy03   (HOME=~/.agyc_homes/agy03, PRO:   dev3@gmail.com → 🔒 RESERVADA)
```

1. **Consultas:** usar `agyc list` o `agyc list --json` (`-r` si se pide estado en vivo) sin imprimir tokens OAuth ni secretos de `accounts/*.json`.
2. **Rotación sin colisiones:** respetar siempre cuentas `EN USO` en otros paneles y cuentas `🔒 RESERVADA`; proteger cuentas `ULTRA` salvo para `Gemini 4 Carbon` o `--allow-ultra` explícito.
3. **Reparación segura:** ante anomalías de permisos, symlinks o `.npm` duplicados en `.agyc_homes`, usar `agyc doctor` / `agyc doctor --fix`. Ejecutar `rm`, `wipe` o `update` solo por petición explícita del usuario.
