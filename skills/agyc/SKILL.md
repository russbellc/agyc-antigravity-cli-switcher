---
name: agyc
description: >-
  Administrador multi-cuenta de Google AI Pro (PRO) y Google AI Ultra (ULTRA)
  para Google Antigravity 1.5.10+ (agyc v1.5). Usa esta habilidad cuando el
  usuario pregunte por el estado de sus cuentas, planes PRO/ULTRA, cuotas de
  los 2 grupos unificados (Gemini y Claude & GPT), barra de estado/título
  (agyc-statusline, agyc-titleline, agyc-topbar), cambio de cuenta o rotación
  inteligente (agyc auto).
---

# Administrador Multi-Cuenta `agyc` (v1.5)

Esta habilidad permite al agente consultar y administrar hasta 15 cuentas (`agy01`..`agy15`) de **Google AI Pro (`PRO`)** y **Google AI Ultra (`ULTRA`)** en Google Antigravity CLI `1.5.10+`.

## Esquema Unificado de Cuotas (Antigravity 1.5.10)

El consumo de modelos se consolida en **2 grupos unificados** por cuenta, descontando saldo de forma proporcional al costo de tokens sobre dos ventanas móviles compartidas: **5 Horas (`5H`, ventana deslizante, NO cuota diaria)** y **Semanal (`Sem`, 168h)**:

1. **Grupo `GEMINI` (Gemini Models):**
   - `Gemini 4 Carbon` *(exclusivo para cuentas `ULTRA`)*
   - `Gemini 4 Argon`
   - `Gemini 4 Hydrogen`
   - `Orchestrator (Carbon/Argon)`
   - `Gemini 3.8 Flash`
2. **Grupo `CLAUDE & GPT` (Claude & GPT Models):**
   - `Claude Sonnet 4.6 / 5.5`
   - `Claude Opus 4.6 / 5.5`
   - `GPT-OSS 120B`

En `agyc list`, la tabla compacta de **6 columnas** expone:
`ALIAS` | `CUENTA / EMAIL` | `PLAN` (`PRO` / `ULTRA`) | `ESTADO` | `GEMINI (5H / SEMANAL)` | `CLAUDE & GPT (5H / SEMANAL)`
- Cuando una ventana conserva el 100% íntegro sin ciclo abierto, muestra **`Disponible`**.
- Cuando existe consumo activo, muestra el porcentaje disponible restante y el tiempo real hasta el reinicio, ej. `(4h 25m)` o `(6d 23h)`.

## Comandos Disponibles

### Consulta de saldo y planes
- `agyc` o `agyc list`: Tabla de 6 columnas con `PLAN` (`PRO`/`ULTRA`), `ESTADO` y barras `5H` / `Sem` de ambos grupos unificados.
- `agyc list -r` (o `--refresh`): Fuerza consulta en vivo a los servidores de Google para refrescar cuotas, plan y tokens.
- `agyc list --json`: Salida estructurada JSON para procesamiento programático por el agente.
- `agyc quota [alias]`: Desglose detallado de modelos y timestamps exactos de reinicio.

### Cambio y rotación inteligente de cuentas
- `agyc <alias>` o `agyc switch <alias>`: Cambia la cuenta activa global (ej. `agyc switch agy02`).
- `agyc default <alias>`: Fija la cuenta predeterminada para futuros inicios con `agy`.
- `agyc auto`: Detecta el modelo activo en `settings.json` y rota a la cuenta válida con mayor saldo ponderado.
- `agyc auto gemini`: Fuerza la evaluación priorizando el grupo unificado **Gemini** (`PRO` + `ULTRA`).
- `agyc auto claude`: Fuerza la evaluación priorizando el grupo unificado **Claude & GPT** (`PRO` + `ULTRA`).
- `agyc auto carbon` o `agyc auto ultra`: Filtra **exclusivamente cuentas `ULTRA`** y selecciona la que tenga mejor cuota Gemini/Carbon disponible (este mismo filtro `ULTRA` se aplica automáticamente en `agyc auto` cuando el modelo activo es `Gemini 4 Carbon`).

