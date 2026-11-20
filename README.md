# agyc — Google Antigravity Multi-Account Switcher (v1.6)

> **Administrador multi-cuenta para Google Antigravity CLI 1.5.10+ (Ubuntu Linux + Windows 10/11)**
> Soporte Google AI Pro (`PRO`) & Google AI Ultra (`ULTRA`) | Detección de paneles en vivo (`EN USO`) | Motor *Reserva ULTRA + Burn-First* | Alertas `≤15%` en Herdr / Toast Win32

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version: v1.6](https://img.shields.io/badge/Version-v1.6-brightgreen.svg)](#historia-de-versiones)
[![Platform: Linux & Windows](https://img.shields.io/badge/Platform-Ubuntu%20Linux%20%7C%20Windows%2010%2F11-orange.svg)](#requisitos)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![Antigravity: 1.5.10+](https://img.shields.io/badge/Google%20Antigravity-1.5.10%2B-red.svg)](https://antigravity.google/docs/cli/reference)

---

## ¿Qué es agyc?

`agyc` convierte Google Antigravity CLI (`agy`) en una estación de trabajo **multi-cuenta de alto rendimiento**. Nació para resolver un cuello de botella real: al programar a tiempo completo con modelos intensivos como `Gemini 4 Carbon`, `Claude Opus 5.5` o `Claude Sonnet 5.5`, las cuotas de una sola suscripción se agotan en mitad de la jornada.

**La solución:** gestionar hasta **15 cuentas (`agy01`..`agy15`)** combinando suscripciones **Google AI Pro (`PRO`)** y **Google AI Ultra (`ULTRA`)** con perfiles `HOME` completamente aislados, detección en vivo de paneles ocupados, reservas/notas por cuenta, alertas automáticas al `≤15%` y rotación inteligente *Reserva ULTRA + Burn-First* para trabajar en **múltiples paneles en paralelo** sin colisiones de tokens.

---

## Características Principales (v1.6)

- 🟢 **Detección en Vivo de Paneles Activos (`EN USO`) y Anti-Colisión** — `agyc list` cruza procesos activos y paneles de Herdr mostrando `EN USO` / `▶ en p2`; `agyc auto` descarta cuentas ocupadas en otros paneles y cuentas `🔒 RESERVADA`.
- 📝 **Notas y Reservas por Cuenta (`note` / `lock` / `unlock`)** — Anota el propósito de cada cuenta (`agyc note <alias> "<texto>"`) o bloquéala contra rotación automática (`agyc lock <alias> "[motivo]"`), visible en la segunda línea de cada fila de `agyc list` manteniendo **131 columnas** exactas.
- 🔥 **Motor *"Reserva ULTRA + Burn-First"* (`agyc auto [--allow-ultra]`)** — Protege las suscripciones `ULTRA` para `Gemini 4 Carbon` priorizando cuentas `PRO` saludables en modelos estándar (salvo `--allow-ultra`), y quema primero ventanas móviles `5H` ya abiertas antes de estrenar cuentas al `100% Disponible`.
- 🔔 **Alerta Inteligente al `≤15%` + Toast Único en Herdr / Win32** — Cuando la cuota efectiva baja a `≤15%`, `agyc-statusline` muestra un badge `⚠ ≤15%` (`⚠ AGOTADA` al `0%`), marca `⚠` en el borde del panel Herdr y lanza **un único toast por ciclo** (`herdr` en Linux/Windows o fallback `System.Windows.Forms.NotifyIcon` en Windows) sugiriendo la mejor cuenta libre disponible.
- 🩺 **Diagnóstico y Auto-Reparación (`agyc doctor [--fix]`)** — Audita y corrige permisos `0700`/`0600`, symlinks rotos, deduplicación de caché `.npm` en `~/.agyc_homes/*` y hooks de `statusLine`, `title` y Herdr.
- 🧩 **Librería Núcleo `lib/agyc_core.py` + Capa `lib/platform/` (`linux.py`, `win32.py`)** — Lógica central desacoplada y capa de abstracción POSIX/Win32 verificada con **38 pruebas unitarias** (`tests/test_agyc.py`).
- 📦 **Migración Portable entre Equipos (`agyc export` / `agyc import`)** — Exporta e importa vinculaciones OAuth en formato `agyc-bundle-v1` (`0600`) entre **Windows ↔ Ubuntu Linux** sin volver a autenticar en navegador en cada máquina.
- 💎 **Soporte Google AI Pro (`PRO`) & Google AI Ultra (`ULTRA`)** — Panel compacto de 6 columnas alineado a los **2 grupos unificados de cuotas** de Antigravity `1.5.10` (**Gemini Models** y **Claude & GPT Models**).
- 🖥️ **Telemetría en Vivo (`5H → Ctx → Sem`)** — Visualización simultánea en el pie de `agy` (`agyc-statusline`), título OSC (`agyc-titleline`), bordes de panel Herdr y barra global superior derecha (`agyc-topbar`).

---

## Esquema Unificado de Cuotas (Google Antigravity 1.5.10)

En Antigravity `1.5.10`, Google unifica el consumo en **2 bolsas globales de cuota** por cuenta. Dentro de cada grupo, todos sus modelos comparten la misma ventana móvil de **5 Horas (`5H`)** y la misma reserva **Semanal (`Sem`, 168h)**, descontando saldo de forma **proporcional al costo de tokens** de cada modelo:

| Grupo de Cuota | Modelos Incluidos | Ventanas Compartidas | Disponibilidad por Plan |
|---|---|---|---|
| **1. Gemini Models** | • `Gemini 4 Carbon` *(exclusivo Ultra)*<br>• `Gemini 4 Argon`<br>• `Gemini 4 Hydrogen`<br>• `Orchestrator (Carbon/Argon)`<br>• `Gemini 3.8 Flash` | Móvil **5H** + **Semanal** | `PRO` y `ULTRA`<br>*(Carbon requiere `ULTRA`)* |
| **2. Claude & GPT Models** | • `Claude Sonnet 4.6 / 5.5`<br>• `Claude Opus 4.6 / 5.5`<br>• `GPT-OSS 120B` | Móvil **5H** + **Semanal** | `PRO` y `ULTRA` |

> **Nota importante sobre las ventanas:** La ventana `5H` es una **ventana móvil de 5 horas** desde el primer consumo activo (no un reinicio fijo diario). Cuando una ventana conserva el 100% íntegro sin gasto activo, `agyc` muestra **`Disponible`**; al iniciar el consumo, muestra la cuenta regresiva exacta, ej. `(4h 25m)` o `(6d 23h)`.

---

## Instalación Rápida

### Ubuntu Linux (`x86_64`)

```bash
git clone https://github.com/russbellc/agyc-antigravity-cli-switcher.git
cd agyc-antigravity-cli-switcher
chmod +x install.sh
./install.sh
source ~/.bashrc
```

### Windows 10/11 (`x86_64`)

```powershell
git clone https://github.com/russbellc/agyc-antigravity-cli-switcher.git
cd agyc-antigravity-cli-switcher
.\install.ps1
# o desde CMD / doble clic:
install.cmd
```

*(Luego abre una nueva terminal para cargar el `User PATH` actualizado con `%LOCALAPPDATA%\agyc\bin` al inicio; si usas Herdr y la barra superior o los bordes aún no aparecen tras instalar, ejecuta `herdr server reload-config` o cierra y vuelve a abrir solo la ventana de Herdr sin perder sesiones).*

El instalador `v1.6` configura y verifica automáticamente:
- **Librería núcleo + capa OS:** `lib/__init__.py`, `lib/agyc_core.py` y `lib/platform/` (`__init__.py`, `linux.py`, `win32.py`) en `~/.gemini/antigravity-cli/lib/` (Linux) o `%USERPROFILE%\.gemini\antigravity-cli\lib\` + `%LOCALAPPDATA%\agyc\lib\` (Windows).
- **Binarios y wrappers:**
  - En Linux: `agyc`, wrapper preservado `agy` (`~/.local/bin/agy` → `agy-real`), `agyc-statusline`, symlink `agyc-titleline -> agyc-statusline`, `agyc-topbar` y lanzadores `agy01`..`agy15`.
  - En Windows: `agyc.cmd`, `agy.cmd` (`bin/agy.cmd`), `agi.cmd`, `agyc-statusline.cmd`, `agyc-titleline.cmd` (`AGYC_INVOKED_AS=agyc-titleline`), `agyc-topbar.cmd` y lanzadores `agy01.cmd`..`agy15.cmd` / `agi01.cmd`..`agi15.cmd` en `%LOCALAPPDATA%\agyc\bin` y `%USERPROFILE%\.gemini\antigravity-cli\bin`.
- **Aislamiento y deduplicación `.npm`:** symlinks en Linux o **NTFS Junctions** (`mklink /J`, sin requerir Administrador) en `%USERPROFILE%\.agyc_homes\*` y ACLs privadas (`0700`/`0600` o `icacls` vía `harden_ntfs_acl`).
- **Telemetría, Herdr y tests:** bloques `"statusLine"` y `"title"` en `settings.json`; en Windows autoconfigura `%APPDATA%\herdr\config.toml` (`show_agent_labels_on_pane_borders = true`, `[[ui.tab_bar_right]]` con `agyc-topbar.cmd`, `[ui.toast]`) y ejecuta `herdr server reload-config`; compilación `py_compile` y ejecución automática de `unittest` en `tests/`.

### Requisitos

- **Sistema operativo:** Ubuntu Linux (`x86_64`) o Windows 10/11 (`x86_64`)
- [Google Antigravity CLI](https://antigravity.google/docs/cli/reference) `1.5.10+` (binario nativo o snap en Linux; `%LOCALAPPDATA%\agy\bin\agy.exe` o descargado con `agyc update` en Windows)
- Python 3.10+ (stdlib puro, sin dependencias externas)
- Al menos 1 cuenta de [Google AI Pro o Google AI Ultra](https://one.google.com/about/plans)

---

## Uso

### Registrar tus cuentas (`PRO` o `ULTRA`) y entrar a Antigravity

```bash
agyc add      # abre el navegador para OAuth → guarda como agy01 (detecta PRO / ULTRA)
agyc add      # segunda cuenta → guarda como agy02
agyc add      # tercera cuenta → guarda como agy03

agy01         # entra con dev1@gmail.com (perfil aislado ~/.agyc_homes/agy01)
agy02         # entra con dev2@gmail.com (perfil aislado ~/.agyc_homes/agy02)
agy03         # entra con dev3@gmail.com (perfil aislado ~/.agyc_homes/agy03)
```

### Notas y reservas por cuenta (`note` / `lock` / `unlock`)

```bash
agyc note agy01 "Solo Carbon crítico"       # añade nota descriptiva a la cuenta
agyc note agy01 --clear                     # limpia la nota de agy01
agyc lock agy03 "Intocable demo cliente"    # reserva la cuenta: agyc auto nunca la tocará
agyc unlock agy03                           # libera la reserva de agy03
```

### Ver estado unificado en vivo (`agyc` / `agyc list` — 131 columnas)

```bash
agyc          # tabla compacta de 6 columnas (131 cols) con paneles activos, notas y reservas
agyc list -r  # fuerza refresco en vivo desde los servidores de Google
```

Ejemplo de salida en `v1.6` (segunda línea por fila con nota/motivo y panel activo manteniendo **131 columnas**):

```text
┌──────────┬──────────────────────┬───────┬───────────────┬───────────────────────────────────┬───────────────────────────────────┐
│ ALIAS    │ CUENTA / EMAIL       │ PLAN  │ ESTADO        │ GEMINI (5H / SEMANAL)             │ CLAUDE & GPT (5H / SEMANAL)       │
├──────────┼──────────────────────┼───────┼───────────────┼───────────────────────────────────┼───────────────────────────────────┤
│ * agy01  │ dev1@gmail.com       │ ULTRA │ *ACTIVA+DEF   │ 5H:  [████████░░]  82% (4h 25m)   │ 5H:  [██████████] 100% Disponible │
│          │ Solo Carbon crítico  │       │ ▶ en p1       │ Sem: [█████████░]  91% (6d 23h)   │ Sem: [████████░░]  78% (6d 23h)   │
├──────────┼──────────────────────┼───────┼───────────────┼───────────────────────────────────┼───────────────────────────────────┤
│   agy02  │ dev2@gmail.com       │ PRO   │ EN USO        │ 5H:  [██████░░░░]  64% (3h 12m)   │ 5H:  [██████░░░░]  60% (4h 25m)   │
│          │ Backend Sprint 4     │       │ ▶ en p2       │ Sem: [█████████░]  92% (6d 10h)   │ Sem: [█████░░░░░]  50% (6d 23h)   │
├──────────┼──────────────────────┼───────┼───────────────┼───────────────────────────────────┼───────────────────────────────────┤
│   agy03  │ dev3@gmail.com       │ PRO   │ 🔒 RESERVADA  │ 5H:  [██████████] 100% Disponible │ 5H:  [██████████] 100% Disponible │
│          │ Intocable demo       │       │               │ Sem: [██████████] 100% Disponible │ Sem: [██████████] 100% Disponible │
└──────────┴──────────────────────┴───────┴───────────────┴───────────────────────────────────┴───────────────────────────────────┘
```

### Rotación inteligente *Reserva ULTRA + Burn-First* (`agyc auto`)

```bash
agyc auto                 # autodetecta modelo activo; protege ULTRA si no es Carbon y evita paneles EN USO
agyc auto --allow-ultra   # permite elegir cuentas ULTRA también en modelos estándar (Argon/Claude)
agyc auto gemini          # evalúa el grupo Gemini (PRO primero + Burn-First; --allow-ultra incluye ULTRA)
agyc auto claude          # evalúa el grupo Claude & GPT (PRO primero + Burn-First)
agyc auto carbon          # filtra EXCLUSIVAMENTE cuentas ULTRA libres y no bloqueadas
agyc auto ultra           # alias de 'carbon': rota únicamente entre cuentas Google AI Ultra
```

### Migrar vinculaciones entre equipos (`agyc export` / `agyc import`)

Permite trasladar tus cuentas ya vinculadas entre máquinas (**Windows ↔ Ubuntu Linux**) sin repetir el flujo OAuth en navegador en cada equipo:

```bash
# En el equipo origen (exporta todas o un alias específico en formato agyc-bundle-v1, modo 0600):
agyc export                               # genera agyc-accounts-bundle.json
agyc export agy01 -o mi-cuenta.json       # exporta solo agy01 (por defecto agyc-agy01.json)

# Transfiere por un canal cifrado (ej. scp):
scp agyc-accounts-bundle.json usuario@otro-equipo:~/

# En el equipo destino:
agyc import ~/agyc-accounts-bundle.json                  # importa, crea HOMEs aislados y sincroniza lanzadores
agyc import ~/mi-cuenta.json --alias work01 --overwrite  # renombra alias único o reemplaza duplicados
rm ~/agyc-accounts-bundle.json                           # elimina el bundle tras importar (contiene tokens OAuth)
```

> **Nota sobre uso simultáneo en paralelo:** Si mantienes los mismos tokens activos en dos equipos a la vez, la renovación automática o rotación de `refresh_token` en un equipo puede invalidar el token en el otro (`invalid_grant`, corregible con `agyc renew <alias>`).

### Diagnóstico y auto-reparación (`agyc doctor`)

```bash
agyc doctor        # audita permisos (0700/0600), symlinks, .npm duplicados y hooks TUI/Herdr
agyc doctor --fix  # repara permisos, reconstruye symlinks, deduplica .npm -> ~/.npm y corrige settings.json
```

---

## Visualización en Vivo y Alerta Inteligente al `≤15%`

`agyc v1.6` mantiene monitoreo continuo en orden **`5H → Ctx → Sem`** en las cuatro superficies e incorpora alerta proactiva de cuota baja:

### 1. Pie de terminal (`agyc-statusline`) + Alerta `≤15%` y Toast Único en Herdr
Cuando la cuota efectiva del modelo activo baja a **`≤15%`** (`min(5H, Sem) <= 15%`):
- **Indicador visual inmediato:** Inserta el badge brillante `⚠ ≤15%` (o `⚠ AGOTADA` si llega a `0%`) en la barra ANSI inferior y antepone `⚠` en el encabezado del panel de Herdr (`display_agent`).
- **Toast único por ciclo en Herdr:** Emite una notificación no bloqueante (`<1ms`, deduplicada por ciclo de reinicio en `~/.cache/agyc/low_quota_alert_<alias>_<familia>.json`) sugiriendo automáticamente una cuenta libre que respete `lock`, paneles activos y *Reserva ULTRA*:

```text
# Pie de terminal con alerta activa (≤15%):
⚡ agy02·PRO │ ⚠ ≤15% │ 🌿 main │ 🤖 Claude Sonnet 5.5 (high) │ 5H: [█░░░░░░░] 12% (⏳ 1h 40m) │ Ctx: [███░░░░░] 36% (90k/250k) │ Sem: [████████] 84% (5d 12h)

# Borde superior del panel en Herdr (display_agent):
⚠ ⚡ agy02 [PRO] · Claude Sonnet 5.5 · 5H:12% Ctx:36% Sem:84%

# Toast automático en Herdr (top-right, 1 vez por ciclo):
⚠ Cuota baja en agy02 (12%)
Sugerida libre: agy04 [PRO] (100% 5H) · Ejecuta: agyc auto
```

### 2. Barra Superior OSC (`agyc-titleline`) y Barra Global Derecha en Herdr (`agyc-topbar`)
- **`agyc-titleline`** (configurado en `"title"` de `settings.json`, `/title on|off`): emite el título dinámico OSC por pestaña/ventana.
- **`agyc-topbar`** (en `[[ui.tab_bar_right]]` de `~/.config/herdr/config.toml`): renderiza en `<20ms` la cuenta y `% Ctx` de la conversación activa en la esquina superior derecha global de Herdr:

```text
⚡ agy01 [ULTRA] │ Gemini 5H: 82% (4h25m) · Ctx: 36% · Sem: 91% (6d23h) │ Claude 5H: 100% · Sem: 78% (6d23h)
```

---

## Comandos Disponibles

| Comando | Descripción |
|---|---|
| `agyc` / `agyc list` | Tabla de 6 columnas (131 cols) con `EN USO` (`▶ en pX`), notas y `🔒 RESERVADA` |
| `agyc list -r` / `--refresh` | Fuerza refresco en vivo de cuotas y plan desde Google |
| `agyc list --json` | Salida estructurada JSON (incluye uso en paneles, notas y reservas) |
| `agy01` .. `agy15` | Entra directo a esa cuenta con perfil `HOME` aislado |
| `agyc note <alias> "<texto>"` | Guarda una nota visible en `agyc list` (`--clear` para borrar) |
| `agyc lock <alias> "[motivo]"` | Reserva/bloquea la cuenta para excluirla de `agyc auto` |
| `agyc unlock <alias>` | Desbloquea una cuenta previamente reservada |
| `agyc auto [--allow-ultra]` | Rotación *Reserva ULTRA + Burn-First* con anti-colisión de paneles activos |
| `agyc auto [gemini\|claude\|carbon\|ultra]` | Fuerza familia objetivo (`carbon`/`ultra` filtra solo `ULTRA`) |
| `agyc doctor [--fix]` | Diagnóstico integral y auto-reparación de permisos, symlinks, `.npm` y hooks |
| `agyc add [alias]` | Registra nueva cuenta `PRO` o `ULTRA` (OAuth en navegador) |
| `agyc renew <alias>` | Re-vincula una cuenta cuando Google solicita re-autenticación |
| `agyc export [alias] [-o <archivo>]` | Exporta una o todas las cuentas a un bundle portable `agyc-bundle-v1` (`0600`) |
| `agyc import <archivo> [--alias ...] [--overwrite]` | Importa cuentas entre equipos (Windows ↔ Linux), prepara `HOME`s aislados y lanzadores |
| `agyc update` / `agy update` | Actualiza `lib/`, binarios, barras (`statusline`/`titleline`/`topbar`) y motor `agy` |
| `agyc switch <alias>` | Cambia la cuenta activa global sin lanzar Antigravity |
| `agyc default <alias>` | Fija la cuenta predeterminada para `agy` |
| `agyc quota [alias]` | Desglose detallado por modelo y hora exacta de reinicio |
| `agyc rm <alias>` | Elimina una cuenta registrada y limpia su perfil |
| `agyc wipe` | Purga todas las credenciales registradas (con confirmación) |

---

## Arquitectura y Tests

### Aislamiento de perfiles `HOME` y librería núcleo `lib/agyc_core.py` + `lib/platform/`

```text
~/.gemini/antigravity-cli/          (Windows: %USERPROFILE%\.gemini\antigravity-cli\)
├── lib/
│   ├── __init__.py
│   ├── agyc_core.py                ← 🧩 motor compartido (scoring Burn-First, locks/notas, paneles activos, doctor)
│   └── platform/                   ← 🌐 abstracción OS POSIX + Win32 (<2ms bajo python -S)
│       ├── __init__.py             ←    selector IS_WINDOWS + helpers de rutas/alias
│       ├── linux.py                ←    symlinks, fcntl.flock, AF_UNIX, /proc ELF, select
│       └── win32.py                ←    NTFS Junctions (mklink /J), icacls, msvcrt.locking,
│                                        CreateToolhelp32Snapshot, PeekNamedPipe, Herdr TCP, Toast
└── bin/                            ← 🚀 Linux: agyc, agy, statusline, titleline, topbar, agy01..15
                                       Windows (%LOCALAPPDATA%\agyc\bin\): agyc.cmd, agy.cmd,
                                       agyc-statusline.cmd, agyc-titleline.cmd, agyc-topbar.cmd, agy01..15.cmd

~/.cache/agyc/                      (Windows: %LOCALAPPDATA%\agyc\cache\)
├── locks/                          ← 🔒 locks de sesión OAuth y deduplicación de alertas
└── run/                            ← 📋 registro <pid>.json usado en Windows por scan_agy_processes()

~/.agyc_homes/                      (Windows: %USERPROFILE%\.agyc_homes\)
├── agy01/
│   ├── .npm                        ← 🔗 symlink deduplicado → ~/.npm (ahorro de caché MCP/npx)
│   └── .gemini/antigravity-cli/
│       ├── antigravity-oauth-token ← 🔒 token exclusivo 0600 (dev1@gmail.com - ULTRA)
│       ├── lib/                    ← 🔗 symlink compartido → ~/.gemini/antigravity-cli/lib
│       ├── settings.json           ← 🔒 configuración por perfil (statusLine + title)
│       ├── accounts/               ← 🔗 symlink compartido
│       ├── conversations/          ← 🔗 symlink compartido
│       └── brain/                  ← 🔗 symlink compartido
├── agy02/...                       ← 🔒 token exclusivo 0600 (dev2@gmail.com - PRO)
└── agy03/...                       ← 🔒 token exclusivo 0600 (dev3@gmail.com - PRO)
```

### Algoritmo *"Reserva ULTRA + Burn-First"* (`agyc auto`)

```text
1. Filtro de elegibilidad y anti-colisión:
   descarta is_revoked == True, locked == True (🔒 RESERVADA), cuentas EN USO en otros paneles (▶ en pX) y cuota agotada.

2. Regla Reserva ULTRA:
   - Modelo Carbon / modo 'carbon'|'ultra': exige exclusivamente cuentas ULTRA.
   - Modelos estándar (Argon, 3.8 Flash, Claude, GPT): prioriza cuentas PRO saludables;
     solo usa ULTRA si se indica --allow-ultra o si no quedan cuentas PRO disponibles.

3. Regla Burn-First (Quemar ventana activa primero):
   prioriza cuentas con ventana 5H ya iniciada y saldo saludable (>15% y <100%) antes de abrir
   una cuenta íntegra al 100% Disponible, maximizando la regeneración paralela de ciclos de 5h.
```

### Ejecutar la suite de tests unitarios (38 pruebas)

En **Ubuntu Linux**:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests
```

En **Windows 10/11 (PowerShell / CMD)**:

```powershell
python -B -m unittest discover -s tests
# o sin -B:
python -m unittest discover -s tests
```

---

## Historia de Versiones

| Versión | Fecha | Cambios principales |
|---|---|---|
| **v1.0** | Oct 13, 2026 | MVP: `switch`, lanzadores directos `agy01..15`, tabla inicial de cuotas |
| **v1.1** | Oct 14, 2026 | `agyc auto`, rotación ponderada inteligente, bypass de keyring vía `SSH_TTY` |
| **v1.2** | Oct 15, 2026 | `agyc renew`, `agyc wipe`, corrección de rutas de entorno en Snap |
| **v1.3** | Oct 15, 2026 | Perfiles `HOME` aislados (`prepare_isolated_home()`), ejecución paralela sin colisiones |
| **v1.4** | Oct 16, 2026 | Soporte preliminar para Gemini 4 Argon, wrapper `bin/agy` y actualizador `agyc update` |
| **v1.5** | Nov 2026 | Esquema oficial **Antigravity 1.5.10** (`PRO` / `ULTRA`, 2 grupos unificados `Gemini` y `Claude & GPT`), Top/Bottom Bar en vivo con `% Ctx` real y orden unificado `5H → Ctx → Sem` |
| **v1.6** | Nov 2026 | Detección en vivo de paneles activos (`EN USO` / `▶ en pX`) y anti-colisión, notas y reservas (`agyc note`, `agyc lock`/`unlock` en 131 cols), motor **Reserva ULTRA + Burn-First** (`agyc auto [--allow-ultra]`), **alerta `≤15%` + toast único en Herdr/Win32**, `agyc doctor [--fix]`, librería `lib/agyc_core.py`, soporte nativo **Windows 10/11 + Ubuntu Linux** (`lib/platform/`, `install.ps1`, `install.cmd`, `bin/agy.cmd`), migración portable (`agyc export` / `agyc import`) y **38 pruebas** en `tests/test_agyc.py` |

---

## Documentación Adicional y Licencia

- Manual completo de operación: [docs/MANUAL.md](docs/MANUAL.md)
- Arquitectura técnica, seguridad, APIs y soporte multiplataforma (`lib/platform/`): [docs/ARQUITECTURA_Y_FUNCIONALIDAD.md](docs/ARQUITECTURA_Y_FUNCIONALIDAD.md)
- Skill para agentes: [skills/agyc/SKILL.md](skills/agyc/SKILL.md)
- Licencia: MIT — ver [LICENSE](LICENSE)
