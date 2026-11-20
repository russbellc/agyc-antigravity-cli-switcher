# Manual Completo de `agyc`
## Google Antigravity Multi-Account Switcher

> **Versión:** v1.6 | **Fecha:** Noviembre 2026
> **Motor soportado:** Google Antigravity CLI `1.5.10+` (binario nativo o Snap `antigravity-cli`)
> **Suscripciones soportadas:** Google AI Pro (`PRO`) y Google AI Ultra (`ULTRA`)
> **Plataforma:** Ubuntu Linux x86_64 y Windows 10/11 x86_64 (`lib/platform/`)
> **Referencia técnica:** [Arquitectura y Funcionalidad Técnica](ARQUITECTURA_Y_FUNCIONALIDAD.md)

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
11. [Librería Núcleo `lib/agyc_core.py`, Capa `lib/platform/` y Suite de Tests](#11-librería-núcleo-libagyc_corepy-capa-libplatform-y-suite-de-tests)
12. [Gestión de Tokens, Elegibilidad y Keyring](#12-gestión-de-tokens-elegibilidad-y-keyring)
13. [Skill para el Agente de Antigravity](#13-skill-para-el-agente-de-antigravity)
14. [Portabilidad entre Equipos (`agyc export` / `agyc import`), `agyc wipe` y `agyc update`](#14-portabilidad-entre-equipos-agyc-export--agyc-import-agyc-wipe-y-agyc-update)
15. [Historia de Versiones y Decisiones de Diseño](#15-historia-de-versiones-y-decisiones-de-diseño)

---

## 1. ¿Para qué sirve agyc?

Google Antigravity CLI (`agy`) opera por defecto con una única sesión OAuth activa. Al trabajar a tiempo completo con modelos de razonamiento profundo (`Gemini 4 Carbon`, `Gemini 4 Argon`, `Claude Opus 5.5`, `Claude Sonnet 5.5`) o ejecutar enjambres de subagentes en paralelo, las ventanas de cuota de una sola cuenta se consumen rápidamente.

`agyc v1.6` transforma Antigravity en una estación de trabajo **multi-cuenta inteligente y libre de colisiones**:

- Gestiona hasta **15 cuentas correlativas** (`agy01`..`agy15`), combinando cuentas **Google AI Pro (`PRO`)** y **Google AI Ultra (`ULTRA`)**.
- Detecta en vivo qué cuentas están **`EN USO`** en paneles activos (`▶ en p2`) y cuáles están **`🔒 RESERVADA`** (`agyc lock`), evitando choques al rotar.
- Permite asignar **notas y reservas con motivo** por cuenta visibles en la segunda línea de cada fila de `agyc list` manteniendo **131 columnas** exactas.
- Implementa el motor ***"Reserva ULTRA + Burn-First"*** en `agyc auto [--allow-ultra]` y dispara una **alerta visual + Toast único por ciclo en Herdr** cuando cualquier ventana cae a **`≤15%`**.
- Incluye diagnóstico integral y auto-reparación con **`agyc doctor [--fix]`**, migración portable entre equipos (**`agyc export` / `agyc import`**), núcleo modular en **`lib/agyc_core.py`**, capa multiplataforma **`lib/platform/`** (`linux.py` + `win32.py`) y suite automatizada de **38 pruebas unitarias** (`tests/test_agyc.py`).

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

### Ubuntu Linux (`install.sh`)

```bash
git clone https://github.com/russbellc/agyc-antigravity-cli-switcher.git
cd agyc-antigravity-cli-switcher
chmod +x install.sh
./install.sh
source ~/.bashrc
```

Qué realiza `install.sh` en `v1.6`:
1. **Endurecimiento de permisos (`0700` / `0600`) y deduplicación `.npm`:** Asegura permisos privados en `~/.agyc_homes`, `~/.gemini/antigravity-cli/accounts` y `~/.cache/agyc`, y enlaza `~/.agyc_homes/<alias>/.npm -> ~/.npm` para evitar duplicar cachés de servidores MCP/`npx`.
2. **Librería núcleo `lib/agyc_core.py` + `lib/platform/`:** Copia `lib/__init__.py`, `lib/agyc_core.py` y `lib/platform/{__init__.py,linux.py,win32.py}` hacia `~/.gemini/antigravity-cli/lib/` (`0755` / `0644`) y enlaza `lib/` en perfiles aislados.
3. **Binarios, wrapper `agy` y barras en vivo:** Instala `agyc`, preserva `agy-real` + wrapper `bin/agy`, instala `agyc-statusline`, crea el symlink `agyc-titleline -> agyc-statusline` e instala `agyc-topbar` en `~/.gemini/antigravity-cli/bin/` y `~/.local/bin/`.
4. **Hooks TUI, lanzadores `agy01..agy15` y verificación unitaria:** Activa `"statusLine"` y `"title"` en `settings.json` (`0600`), instala `skills/agyc/SKILL.md`, valida sintaxis Python y ejecuta `python3 -m unittest discover -s tests`.

### Windows 10/11 (`install.ps1` / `install.cmd`)

```powershell
git clone https://github.com/russbellc/agyc-antigravity-cli-switcher.git
cd agyc-antigravity-cli-switcher
.\install.ps1
# o desde CMD / doble clic (ejecuta powershell.exe -ExecutionPolicy Bypass -File install.ps1):
install.cmd
```

Qué realiza `install.ps1` en `v1.6` (admite `-SkipPath` y `-SkipTests`):
1. **Detección de Python 3.10+ y motor Antigravity:** Busca `python`, `py -3` o `python3` (`>= 3.10`) y localiza `agy-real.exe` o `%LOCALAPPDATA%\agy\bin\agy.exe`.
2. **Rutas Windows y seguridad NTFS:** Crea `%USERPROFILE%\.gemini\antigravity-cli`, `%LOCALAPPDATA%\agyc\{bin,lib,cache,cache\locks,cache\run}` y `%USERPROFILE%\.agyc_homes`. Endurece ACLs NTFS restringidas al SID del usuario actual (`harden_ntfs_acl()` vía `whoami /user` + `icacls`) y deduplica `.npm` mediante **NTFS Junctions** (`cmd /c mklink /J`, sin privilegios de Administrador).
3. **Librería `lib/` y wrappers `.cmd`:** Instala `lib/__init__.py`, `lib/agyc_core.py` y `lib/platform/*` en `%USERPROFILE%\.gemini\antigravity-cli\lib` y `%LOCALAPPDATA%\agyc\lib`, enlaza `lib/` en perfiles aislados vía NTFS Junction, e instala `agyc.cmd`, `agy.cmd` (`bin/agy.cmd`), `agi.cmd`, `agyc-statusline.cmd`, `agyc-titleline.cmd` (`AGYC_INVOKED_AS=agyc-titleline`), `agyc-topbar.cmd` y los lanzadores directos `agy01.cmd..agy15.cmd` / `agi01.cmd..agi15.cmd` en `%LOCALAPPDATA%\agyc\bin` y `%USERPROFILE%\.gemini\antigravity-cli\bin`.
4. **Hooks, Herdr, `User PATH` y verificación:** Configura `"statusLine": "agyc-statusline.cmd"` y `"title": "agyc-titleline.cmd"` en `settings.json`, autoconfigura `%APPDATA%\herdr\config.toml` (`show_agent_labels_on_pane_borders = true`, `[[ui.tab_bar_right]]` `agyc-topbar.cmd`, `[ui.toast]`) y ejecuta `herdr server reload-config`, antepone `%LOCALAPPDATA%\agyc\bin` al `User PATH` (para que `agy.cmd` preceda a `%LOCALAPPDATA%\agy\bin\agy.exe`), instala `skills/agyc/SKILL.md` si existe `.agents\skills`, ejecuta `py_compile` y corre `python -m unittest discover -s tests`.

#### Post-instalación y Troubleshooting rápido en Windows
- **El comando `agyc` no se reconoce tras instalar:** PowerShell/CMD no recarga automáticamente el `User PATH` en la sesión actual. Abre una **nueva terminal**, o recarga el `PATH` en la misma ventana de PowerShell:
  ```powershell
  $env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User")
  ```
- **Error de `ExecutionPolicy` al ejecutar `.\install.ps1`:** usa `.\install.cmd`, que invoca `powershell.exe -NoProfile -ExecutionPolicy Bypass -File install.ps1` sin requerir cambios globales de política.
- **No aparecen la barra superior derecha (`agyc-topbar`) o los bordes de panel en Herdr tras instalar:**
  1. Primero recarga la configuración en caliente sin cerrar paneles:
     ```powershell
     herdr server reload-config
     ```
  2. Si el cliente gráfico de Herdr aún no refresca la barra o los bordes, haz detach o cierra **solo la ventana de Herdr** y vuelve a abrir `herdr` (tus sesiones y agentes siguen vivos en el servidor en segundo plano).
- **Cuentas previas o reparación integral:** ejecuta `agyc doctor` para auditar `%LOCALAPPDATA%\agyc\bin`, ACLs NTFS y `%APPDATA%\herdr\config.toml`; usa `agyc doctor --fix` si necesitas crear perfiles aislados faltantes o reparar enlaces y configuración de Herdr.

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

### Autenticación, migración entre equipos y mantenimiento
```bash
agyc add [alias]                         # Registra nueva cuenta (PRO o ULTRA) vía OAuth en navegador
agyc renew <alias>                       # Re-vincula OAuth cuando Google pide re-autenticación (alias: reauth)
agyc export [alias] [-o <archivo>]       # Exporta una o todas las cuentas a un bundle agyc-bundle-v1 (0600)
agyc import <archivo> [--alias <nuevo>] [--overwrite]  # Importa cuentas (Windows ↔ Linux), crea HOMEs y lanzadores
agyc rm <alias>                          # Elimina una cuenta y limpia su perfil aislado
agyc wipe [--force]                      # Vacía TODAS las credenciales registradas
agyc update / agy update                 # Sincroniza repo, lib/, binarios, barras y motor oficial de Antigravity
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

### 6.2 Notificación Toast Única por Ciclo en Herdr / Win32 (`maybe_notify_low_quota`)

Al cruzar `≤15%` dentro de Herdr (`HERDR_ENV=1`, `HERDR_PANE_ID`, socket `~/.config/herdr/herdr.sock` en Linux o `%APPDATA%\herdr\herdr.sock` en Windows):
- **Cero spam (deduplicación estricta):** Registra `{"reset_key": "<reset_5h|reset_sem|active>", "notified_at": <ts>}` con permisos privados (`0600`) y lock atómico vía `acquire_file_lock()` (`fcntl.flock` en Linux / `msvcrt.locking` en Windows) en `~/.cache/agyc/low_quota_alert_<alias>_<familia>.json` (o `%LOCALAPPDATA%\agyc\cache\...` en Windows). Durante todo ese ciclo de reinicio (hasta 5 horas), **no vuelve a emitir otro toast**.
- **Sugerencia inteligente en `<3ms`:** Escanea localmente `accounts/*.json`, `quota_cache_*.json` y `pane.list` del IPC de Herdr (`AF_UNIX` en Linux; TCP `127.0.0.1:<port>` leyendo `<port>:<nonce>` en Windows):
  - Descarta la cuenta actual, cuentas con `is_revoked == True`, cuentas con `locked == True` (`🔒 RESERVADA`) y cuentas ocupadas en otros paneles de Herdr.
  - Si el modelo contiene `"carbon"`, exige `plan_type == "ULTRA"`; en caso contrario, prefiere cuentas **`PRO`** saludables (*Reserva ULTRA*).
- **Ejecución desacoplada (`<1ms`):** A través de `platform.send_low_quota_toast()` y `platform.spawn_detached()` (`start_new_session=True` en Linux; `CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS` en Windows):
  - Si existe `herdr` / `herdr.exe`, ejecuta `herdr notification show --position top-right --sound none --body ...` sin bloquear el renderizado de la TUI.
  - En Windows, si `herdr.exe` no está en `PATH`, `win32.py` usa un fallback nativo con `powershell.exe` + `System.Windows.Forms.NotifyIcon` (`ShowBalloonTip(5000)`) pasando título y cuerpo por variables de entorno (`AGYC_TOAST_TITLE`, `AGYC_TOAST_BODY`).
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

Cada lanzador (`agy01`..`agy15` en Linux, `agy01.cmd`..`agy15.cmd` en Windows) prepara el perfil aislado e inyecta `HOME=~/.agyc_homes/<alias>` (más `USERPROFILE=%USERPROFILE%\.agyc_homes\<alias>` y `AGYC_ACCOUNT=<alias>` en Windows) antes de lanzar `agy-real` (`os.execve` en Linux; `subprocess.Popen` con registro `<run_dir>\<pid>.json` en Windows):

```text
~/.agyc_homes/<alias>/                     (Windows: %USERPROFILE%\.agyc_homes\<alias>\)
├── .npm                            ← 🔗 Symlink / NTFS Junction → ~/.npm (%USERPROFILE%\.npm)
└── .gemini/antigravity-cli/
    ├── antigravity-oauth-token     ← 🔒 Copia exclusiva (0600 / NTFS ACL) del alias
    ├── bin/                        ← 🔗 Symlink / NTFS Junction → base\bin
    ├── lib/                        ← 🔗 Symlink / NTFS Junction → base\lib
    ├── settings.json               ← 🔒 Archivo propio por perfil (statusLine + title)
    ├── accounts/                   ← 🔗 Symlink / NTFS Junction → base\accounts
    ├── conversations/              ← 🔗 Symlink / NTFS Junction → historial compartido (/resume)
    └── brain/                      ← 🔗 Symlink / NTFS Junction → artefactos y contexto compartido
```

---

## 8. Uso en Múltiples Paneles y Detección `EN USO` (Anti-Colisión)

Cuando trabajas con varios paneles abiertos en Herdr, tmux o terminales paralelas:
1. `agyc` inspecciona los procesos `agy-real` en ejecución (`/proc` en Linux, o `CreateToolhelp32Snapshot` + `<run_dir>\<pid>.json` vía `lib/platform/win32.py` en Windows) y los paneles reportados por Herdr (`pane.list`).
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

## 11. Librería Núcleo `lib/agyc_core.py`, Capa `lib/platform/` y Suite de Tests

En `v1.6`, la lógica de dominio reutilizable reside en `lib/agyc_core.py` (instalada en `~/.gemini/antigravity-cli/lib/agyc_core.py`) apoyada por la capa de abstracción OS en `lib/platform/` (`__init__.py`, `linux.py`, `win32.py`):
- Gestión atómica de metadatos por cuenta (`note`, `locked`, `lock_reason`).
- Detección en vivo de procesos `agy-real` / `agy` y paneles de Herdr (`EN USO` / `▶ en pX`).
- Primitivas POSIX/Win32 equivalentes (enlaces de directorio/archivo, locks concurrentes, lectura no bloqueante de `stdin`, IPC Herdr y notificaciones Toast).
- Motor de ranking *Reserva ULTRA + Burn-First + Anti-Colisión*.
- Auditoría y reparación de `agyc doctor [--fix]`.

Para ejecutar la suite completa de **38 pruebas unitarias** (`tests/test_agyc.py`) sin generar bytecode residual:

```bash
# Ubuntu Linux
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests
```

```powershell
# Windows 10/11 (PowerShell / CMD)
python -B -m unittest discover -s tests
```

---

## 12. Gestión de Tokens, Elegibilidad y Keyring

- **Renovación OAuth (`invalid_grant` o `Eligibility check failed`):** Ejecuta `agyc renew <alias>` para re-autenticar en navegador.
- **Bypass de GNOME Keyring (Linux) y Windows Credential Manager (`wincred`):** `agyc`, `bin/agy` (Linux) y `bin/agy.cmd` (Windows) inyectan `SSH_TTY="${SSH_TTY:-/dev/pts/0}"` solo al invocar `agy-real` / `agy.exe` (sin contaminar el shell del usuario), evitando que Antigravity lea credenciales globales de GNOME Keyring o de Windows Credential Manager (`LegacyGeneric:target=gemini:antigravity`) y forzando lectura directa desde `antigravity-oauth-token` en cada perfil aislado.

---

## 13. Skill para el Agente de Antigravity

`skills/agyc/SKILL.md` capacita al agente de IA para operar `agyc v1.6`:
- Consultar `agyc list` / `agyc list --json` respetando cuentas `EN USO` y `🔒 RESERVADA`.
- Administrar `agyc note`, `agyc lock`/`unlock`, `agyc doctor [--fix]` y `agyc auto [--allow-ultra]`.
- Aplicar la política *Reserva ULTRA + Burn-First* y atender las alertas `≤15%` de Herdr sin exponer tokens OAuth.

---

## 14. Portabilidad entre Equipos (`agyc export` / `agyc import`), `agyc wipe` y `agyc update`

### Migración portable Windows ↔ Ubuntu Linux (`agyc export` / `agyc import`)

Permite llevar tus vinculaciones OAuth ya autenticadas de un equipo a otro (por ejemplo, de **Ubuntu Linux a Windows 10/11** o viceversa) sin volver a abrir el navegador en cada máquina:

1. **Exportar en el equipo origen:**
   - `agyc export`: exporta todas las cuentas válidas registradas en `accounts/` (excluyendo `config.json` y archivos prefijados con `_`) en `agyc-accounts-bundle.json`.
   - `agyc export agy01`: exporta solo `agy01` (por defecto en `agyc-agy01.json`, o en la ruta indicada con `-o <archivo>`).
   - El bundle se escribe atómicamente con formato `agyc-bundle-v1` y permisos privados (`0600`).
2. **Transferencia segura y limpieza:**
   - Como el archivo contiene tokens OAuth activos (`access_token` y `refresh_token`), transfiérelo únicamente por un canal cifrado (por ejemplo `scp agyc-accounts-bundle.json usuario@otro-equipo:~/`).
   - Elimina el archivo bundle tanto del origen como del destino inmediatamente después de completar la importación.
3. **Importar en el equipo destino:**
   - `agyc import <archivo>`: valida `format == "agyc-bundle-v1"`, guarda cada cuenta en `accounts/<alias>.json`, prepara su perfil aislado en `.agyc_homes/<alias>/`, sincroniza lanzadores (`agy01..15` / `.cmd`) y configura `active_account` / `default_account` si el equipo destino no tenía cuenta activa.
   - `--alias <nuevo_alias>`: renombra la cuenta al importar (solo válido cuando el bundle contiene exactamente 1 cuenta).
   - `--overwrite`: reemplaza cuentas existentes que coincidan por alias o email; sin `--overwrite`, omite los duplicados existentes.
4. **Advertencia sobre uso simultáneo en paralelo:** Si mantienes la misma cuenta operando en ambos equipos a la vez, la rotación/renovación de `refresh_token` ejecutada por Google en una máquina puede revocar el token de la otra (`invalid_grant`, recuperable con `agyc renew <alias>`).

### `agyc wipe` y `agyc update`

- **`agyc wipe [--force]`:** Elimina credenciales `accounts/*.json` y tokens OAuth conservando `settings.json`, `conversations/` y `brain/`.
- **`agyc update` (o `agy update`):** Sincroniza el repositorio (`git pull` o descarga HTTPS), actualiza `lib/` (incluyendo `lib/platform/`), binarios, wrappers (`bin/agy` en Linux; `bin/agy.cmd`, `agyc.cmd`, `agy01.cmd..15.cmd`, `agyc-statusline.cmd`, `agyc-titleline.cmd`, `agyc-topbar.cmd` en Windows) y descarga/actualiza el binario oficial de Google Antigravity CLI:
  - En **Linux**: consulta `manifests/linux_amd64.json`, extrae `.tar.gz`, valida `_verify_sha512()` y reemplaza `agy-real` vía `os.replace()`.
  - En **Windows**: consulta `manifests/windows_amd64.json`, reutiliza `%LOCALAPPDATA%\agy\bin\agy.exe` si coincide el SHA-512 o descarga/extrae el paquete `.zip` oficial, verifica `_verify_sha512()` y reemplaza `agy-real.exe` (renombrando a `.old` si está en uso por otro panel).

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
