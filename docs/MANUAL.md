# Manual Completo de `agyc`
## Google Antigravity Multi-Account Switcher

> **Versión:** v1.6 | **Fecha:** Noviembre 2026
> **Motor soportado:** Google Antigravity CLI `1.5.10+` (binario nativo o Snap `antigravity-cli`)
> **Suscripciones soportadas:** Google AI Pro (`PRO`) y Google AI Ultra (`ULTRA`)
> **Plataforma:** Ubuntu Linux x86_64

---

## Índice

1. [¿Para qué sirve agyc?](#1-para-qué-sirve-agyc)
2. [Esquema Oficial de Cuotas en Google Antigravity 1.5.10](#2-esquema-oficial-de-cuotas-en-google-antigravity-1510)
3. [Instalación (`v1.6`)](#3-instalación-v16)
4. [Primeros pasos, Panel de 131 Columnas, Notas y Reservas](#4-primeros-pasos-panel-de-131-columnas-notas-y-reservas)
5. [Comandos de Referencia](#5-comandos-de-referencia)
6. [Visualización en Vivo y Alerta Inteligente al `≤15%` en Herdr](#6-visualización-en-vivo-y-alerta-inteligente-al-15-en-herdr)
7. [Aislamiento de Perfiles HOME y Deduplicación `.npm`](#7-aislamiento-de-perfiles-home-y-deduplicación-npm)
8. [Uso en Múltiples Paneles y Detección `EN USO` (Anti-Colisión)](#8-uso-en-múltiples-paneles-y-detección-en-uso-anti-colisión)
9. [Motor *"Reserva ULTRA + Burn-First"* (`agyc auto [--allow-ultra]`)](#9-motor-reserva-ultra--burn-first-agyc-auto---allow-ultra)
10. [Diagnóstico y Auto-Reparación (`agyc doctor [--fix]`)](#10-diagnóstico-y-auto-reparación-agyc-doctor---fix)
11. [Librería Núcleo `lib/agyc_core.py` y Suite de Tests](#11-librería-núcleo-libagyc_corepy-y-suite-de-tests)
12. [Gestión de Tokens, Elegibilidad y Keyring](#12-gestión-de-tokens-elegibilidad-y-keyring)
13. [Skill para el Agente de Antigravity](#13-skill-para-el-agente-de-antigravity)
14. [`agyc wipe` y `agyc update`](#14-agyc-wipe-y-agyc-update)
15. [Historia de Versiones y Decisiones de Diseño](#15-historia-de-versiones-y-decisiones-de-diseño)

---

## 1. ¿Para qué sirve agyc?

Google Antigravity CLI (`agy`) opera por defecto con una única sesión OAuth activa. Al trabajar a tiempo completo con modelos de razonamiento profundo (`Gemini 4 Carbon`, `Gemini 4 Argon`, `Claude Opus 5.5`, `Claude Sonnet 5.5`) o ejecutar enjambres de subagentes en paralelo, las ventanas de cuota de una sola cuenta se consumen rápidamente.

`agyc v1.6` transforma Antigravity en una estación de trabajo **multi-cuenta inteligente y libre de colisiones**:

- Gestiona hasta **15 cuentas correlativas** (`agy01`..`agy15`), combinando cuentas **Google AI Pro (`PRO`)** y **Google AI Ultra (`ULTRA`)**.
- Detecta en vivo qué cuentas están **`EN USO`** en paneles activos (`▶ en p2`) y cuáles están **`🔒 RESERVADA`** (`agyc lock`), evitando choques al rotar.
- Permite asignar **notas y reservas con motivo** por cuenta visibles en la segunda línea de cada fila de `agyc list` manteniendo **131 columnas** exactas.
- Implementa el motor ***"Reserva ULTRA + Burn-First"*** en `agyc auto [--allow-ultra]` y dispara una **alerta visual + Toast único por ciclo en Herdr** cuando cualquier ventana cae a **`≤15%`**.
- Incluye diagnóstico integral y auto-reparación con **`agyc doctor [--fix]`**, núcleo modular en **`lib/agyc_core.py`** y suite automatizada de pruebas unitarias.

---

## 2. Esquema Oficial de Cuotas en Google Antigravity 1.5.10

### Niveles de suscripción (`PRO` vs `ULTRA`)

| Código | Suscripción | Capacidades en Antigravity 1.5.10 |
|---|---|---|
| **`PRO`** | **Google AI Pro** | Acceso a modelos `Gemini 4 Argon/Hydrogen`, `Gemini 3.8 Flash` y toda la familia `Claude & GPT` con techos estándar Pro. |
| **`ULTRA`** | **Google AI Ultra** | Techos de cuota extendidos + **acceso exclusivo a `Gemini 4 Carbon`** (y `Orchestrator` ejecutando Carbon). |

### Los 2 Grupos Unificados de Cuotas

Todas las cuotas de modelos se consolidan en **2 grupos unificados** por cuenta sobre dos ventanas móviles compartidas:
- **Ventana de 5 Horas (`5H`):** Ventana deslizante desde el primer consumo activo (se restablece 5h después; **no** es un corte diario fijo).
- **Ventana Semanal (`Sem`):** Reserva móvil acumulada de 7 días (`168h`).

1. **Grupo `GEMINI` (Gemini Models):** `Gemini 4 Carbon` *(exclusivo `ULTRA`)*, `Gemini 4 Argon`, `Gemini 4 Hydrogen`, `Orchestrator (Carbon/Argon)`, `Gemini 3.8 Flash`.
2. **Grupo `CLAUDE & GPT` (Claude & GPT Models):** `Claude Sonnet 4.6 / 5.5`, `Claude Opus 4.6 / 5.5`, `GPT-OSS 120B`.

- **`100% Disponible`:** La cuenta conserva el 100% íntegro sin ciclo de reinicio abierto.
- **`82% (4h 25m)` / `91% (6d 23h)`:** Muestra el porcentaje restante disponible y el tiempo exacto hasta volver al 100%.

---

## 3. Instalación (`v1.6`)

### Instalación automática desde el repositorio

```bash
git clone https://github.com/russbellc/agyc-antigravity-cli-switcher.git
cd agyc-antigravity-cli-switcher
chmod +x install.sh
./install.sh
source ~/.bashrc
```

### Qué realiza `install.sh` en `v1.6`

1. **Endurecimiento de permisos (`0700` / `0600`) y deduplicación `.npm`:** Asegura permisos privados en `~/.agyc_homes`, `~/.gemini/antigravity-cli/accounts` y `~/.cache/agyc`, y enlaza `~/.agyc_homes/<alias>/.npm -> ~/.npm` para evitar duplicar cachés de servidores MCP/`npx`.
2. **Librería núcleo `lib/agyc_core.py`:** Copia `lib/__init__.py` y `lib/agyc_core.py` hacia `~/.gemini/antigravity-cli/lib/` (`0755` / `0644`) y enlaza `lib/` en perfiles aislados.
3. **Binarios, wrapper `agy` y barras en vivo:** Instala `agyc`, preserva `agy-real` + wrapper `bin/agy`, instala `agyc-statusline`, crea el symlink `agyc-titleline -> agyc-statusline` e instala `agyc-topbar` en `~/.gemini/antigravity-cli/bin/` y `~/.local/bin/`.
4. **Hooks TUI, lanzadores `agy01..agy15` y verificación unitaria:** Activa `"statusLine"` y `"title"` en `settings.json` (`0600`), instala `skills/agyc/SKILL.md`, valida sintaxis Python y ejecuta `python3 -m unittest discover -s tests` si está presente.

---

## 4. Primeros pasos, Panel de 131 Columnas, Notas y Reservas

### Registrar cuentas y anotar/reservar alias

```bash
agyc add                                    # primera cuenta → agy01
agyc add                                    # segunda cuenta → agy02
agyc add                                    # tercera cuenta → agy03

agyc note agy01 "Solo Carbon crítico"       # asigna nota informativa a agy01
agyc note agy01 --clear                     # elimina la nota de agy01

agyc lock agy03 "Intocable demo"            # bloquea agy03 con motivo (excluida de agyc auto)
agyc unlock agy03                           # desbloquea agy03
```

### Consultar el panel unificado (`agyc` / `agyc list`)

```text
PANEL DE CUENTAS DE GOOGLE AI PRO & ULTRA (ANTIGRAVITY 1.5.10 / AGYC v1.6)

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

Lectura de la segunda línea de cada fila (manteniendo exactamente **131 columnas** de ancho total):
- Bajo `CUENTA / EMAIL`: muestra la **nota** configurada con `agyc note` o el **motivo de bloqueo** de `agyc lock`.
- En `ESTADO`: muestra `EN USO` + `▶ en pX` cuando la cuenta tiene sesiones vivas de `agy` en paneles de Herdr o terminales locales, y `🔒 RESERVADA` cuando está protegida con `agyc lock`.

---

## 5. Comandos de Referencia

### Lanzadores directos
```bash
agy01 .. agy15             # Entra directo a esa cuenta con perfil HOME aislado y --dangerously-skip-permissions
agy                        # Entra con la cuenta activa/default usando el wrapper preservado
```

### Consulta, notas y reservas
```bash
agyc / agyc list           # Panel de 6 columnas (131 cols) con paneles activos, notas y reservas
agyc list -r               # Refresca cuotas y planes en vivo desde Google (--refresh)
agyc list --json           # Salida JSON estructurada (incluye in_use, panes, locked, lock_reason, note)
agyc quota [alias]         # Desglose detallado de modelos y timestamps exactos de reinicio
agyc note <alias> "<txt>"  # Guarda una nota descriptiva en la cuenta
agyc note <alias> --clear  # Borra la nota de la cuenta
agyc lock <alias> "[mot]"  # Marca la cuenta como 🔒 RESERVADA (excluida de agyc auto y sugerencias)
agyc unlock <alias>        # Retira la reserva de la cuenta
```

### Selección, rotación inteligente y diagnóstico
```bash
agyc switch <alias>        # Cambia la cuenta activa global sin abrir la TUI
agyc default <alias>       # Define la cuenta predeterminada para inicios con 'agy'
agyc auto                  # Rota con motor Reserva ULTRA + Burn-First y anti-colisión de paneles
agyc auto --allow-ultra    # Permite usar cuentas ULTRA también cuando el modelo activo no es Carbon
agyc auto gemini           # Fuerza evaluación sobre el grupo Gemini (PRO primero salvo --allow-ultra)
agyc auto claude           # Fuerza evaluación sobre el grupo Claude & GPT (PRO primero salvo --allow-ultra)
agyc auto carbon / ultra   # Filtra EXCLUSIVAMENTE cuentas ULTRA libres y no bloqueadas
agyc doctor                # Audita permisos, symlinks, caché .npm y configuración de hooks TUI/Herdr
agyc doctor --fix          # Repara automáticamente todos los hallazgos detectados por doctor
```

### Autenticación y mantenimiento
```bash
agyc add [alias]           # Registra nueva cuenta (PRO o ULTRA) vía OAuth en navegador
agyc renew <alias>         # Re-vincula OAuth cuando Google pide re-autenticación (alias: reauth)
agyc rm <alias>            # Elimina una cuenta y limpia su perfil aislado
agyc wipe [--force]        # Vacía TODAS las credenciales registradas
agyc update / agy update   # Sincroniza repo, lib/, binarios, barras y motor oficial de Antigravity
```

---

## 6. Visualización en Vivo y Alerta Inteligente al `≤15%` en Herdr

`agyc v1.6` mantiene el orden unificado **`5H → Ctx → Sem`** en las cuatro superficies en vivo (`agyc-statusline`, `agyc-titleline`, `pane.report_metadata` y `agyc-topbar`) y añade detección proactiva de agotamiento inminente.

### 6.1 Pie de `agy` (`agyc-statusline`) + Alerta Visual `≤15%`

Cuando la cuota efectiva del modelo activo cae a **`≤15%`** (`min(5H, Sem) <= 15%`, excluyendo estados sin inicializar):
1. **Badge ANSI inmediato:** Añade en la barra inferior `⚠ ≤15%` en naranja brillante (o `⚠ AGOTADA` en rojo brillante si llega a `0%`).
2. **Marca en borde de panel Herdr:** Antepone `⚠` en `display_agent` de `pane.report_metadata` (con bypass inmediato del throttle de 8s al cambiar de estado) para alertar visualmente en el borde superior del panel dividido.

```text
# Barra inferior ANSI con cuota baja:
⚡ agy02·PRO │ ⚠ ≤15% │ 🌿 main │ 🤖 Claude Sonnet 5.5 (high) │ 5H: [█░░░░░░░] 12% (⏳ 1h 40m) │ Ctx: [███░░░░░] 36% (90k/250k) │ Sem: [████████] 84% (5d 12h)

# Borde superior del panel en Herdr:
⚠ ⚡ agy02 [PRO] · Claude Sonnet 5.5 · 5H:12% Ctx:36% Sem:84%
```

### 6.2 Notificación Toast Única por Ciclo en Herdr (`maybe_notify_low_quota`)

Al cruzar `≤15%` dentro de Herdr (`HERDR_ENV=1` o socket `~/.config/herdr/herdr.sock` + binario `~/.local/bin/herdr`):
- **Cero spam (deduplicación estricta):** Registra `{"reset_key": "<reset_5h|reset_sem|active>", "notified_at": <ts>}` con permisos `0600` y `flock` atómico en `~/.cache/agyc/low_quota_alert_<alias>_<familia>.json`. Durante todo ese ciclo de reinicio (hasta 5 horas), **no vuelve a emitir otro toast**.
- **Sugerencia inteligente en `<3ms`:** Escanea localmente `accounts/*.json`, `quota_cache_*.json` y `pane.list` del socket Herdr:
  - Descarta la cuenta actual, cuentas con `is_revoked == True`, cuentas con `locked == True` (`🔒 RESERVADA`) y cuentas ocupadas en otros paneles de Herdr.
  - Si el modelo contiene `"carbon"`, exige `plan_type == "ULTRA"`; en caso contrario, prefiere cuentas **`PRO`** saludables (*Reserva ULTRA*).
- **Ejecución desacoplada (`<1ms`):** Lanza `herdr notification show --position top-right --sound none --body ...` mediante `subprocess.Popen(..., start_new_session=True)` sin bloquear jamás el renderizado de la TUI:
  - Con reemplazo libre encontrado:
    - Título: `⚠ Cuota baja en agy02 (12%)`
    - Cuerpo: `Sugerida libre: agy04 [PRO] (100% 5H) · Ejecuta: agyc auto`
  - Sin reemplazo libre disponible:
    - Cuerpo: `Ventana Claude al 12% · Revisa con: agyc list`

### 6.3 Barra Superior OSC (`agyc-titleline`) y Widget Global (`agyc-topbar`)

- **`agyc-titleline`** (`"title"` en `settings.json`): emite texto limpio OSC para pestañas/ventanas (`⚡ agy01 [ULTRA] · Gemini 4 Carbon (high) · 5H: 82% (4h 25m) · Ctx: 36% · Sem: 91% (6d 23h)`).
- **`agyc-topbar`** (`[[ui.tab_bar_right]]` en `~/.config/herdr/config.toml`): muestra en `<20ms` la cuenta activa del panel/pestaña enfocada en Herdr con `% Ctx` intercalado en `5H → Ctx → Sem`.

---

## 7. Aislamiento de Perfiles HOME y Deduplicación `.npm`

Cada lanzador `agy01`..`agy15` inyecta `HOME=~/.agyc_homes/<alias>` antes de `os.execv()` hacia `agy-real`:

```text
~/.agyc_homes/<alias>/
├── .npm                            ← 🔗 Symlink → ~/.npm (evita gigabytes duplicados en npx/MCP)
└── .gemini/antigravity-cli/
    ├── antigravity-oauth-token     ← 🔒 Copia exclusiva (0600) del alias
    ├── bin/                        ← 🔗 Symlink → ~/.gemini/antigravity-cli/bin
    ├── lib/                        ← 🔗 Symlink → ~/.gemini/antigravity-cli/lib
    ├── settings.json               ← 🔗 Symlink → ~/.gemini/antigravity-cli/settings.json
    ├── accounts/                   ← 🔗 Symlink → ~/.gemini/antigravity-cli/accounts
    ├── conversations/              ← 🔗 Symlink → historial compartido para /resume entre cuentas
    └── brain/                      ← 🔗 Symlink → artefactos y contexto compartido
```

---

## 8. Uso en Múltiples Paneles y Detección `EN USO` (Anti-Colisión)

Cuando trabajas con varios paneles abiertos en Herdr, tmux o terminales paralelas:
1. `agyc` inspecciona los procesos `agy-real` en ejecución (`/proc`) y los paneles reportados por el socket de Herdr (`pane.list`).
2. `agyc list` marca automáticamente esas cuentas como **`EN USO`** e indica en qué panel corren (`▶ en p1`, `▶ en p2`).
3. Cuando ejecutas `agyc auto` en un panel cuya cuota se agotó, el motor **descarta las cuentas `EN USO` en otros paneles** y las cuentas **`🔒 RESERVADA`**, asignándote siempre una cuenta libre para evitar desgastar la misma ventana `5H` desde dos sesiones pesadas simultáneas.

---

## 9. Motor *"Reserva ULTRA + Burn-First"* (`agyc auto [--allow-ultra]`)

El selector inteligente de `v1.6` aplica tres reglas jerárquicas:

1. **Anti-colisión y bloqueo:** Excluye cuentas con `is_revoked == True`, `locked == True` (`agyc lock <alias>`) y cuentas `EN USO` en otros paneles activos.
2. **Reserva ULTRA:**
   - En modo `carbon` / `ultra` (o cuando el modelo activo en `settings.json` es `Gemini 4 Carbon`), exige **exclusivamente cuentas `ULTRA`**.
   - En modos `gemini` (Argon, Hydrogen, 3.8 Flash) y `claude` (Sonnet, Opus, GPT-OSS), **protege las cuentas `ULTRA`** seleccionando primero entre cuentas **`PRO`** saludables. Solo recurre a una cuenta `ULTRA` si pasas `--allow-ultra` o si ninguna cuenta `PRO` libre tiene cuota disponible.
3. **Burn-First (Quemar primero ventanas móviles abiertas):**
   - Entre candidatas saludables del mismo nivel de plan (`>15%`), prioriza una cuenta cuya ventana móvil `5H` **ya esté en curso** (`15% < 5H < 100%`) antes de abrir una cuenta intacta al `100% Disponible`.
   - Así evitas fragmentar media docena de cuentas al 85% y concentras el consumo hasta agotar ordenadamente la ventana cuyo reloj de 5 horas ya se está regenerando.

---

## 10. Diagnóstico y Auto-Reparación (`agyc doctor [--fix]`)

El comando `agyc doctor` verifica de extremo a extremo la salud de la instalación:

- **Permisos de seguridad:** Directorios sensibles (`~/.agyc_homes`, `accounts/`, `~/.cache/agyc`) en `0700` y credenciales JSON/tokens en `0600`.
- **Integridad de binarios y librería:** Presencia de `agy-real`, wrapper `bin/agy`, `lib/agyc_core.py`, `agyc-statusline`, symlink `agyc-titleline` y `agyc-topbar`.
- **Perfiles aislados y `.npm`:** Symlinks válidos en `~/.agyc_homes/*` y deduplicación de carpetas `.npm` hacia `~/.npm`.
- **Hooks de telemetría:** Configuración activa de `"statusLine"` y `"title"` en `settings.json` e integración con Herdr (`agyc-topbar`).

Al ejecutar `agyc doctor --fix`, repara permisos, recrea symlinks faltantes, deduplica `.npm` y restaura los hooks en `settings.json` de forma idempotente.

---

## 11. Librería Núcleo `lib/agyc_core.py` y Suite de Tests

En `v1.6`, la lógica de dominio reutilizable reside en `lib/agyc_core.py` (instalada en `~/.gemini/antigravity-cli/lib/agyc_core.py`):
- Gestión atómica de metadatos por cuenta (`note`, `locked`, `lock_reason`).
- Detección en vivo de procesos `agy-real` y paneles de Herdr (`EN USO` / `▶ en pX`).
- Motor de ranking *Reserva ULTRA + Burn-First + Anti-Colisión*.
- Auditoría y reparación de `agyc doctor [--fix]`.

Para ejecutar la suite completa de pruebas unitarias sin generar bytecode residual:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests
```

---

## 12. Gestión de Tokens, Elegibilidad y Keyring

- **Renovación OAuth (`invalid_grant` o `Eligibility check failed`):** Ejecuta `agyc renew <alias>` para re-autenticar en navegador.
- **Bypass de GNOME Keyring:** `agyc` y `bin/agy` inyectan `SSH_TTY="${SSH_TTY:-/dev/pts/0}"` solo al invocar `agy-real` (sin contaminar `~/.bashrc`), asegurando lectura directa desde `antigravity-oauth-token`.

---

## 13. Skill para el Agente de Antigravity

`skills/agyc/SKILL.md` capacita al agente de IA para operar `agyc v1.6`:
- Consultar `agyc list` / `agyc list --json` respetando cuentas `EN USO` y `🔒 RESERVADA`.
- Administrar `agyc note`, `agyc lock`/`unlock`, `agyc doctor [--fix]` y `agyc auto [--allow-ultra]`.
- Aplicar la política *Reserva ULTRA + Burn-First* y atender las alertas `≤15%` de Herdr sin exponer tokens OAuth.

---

## 14. `agyc wipe` y `agyc update`

- **`agyc wipe [--force]`:** Elimina credenciales `accounts/*.json` y tokens OAuth conservando `settings.json`, `conversations/` y `brain/`.
- **`agyc update` (o `agy update`):** Sincroniza el repositorio, actualiza `lib/agyc_core.py`, binarios, wrappers, barras (`statusline`, `titleline`, `topbar`), lanzadores `agy01..15` y verifica actualizaciones oficiales de `agy-real`.

---

## 15. Historia de Versiones y Decisiones de Diseño

- **v1.0 (Oct 13, 2026):** MVP con `switch`, lanzadores `agy01..15` y `os.execv()`.
- **v1.1 (Oct 14, 2026):** `agyc auto` inicial y bypass de keyring vía `SSH_TTY`.
- **v1.2 (Oct 15, 2026):** `agyc renew` y `agyc wipe`.
- **v1.3 (Oct 15, 2026):** Aislamiento real de perfiles `HOME` en `~/.agyc_homes/<alias>`.
- **v1.4 (Oct 16, 2026):** Wrapper `bin/agy` y actualizador integrado `agyc update`.
- **v1.5 (Nov 2026):** Esquema oficial Antigravity `1.5.10` (`PRO`/`ULTRA`, 2 grupos unificados `Gemini` y `Claude & GPT`), cálculo exacto de `% Ctx` post-compactación y orden unificado `5H → Ctx → Sem` en `agyc-statusline`, `agyc-titleline`, bordes Herdr y `agyc-topbar`.
- **v1.6 (Nov 2026):**
  1. Detección en vivo de paneles activos (`EN USO` / `▶ en pX`) y anti-colisión en `agyc auto`.
  2. Notas y reservas por cuenta (`agyc note`, `agyc lock`/`unlock`) en la segunda línea de `agyc list` manteniendo **131 columnas**.
  3. Motor ***Reserva ULTRA + Burn-First*** en `agyc auto [--allow-ultra]` + **alerta visual y Toast único al `≤15%` en Herdr**.
  4. Diagnóstico y auto-reparación **`agyc doctor [--fix]`** (permisos `0700`/`0600`, symlinks, deduplicación `.npm` y hooks).
  5. Librería núcleo **`lib/agyc_core.py`** y suite de pruebas **`python3 -m unittest discover -s tests`**.