### Autenticación y mantenimiento
- `agyc add [alias]`: Registra una cuenta nueva en el navegador asignando el siguiente correlativo libre (`agy01`..`agy15`).
- `agyc renew <alias>` (o `reauth`): Re-autentica una cuenta con token expirado o verificación de elegibilidad pendiente.
- `agyc update` (o `agy update`): Actualiza `agyc`, preserva el wrapper `agy`, sincroniza barras (`statusline`, `titleline`, `topbar`) y verifica releases oficiales de Antigravity CLI.
- `agyc rm <alias>`: Elimina una cuenta específica y limpia su perfil aislado.
- `agyc wipe`: Purga todas las credenciales registradas con confirmación interactiva (no usar `--force` sin orden explícita del usuario).

## Herramientas de Barra de Estado y Top Bar en Vivo

`agyc v1.5` provee tres componentes de telemetría en tiempo real instalados en `~/.gemini/antigravity-cli/bin/` y `~/.local/bin/`:

1. **`agyc-statusline` (Pie de `agy` + metadatos Herdr):** Configurado en `"statusLine"` de `~/.gemini/antigravity-cli/settings.json`. Muestra al pie del TUI el alias activo, plan (`PRO`/`ULTRA`), rama Git, modelo + esfuerzo, cuota `5H`/`Sem` en vivo y uso de contexto (`Ctx`), además de sincronizar metadatos dinámicos por panel en Herdr (`pane.report_metadata`).
2. **`agyc-titleline` (Top Bar de `agy`):** Symlink `agyc-titleline -> agyc-statusline` configurado en `"title"` de `settings.json` (`/title on|off`). Emite la línea OSC de título dinámico a la barra superior de la ventana/pestaña.
3. **`agyc-topbar` (Barra Superior derecha global en Herdr):** Widget ultraligero (<20ms) para `[[ui.tab_bar_right]]` (`type = "command"`, `command = "agyc-topbar"`) en `~/.config/herdr/config.toml`, detectando la cuenta enfocada en Herdr y mostrando en vivo las cuotas `5H`/`Sem` de Gemini y Claude.

## Perfiles HOME Aislados y Reglas Operativas del Agente

Cada lanzador directo (`agy01`..`agy15`) inyecta `HOME=~/.agyc_homes/<alias>` antes de `os.execv()`, manteniendo un `antigravity-oauth-token` exclusivo por panel mientras comparte `settings.json`, `accounts/`, `conversations/` y `brain/` mediante symlinks:

```text
Panel 1 → agy01   (HOME=~/.agyc_homes/agy01, ULTRA: dev1@gmail.com → Gemini 4 Carbon)
Panel 2 → agy02   (HOME=~/.agyc_homes/agy02, PRO:   dev2@gmail.com → Claude Sonnet 5.5)
Panel 3 → agy03   (HOME=~/.agyc_homes/agy03, PRO:   dev3@gmail.com → Gemini 4 Argon)
```

### Pautas para el agente
1. **Consultas de saldo:** Ejecutar `agyc list` o `agyc list --json` (usar `-r` cuando el usuario pida datos en vivo) y resumir alias, plan (`PRO`/`ULTRA`), cuota disponible y tiempo de reinicio sin imprimir tokens OAuth ni secretos de `accounts/*.json`.
2. **Cuota agotada o cambio a `Gemini 4 Carbon`:** Si el modelo requerido es `Gemini 4 Carbon`, verificar que la cuenta sea **`ULTRA`** o usar `agyc auto carbon` / `agyc auto ultra`. Aplicar la estrategia **"Agotar y Rotar"** (trabajar una cuenta hasta ~15-20% para que su ventana móvil de 5 horas corra en segundo plano mientras se usa la siguiente).
3. **Acciones destructivas o de actualización:** Ejecutar `agyc update`, `agyc rm` o `agyc wipe` solo cuando el usuario lo solicite explícitamente.
