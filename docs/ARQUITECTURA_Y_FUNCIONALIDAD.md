# Arquitectura y Funcionalidad Técnica de `agyc` (`v1.6`)

> **Repositorio:** `agyc-antigravity-cli-switcher`
> **Motor soportado:** Google Antigravity CLI `1.5.10+` (`PRO` / `ULTRA`)
> **Plataforma actual:** Ubuntu Linux `x86_64` y Windows 10/11 `x86_64` (`Python 3.10+` stdlib puro)

Este documento describe la arquitectura interna, el modelo de seguridad y aislamiento, el protocolo OAuth2 y de cuotas CloudCode PA, el motor de rotación inteligente, la telemetría en vivo en 4 superficies y la capa de abstracción multiplataforma `lib/platform/` (`__init__.py`, `linux.py` y `win32.py`). Todo lo aquí descrito corresponde directamente al código fuente del repositorio.

---

## 1. Visión General y Mapa de Componentes

`agyc` separa la lógica de dominio pura (`lib/agyc_core.py`), la capa de abstracción del sistema operativo (`lib/platform/`), el CLI administrativo y lanzador (`bin/agyc`), los wrappers de seguridad de `agy` (`bin/agy` en Linux y `bin/agy.cmd` en Windows), y los renderizadores de telemetría de baja latencia (`bin/agyc-statusline`, `agyc-titleline`, `bin/agyc-topbar`).

| Componente | Ubicación en repo | Ubicación instalada | Rol exacto |
|---|---|---|---|
| **Núcleo compartido** | `lib/agyc_core.py` (`lib/__init__.py`) | `~/.gemini/antigravity-cli/lib/` (Win: + `%LOCALAPPDATA%\agyc\lib\`) | Lógica pura en Python stdlib (`<2ms` bajo `python -S`, imports pesados diferidos): delegación OS vía `_plat()`, validación de alias, escritura atómica (`0600` + retry `PermissionError` en Windows), sanitización `--json`, normalización de ventanas, estimación O(1) de `% Ctx` desde EOF, escáner multiplataforma (`scan_active_herdr_panes`) y motor `compute_smart_auto_choice`. |
| **Capa OS multiplataforma** | `lib/platform/__init__.py`, `lib/platform/linux.py`, `lib/platform/win32.py` | `~/.gemini/antigravity-cli/lib/platform/` (Win: + `%LOCALAPPDATA%\agyc\lib\platform\`) | Abstracción POSIX + Win32 (`IS_WINDOWS = os.name == "nt"`): `resolve_real_home`, `get_base_dir`, `get_cache_dir`, `get_locks_dir`, `get_run_dir`, `ensure_private_dir`, `ensure_private_file`, `harden_ntfs_acl`, `create_dir_link`, `is_dir_link`, `read_dir_link`, `create_file_link`, `acquire_file_lock`, `default_herdr_socket_path`, `query_herdr_ipc` (Named Pipe Win32 + fallback TCP / `AF_UNIX`), `scan_agy_processes`, `find_ancestor_agy_pid`, `read_stdin_nonblocking`, `spawn_detached` y `send_low_quota_toast`. |
| **CLI y lanzador** | `bin/agyc` | Linux: `~/.gemini/antigravity-cli/bin/` + `~/.local/bin/` (`agyc`, `agy01..15`)<br>Win: `%LOCALAPPDATA%\agyc\bin\` + `%USERPROFILE%\.gemini\antigravity-cli\bin\` (`agyc.cmd`, `agy01.cmd..15.cmd`) | Interfaz de usuario (`list`, `add`, `renew`, `switch`, `default`, `auto`, `note`, `lock`, `unlock`, `quota`, `doctor`, `rm`, `wipe`, `update`, `export`, `import`) y lanzador directo por alias (`agy01..15` / `AGYC_INVOKED_AS`). Usa `platform.create_dir_link()` (NTFS Junctions / symlinks), `os.execve` en Linux, `subprocess.Popen` + `<run_dir>\<pid>.json` en Windows, `WINDOWS_AMD64`/`LINUX_AMD64`, y `cmd_update` con `manifests/windows_amd64.json` (`.zip` + `.old`) o `manifests/linux_amd64.json` (`.tar.gz`). |
| **Wrapper `agy`** | `bin/agy` (Linux) / `bin/agy.cmd` (Windows) | Linux: `~/.local/bin/agy`<br>Win: `%LOCALAPPDATA%\agyc\bin\agy.cmd` (`agi.cmd`) | Intercepta `agy update`/`agy upgrade` hacia `agyc update` (`agyc.cmd`), resuelve `REAL_HOME` inmune a `.agyc_homes`, localiza `agy-real` / `agy-real.exe` (o Snap en Linux / `%LOCALAPPDATA%\agy\bin\agy.exe` en Windows) sin recursión sobre el wrapper, inyecta `SSH_TTY=/dev/pts/0` para bypass de keyring (`GNOME Keyring` en Linux / Windows Credential Manager `wincred` en Windows) y añade `--dangerously-skip-permissions` por defecto. |
| **Barra inferior TUI** | `bin/agyc-statusline` | Linux: `agyc-statusline`<br>Win: `agyc-statusline.cmd` (`python -S`) | Script `python3 -S` / `python -S` invocado por Antigravity (`settings.json -> statusLine`). Lee `stdin` vía `platform.read_stdin_nonblocking()`, normaliza extensiones `.cmd`/`.exe`/`.bat`, envía `WINDOWS_AMD64` o `LINUX_AMD64` en `loadCodeAssist`, renderiza la barra ANSI `5H → Ctx → Sem`, persiste `pane_ctx_*.json`, reporta `pane.report_metadata` a Herdr, refresca cuotas en background (`--refresh-quota-bg`) y emite toast único al `≤15%`. |
| **Título OSC** | Symlink `agyc-titleline` (Linux) / `agyc-titleline.cmd` (`AGYC_INVOKED_AS=agyc-titleline`) | Linux: `agyc-titleline`<br>Win: `agyc-titleline.cmd` | Invocado por Antigravity (`settings.json -> title`). Detecta `basename(sys.argv[0]) == "agyc-titleline"` (tras quitar `.cmd`/`.exe`/`.bat`), `AGYC_INVOKED_AS=agyc-titleline` o `--title` y emite texto plano sin códigos ANSI para el título OSC de ventana/pestaña, sincronizando también `pane_ctx_*`, `pane.report_metadata` y alerta `≤15%`. |
| **Barra global Herdr** | `bin/agyc-topbar` | Linux: `agyc-topbar`<br>Win: `agyc-topbar.cmd` (`python -S`) | Widget `<20ms` integrado con `lib.platform` para `[[ui.tab_bar_right]]` de Herdr. Identifica la cuenta del panel enfocado (o pestaña activa) usando `scan_agy_processes()` + `query_herdr_ipc()` y renderiza cuotas `Gemini` y `Claude` intercalando `Ctx` en orden `5H → Ctx → Sem`. |
| **Instaladores** | `install.sh` (Linux) / `install.ps1` + `install.cmd` (Windows) | Raíz del repo | `install.sh` (Bash, 7 pasos) e `install.ps1` / `install.cmd` (PowerShell, 7 pasos, flags `-SkipPath` / `-SkipTests`): verifican Python 3.10+ y Antigravity CLI, crean directorios privados (`0700`/`0600` o `harden_ntfs_acl()`), deduplican `.npm` (symlinks / NTFS Junctions), instalan `lib/` y wrappers `.cmd`, configuran `settings.json`, `PATH` (anteponiendo `%LOCALAPPDATA%\agyc\bin` en Windows), `SKILL.md`, `py_compile` y `unittest`. |
| **Suite de tests** | `tests/test_agyc.py` | Raíz del repo (`tests/`) | **38 pruebas unitarias herméticas** (`test_01`..`test_38`) sobre `lib/agyc_core.py`, `lib/platform/` y `bin/agyc` (`export`/`import`, bypass keyring Win32, Named Pipe Herdr y `find_ancestor_agy_pid`) (sin red, usando `tempfile.TemporaryDirectory`, mocks de `pwd.getpwuid`, `/proc` sintético, `CreateToolhelp32Snapshot`, `msvcrt.locking`, `mklink /J`, `PeekNamedPipe`, socket `AF_UNIX` en Linux y Named Pipe / TCP `127.0.0.1:<port>` en Windows). |

---

## 2. Modelo de Almacenamiento, Aislamiento y Seguridad

### 2.1 Estructura de directorios y permisos (`0700` / `0600` / NTFS ACL)

`agyc` resuelve el directorio real del usuario mediante `resolve_real_home()` en `lib/platform/` (`AGYC_REAL_HOME`, `REAL_HOME`, `pwd.getpwuid(os.getuid()).pw_dir` en Linux o `USERPROFILE`/`os.path.expanduser("~")` en Windows, limpiando cualquier segmento `/.agyc_homes/*` o `\.agyc_homes\*`) para que los subprocesos lanzados dentro de un perfil aislado sigan encontrando el almacén maestro.

En **Linux**, el caché reside en `~/.cache/agyc/`; en **Windows**, `get_cache_dir()` resuelve `%LOCALAPPDATA%\agyc\cache` (respetando `AGYC_CACHE_DIR` y haciendo fallback a `<real_home>\.cache\agyc` en entornos aislados de test o sin `LOCALAPPDATA`) e incluye `run\<pid>.json` para seguimiento de procesos `agy` activos. Para permisos en Windows, `harden_ntfs_acl()` obtiene el SID actual con `whoami /user /fo csv /nh` y aplica `icacls <ruta> /inheritance:r /grant:r *<SID>:(OI)(CI)F` (directorios) o `*<SID>:F` (archivos).

```text
~/.gemini/antigravity-cli/                 # Base dir (Windows: %USERPROFILE%\.gemini\antigravity-cli\)
├── accounts/                              # 0700 — Almacén maestro de credenciales
│   ├── config.json                        # 0600 — {"active_account": "agy01", "default_account": "agy01"}
│   ├── agy01.json                         # 0600 — Perfil, email, plan_type, note, locked, token_data, quota
│   └── agy02.json                         # 0600 — ...
├── lib/                                   # 0755 — agyc_core.py, __init__.py, platform/{__init__.py,linux.py,win32.py}
├── bin/                                   # Binarios y symlinks (agy-real, agyc, agy, statusline, titleline, topbar, agy01..15)
├── settings.json                          # 0600 — Configuración base (statusLine + title)
└── conversations/, brain/, projects/, skills/, builtin/, mcp/

~/.cache/agyc/                             # Privado (Windows: %LOCALAPPDATA%\agyc\cache\)
├── locks/                                 # Locks flock / msvcrt.locking por alias (*.oauth.lock, low_quota_*.lock)
├── run/                                   # Windows: <pid>.json para cruce con CreateToolhelp32Snapshot
├── quota_cache_<alias>.json               # 0600 — Caché local de cuotas (TTL 20s)
├── quota_refreshing_<alias>.lock          # 0600 — Throttle de refresco en background (15s)
├── pane_ctx_<pane|conv>.json              # 0600 — Snapshot de % Ctx y modelo del panel/conversación
├── herdr_meta_<pane>.json                 # 0600 — Estado previo para throttle de 8s hacia Herdr
└── low_quota_alert_<alias>_<fam>.json     # 0600 — Deduplicación de toast ≤15% por ciclo (5h)

~/.agyc_homes/<alias>/                     # Privado (Windows: %USERPROFILE%\.agyc_homes\<alias>\)
```

Toda escritura JSON crítica usa `atomic_write_json()` (`os.open(..., os.O_CREAT | os.O_TRUNC, 0o600)` en archivo temporal + `os.chmod(0o600)` en POSIX + `os.replace()` con reintentos ante `PermissionError` en Windows), garantizando atomicidad ante lecturas concurrentes y ausencia de fugas de permisos.

### 2.2 Qué se comparte por enlace vs qué es exclusivo por perfil

Al lanzar una cuenta (`prepare_isolated_home(alias)`), `agyc` inyecta `HOME=~/.agyc_homes/<alias>` (más `USERPROFILE` y `AGYC_ACCOUNT` en Windows). En Linux usa symlinks (`os.symlink`); en Windows usa **NTFS Junctions** (`platform.create_dir_link()` → `cmd /c mklink /J`, sin privilegios de Administrador) para directorios y hardlinks/copia (`platform.create_file_link()`) para archivos compartidos. Dentro de ese perfil aislado:

| Recurso dentro de `~/.agyc_homes/<alias>/` | Tipo | Destino / Origen | Propósito |
|---|---|---|---|
| `.gemini/antigravity-cli/antigravity-oauth-token` | **Exclusivo (`0600` / ACL)** | Copia atómica desde `accounts/<alias>.json -> token_data` | Aísla la sesión OAuth de cada cuenta; jamás es symlink/junction para evitar colisiones entre paneles simultáneos. |
| `.gemini/antigravity-cli/settings.json` | **Exclusivo (`0600` / ACL)** | Archivo propio por perfil | Preserva el modelo elegido por cuenta (si la cuenta es `PRO`/`FREE` y heredó `carbon`, degrada automáticamente a `Gemini 4 Argon (High)`), manteniendo activos `statusLine` y `title` (`.cmd` en Windows). |
| `.gemini/antigravity-cli/accounts` | **Symlink / NTFS Junction** | `<base_dir>/accounts` | Permite que comandos `agyc` dentro del panel vean toda la flota. |
| `.gemini/antigravity-cli/conversations`, `brain`, `projects`, `annotations`, `history.jsonl`, `conversation_summaries.db*`, `jetbox_summaries_proto.pb`, `jetski_state.pbtxt`, `installation_id` | **Symlink / NTFS Junction / Hardlink** | `<base_dir>/<item>` | Unifica el historial de conversaciones (`/resume`), artefactos y memoria entre todas las cuentas. |
| `.gemini/antigravity-cli/skills`, `builtin`, `mcp`, `bin`, `lib` | **Symlink / NTFS Junction** | `<base_dir>/<item>` | Comparte skills, herramientas integradas, servidores MCP (`mcp` y `builtin` se fuerzan a enlace), binarios/wrappers y `agyc_core.py` + `lib/platform/`. |
| `.gemini/config` | **Symlink / NTFS Junction** | `<real_home>/.gemini/config` | Comparte configuración global de servidores MCP. |
| `.npm` | **Symlink / NTFS Junction** | `<real_home>/.npm` | Deduplica cachés de `npx`/MCP entre perfiles aislados. |
| `.gitconfig`, `.git-credentials`, `.ssh`, `.config/gh`, `.config/herdr` | **Symlink / NTFS Junction / Hardlink** | `<real_home>/<dotfile>` | Mantiene credenciales Git, llaves SSH, GitHub CLI e IPC de Herdr operativos dentro del `HOME` aislado. |

### 2.3 Validación de alias (`validate_alias`) y sanitización de `--json`

- **Validación anti-traversal (`validate_alias`):**
  1. Normaliza alias correlativos mediante `normalize_alias()` (`agy1` → `agy01`, `agi2` → `agy02`).
  2. Rechaza cadenas vacías, `..`, `/`, `\`, bytes nulos `\x00` y longitudes `> 32` o caracteres fuera de `^[a-zA-Z0-9][a-zA-Z0-9_-]{0,31}$`.
  3. Rechaza nombres reservados definidos en `RESERVED_ALIASES` (`config`, `agy`, `agi`, `agyc`, `agy-real`, `agyc-statusline`, `agyc-titleline`, `agyc-topbar`, `list`, `switch`, `auto`, `doctor`, `wipe`, `update`, `export`, `import`, etc.).
- **Sanitización de salida (`agyc list --json`):**
  `sanitize_account_for_json()` construye una proyección segura usando únicamente la lista blanca `SAFE_QUOTA_KEYS` para `quota` y aplica recursivamente `_scrub_secrets()`, que elimina cualquier clave cuyo nombre contenga subcadenas sensibles (`token`, `secret`, `password`, `credential`, `auth_code`, `private_key`, `cookie`, `authorization`). Así, `access_token`, `refresh_token`, `id_token` y `client_secret` nunca aparecen en `--json`.

---

## 3. Autenticación OAuth2, Refresh Concurrente y APIs de Google CloudCode PA

### 3.1 Flujo OAuth2 con localhost callback y protección CSRF

Al ejecutar `agyc add` o `agyc renew <alias>`:
1. **Scopes solicitados (`GOOGLE_SCOPES`):**
   - `https://www.googleapis.com/auth/cloud-platform`
   - `https://www.googleapis.com/auth/userinfo.email`
   - `https://www.googleapis.com/auth/userinfo.profile`
   - `https://www.googleapis.com/auth/cclog`
   - `https://www.googleapis.com/auth/experimentsandconfigs`
   - `https://www.googleapis.com/auth/aicode`
2. **Servidor local y `state` CSRF:** `OAuthCallbackHandler` (`http.server.HTTPServer`) escucha en `127.0.0.1` probando los puertos `OAUTH_PORTS = [9120, 9121, 9122, 9123, 9124]`, con `redirect_uri = http://localhost:<port>/oauth-callback`. Se genera `oauth_state = secrets.token_urlsafe(24)` y el callback verifica `received_state == expected_state` antes de aceptar el parámetro `code` (devolviendo HTTP `400` ante discrepancias). También soporta pegado manual de URL/código en sesiones SSH sin navegador durante una ventana de `180s`.
3. **Intercambio y detección:** Obtiene `access_token`, `refresh_token` (`access_type=offline`, `prompt=select_account consent`) e `id_token`, consulta el perfil del usuario y guarda `accounts/<alias>.json` (`0600`).

### 3.2 Refresh concurrente con `acquire_file_lock()` (`fcntl.flock` / `msvcrt.locking`) y Double-Checked Locking

Cuando varios paneles consultan cuotas o lanzan `agyc-statusline` simultáneamente y el token está próximo a expirar (`< 300s` respecto a `expiry` o `force=True`):
1. `refresh_token_if_needed(..., alias=alias)` abre `<locks_dir>/<alias>.oauth.lock` (`0600`) y adquiere un lock exclusivo mediante `acquire_file_lock()` (`fcntl.flock(..., LOCK_EX)` en Linux; `msvcrt.locking(..., LK_LOCK / LK_NBLCK, 1)` sobre el byte 0 en Windows).
2. **Double-checked locking:** Ya dentro del lock, vuelve a leer `accounts/<alias>.json` desde disco. Si otro proceso ya renovó el token mientras esperaba el lock (margen `>= 300s`, o `>= 3570s` en caso de `force=True`), reutiliza el token fresco de disco y sincroniza `~/.agyc_homes/<alias>/.gemini/antigravity-cli/antigravity-oauth-token` sin hacer otra petición a Google.
3. Si aún requiere renovación, hace `POST https://oauth2.googleapis.com/token` con `grant_type=refresh_token`. Si Google responde `400`/`401` con `invalid_grant`, marca `is_revoked = True` en `accounts/<alias>.json` y lanza `TokenRevokedError`.
4. Si la renovación tiene éxito, guarda `token_data` actualizado (`is_revoked = False`) en `accounts/<alias>.json` y sincroniza atómicamente el `antigravity-oauth-token` del `HOME` aislado antes de liberar el lock.

### 3.3 APIs de Google CloudCode PA, fusión `min()` y normalización

`fetch_quota_summary()` usa `User-Agent: antigravity/1.5.10 (aidev_client; os_type=linux; arch=amd64; cl=999999999)` (`ANTIGRAVITY_UA` en `lib/agyc_core.py`) y tanto `bin/agyc` como `bin/agyc-statusline` envían en `v1internal:loadCodeAssist` `"platform": "WINDOWS_AMD64" if IS_WINDOWS else "LINUX_AMD64"`. Ejecuta tres pasos:

1. **Detección de suscripción (`v1internal:loadCodeAssist`):**
   Consulta `https://cloudcode-pa.googleapis.com/v1internal:loadCodeAssist` y, si no obtiene `paidTier` (o para evitar degradar a `FREE`), consulta `https://daily-cloudcode-pa.googleapis.com/v1internal:loadCodeAssist` conservando el tier de mayor rango (`ultra` > `pro` > `enterprise`/`standard` > `free`).
   - Determina `plan_type` (`ULTRA`, `PRO`, `ENT`, `FREE`), `tier_id`, `tier_name`, `project_id` (`cloudaicompanionProject`) y `supports_carbon = (plan_type == "ULTRA")`.
2. **Fusión paralela de cuotas (`ThreadPoolExecutor(max_workers=4)`):**
   Consulta simultáneamente 4 endpoints en `daily-cloudcode-pa.googleapis.com` y `cloudcode-pa.googleapis.com`:
   - `v1internal:retrieveUserQuotaSummary` (daily + prod): fusiona grupos (`gemini` vs `claude`) y ventanas (`5h` vs `weekly`) tomando `min(remainingFraction)` entre ambos entornos para no mostrar saldo optimista desfasado.
   - `v1internal:retrieveUserQuota` (daily + prod): fusiona buckets por `modelId` tomando igualmente `min(remainingFraction)`.
3. **Separación `5h` vs `weekly`, normalización y redondeo:**
   - `_classify_bucket_window()` clasifica por `"5h"` / `"five hour"` vs `"weekly"` / `"month"`. En `extract_quota_metrics()` para buckets por modelo sin etiqueta explícita, distingue el horizonte comparando `resetTime` contra un umbral (`<= ~6.5h` → `5h`; mayor → `weekly`).
   - `normalize_window(frac, reset_str)` devuelve `(1.0, None)` si `reset_str <= now_utc` (ventana expirada ya recargada) o si `frac >= 0.9995` (eliminando `resetTime` sintéticos cuando la ventana está íntegra).
   - `pct_display(frac)` devuelve `100` si `frac is None` o `>= 0.9995`, `0` si `<= 0.0005`, y en el resto usa `min(99, math.floor(frac * 100.0 + 1e-9))` para nunca mostrar `100%` falso cuando ya existe consumo.

### 3.4 Portabilidad entre equipos (`agyc export` / `agyc import`)

`cmd_export` y `cmd_import` en `bin/agyc` permiten migrar vinculaciones OAuth entre máquinas (**Windows ↔ Ubuntu Linux**) sin repetir la autenticación OAuth2 en navegador:
- **`agyc export [alias] [-o <archivo>]` (`BUNDLE_FORMAT_V1 = "agyc-bundle-v1"`):** Exporta una cuenta específica o todas las cuentas válidas de `accounts/` (excluyendo `config.json` y archivos `_*`), generando un bundle JSON con `format`, `exported_at` y `accounts` escrito atómicamente con `_atomic_write_json(..., mode=0o600)` (`agyc-<alias>.json` o `agyc-accounts-bundle.json` por defecto).
- **`agyc import <archivo> [--alias <nuevo_alias>] [--overwrite]`:** Valida `BUNDLE_FORMAT_V1` y cada alias (`validate_alias`), detecta colisiones por alias o email (`_find_alias_by_email`), rechaza `--alias` en bundles con más de 1 cuenta, escribe `accounts/<alias>.json`, invoca `prepare_isolated_home()` + `sync_launchers()` y activa la primera cuenta importada si `config.json` no tenía `active_account`.
- **Seguridad operativa:** El bundle incluye `token_data` en claro; debe transferirse por canal cifrado (`scp`), eliminarse tras importar y tener en cuenta que el uso paralelo simultáneo en dos equipos puede provocar invalidación por rotación de `refresh_token`.

---

## 4. Motor Inteligente de Rotación (`agyc auto`) y Gestión de Flota

### 4.1 Notas, reservas y detección en vivo (`EN USO`)

- **Notas y bloqueos:** `agyc note <alias> "<texto>"` (`--clear` para limpiar) y `agyc lock <alias> "[motivo]"` / `agyc unlock <alias>` persisten `note`, `locked` y `lock_reason` en `accounts/<alias>.json`. En `agyc list` (131 columnas exactas), la segunda línea de cada fila muestra la nota/motivo y los paneles activos (`▶ en pX`).
- **Detección en vivo (`scan_active_herdr_panes`):**
  1. Escanea `/proc/[0-9]*` (solo UID actual) buscando binarios ELF `agy-real` o `agy`/`antigravity` (excluyendo intérpretes Python/Bash/Node y procesos en estado `Z`/`X`).
  2. Lee `/proc/<pid>/environ` para extraer `HERDR_PANE_ID` y el alias desde `HOME` (`/.agyc_homes/<alias>`), `ANTIGRAVITY_APP_DATA_DIR`, `AGYC_ACCOUNT` o `AGYC_ALIAS`, deduplicando múltiples subprocesos del mismo `pane_id` (priorizando procesos activos sobre detenidos `T`/`t`).
  3. Consulta `pane.list` en el UNIX socket de Herdr (`~/.config/herdr/herdr.sock`, timeout `0.06s`): si Herdr está en línea, descarta procesos huérfanos cuyo `pane_id` ya fue cerrado y enriquece cada panel con `short_pane`, `label`, `tab_id` y `focused`.

### 4.2 Reglas de `compute_smart_auto_choice()`

El selector recibe `accounts_map`, `target_mode` (`auto`, `gemini`, `claude`, `carbon`/`ultra`), `active_model`, `active_panes_map`, `allow_ultra_for_pro_models` (`--allow-ultra`) y `exclude_pane_id` (para no penalizar al propio panel que invoca `agyc auto`):

1. **Descartes iniciales:** Excluye cuentas con `is_revoked == True` y `locked == True` (`🔒 RESERVADA`).
2. **Filtro estricto `Carbon`:** Si `target_mode` es `carbon`/`ultra` o `active_model` contiene `"carbon"`, descarta toda cuenta que no sea `ULTRA`. Si no existe ninguna `ULTRA` válida, retorna `reason = "no_ultra"`.
3. **Regla estricta `AND` de disponibilidad:** Una cuenta solo es candidata disponible si `q5h > 0.001 and qweek > 0.001` (y `not disabled`). Si `qweek <= 0.001` o `disabled`, fuerza `q5h = 0.0`. Paralelamente calcula `earliest_alias` y `min_reset_seconds` entre las agotadas usando `rweek` (si `qweek <= 0.001`) o `r5h` (si solo `5H` está en `0%`).
4. **Reserva `ULTRA`:** En modos estándar (`gemini`, `claude`) y sin `--allow-ultra`, si existe al menos una cuenta `PRO` saludable (`q5h >= 0.15 and qweek >= 0.15`), excluye del pool activo a todas las cuentas `ULTRA` marcándolas `[Reserva ULTRA protegida para Carbon]`. Si no hay `PRO` saludables, habilita automáticamente el fallback a `ULTRA`.
5. **Puntuación base por familia:**
   - `carbon`: `0.70 * qweek + 0.30 * q5h` (`+0.01` si `tier_id == "g1-ultra-tier"`).
   - `claude`: `0.65 * qweek + 0.35 * q5h`.
   - `gemini` pesado (`argon`, `hydrogen`, `orchestrator`): `0.55 * qweek + 0.45 * q5h`.
   - `gemini` estándar: `0.60 * q5h + 0.40 * qweek`.
6. **Anti-Colisión:** Si la cuenta no está ocupada en otros paneles (`busy_n == 0`) y tiene `q5h >= 0.15`, suma `+0.30`; si tiene `busy_n > 0` paneles activos, penaliza `-0.15 * busy_n`.
7. **Burn-First:** Si la cuenta está libre (`busy_n == 0`), su ventana `5H` ya está iniciada y saludable (`0.20 <= q5h < 0.9995`) y tiene reserva semanal (`qweek >= 0.25`), suma `+0.22` (`burn_first = True`) para drenar la ventana ya abierta antes de estrenar una cuenta al `100% Disponible`.

### 4.3 `agyc doctor [--fix]` y `agyc update`

`cmd_doctor` ejecuta **6 auditorías secuenciales** (y con `--fix` aplica reparaciones idempotentes):
1. **`[1/6]` Binarios, Librería y PATH:** Verifica `agy-real` (`>= 1.5.10`), ausencia de recursión en el wrapper `agy`, presencia de `agyc`, `agyc-statusline`, `agyc-titleline`, `agyc-topbar`, lanzadores `agy01..agy15`, `lib/agyc_core.py` y `PATH`.
2. **`[2/6]` Permisos de Seguridad (`0700` / `0600`):** Audita `0700` en `accounts/`, `~/.agyc_homes`, `~/.cache/agyc`, `locks/` y cada perfil `~/.agyc_homes/<alias>`, y `0600` en `accounts/*.json`, `antigravity-oauth-token`, `settings.json` y `quota_cache_*.json`.
3. **`[3/6]` Aislamiento de Perfiles, Symlinks y Duplicados:** Verifica `HOME` aislado, sincronización de `refresh_token`/`access_token` contra `accounts/<alias>.json`, symlinks `builtin`, `mcp` y dotfiles (`.gitconfig`, `.ssh`, `.config/herdr`), emails duplicados y tokens revocados.
4. **`[4/6]` Auditoría de Espacio y Cachés Duplicadas:** Detecta carpetas `.npm` reales dentro de `~/.agyc_homes/*` (y con `--fix` las unifica por symlink hacia `~/.npm`), además de limpiar archivos residuales `/tmp/agyc_*`.
5. **`[5/6]` Telemetría TUI y TopBar de Herdr:** Verifica `"statusLine"` y `"title"` en todos los `settings.json`, presencia de `agyc-topbar` en `~/.config/herdr/config.toml` y latencia del socket de Herdr.
6. **`[6/6]` Resumen Operativo de Flota:** Conteo por plan (`ULTRA`, `PRO`, `ENT`, `FREE`), cuentas `locked` y paneles `agy` vivos por cuenta.

`cmd_update` (invocado también por `agy update` / `agy upgrade`) ejecuta `git pull` sobre el repo (o descarga `bin/agyc` por HTTPS), resincroniza binarios, `lib/` (incluido `lib/platform/`), symlinks (Linux) o wrappers `.cmd` (Windows) y lanzadores `agy01..15`, y actualiza el binario oficial de Google Antigravity CLI sin sobrescribir jamás los wrappers `agy`/`agy.cmd`:
- **Linux:** consulta `manifests/linux_amd64.json`, extrae `antigravity` desde `.tar.gz`, verifica `_verify_sha512()` (hex de 128 chars o Base64) y reemplaza `agy-real` vía `os.replace()`.
- **Windows:** consulta `manifests/windows_amd64.json`, reutiliza `%LOCALAPPDATA%\agy\bin\agy.exe` si su SHA-512 coincide o descarga/extrae el paquete `.zip` (`zipfile`), verifica `_verify_sha512()` y reemplaza `agy-real.exe` (renombrando el binario en uso a `.old` ante `PermissionError` y limpiando `.old` en el siguiente `update`).

---

## 5. Telemetría en Vivo (4 Superficies) y Alerta `≤15%`

Todas las superficies muestran las métricas en el orden unificado **`5H → Ctx → Sem`**.

### 5.1 `agyc-statusline` (pie TUI) y refresco asíncrono

- Ejecuta con `#!/usr/bin/python3 -S` (sin `site.py`) cargando `lib/platform/` de forma perezosa (`_load_platform()`) para mantener latencia `<3ms` sin importar `agyc_core` en el hot-path.
- **`read_stdin_json(max_wait_sec=0.020)`:** Delega en `platform.read_stdin_nonblocking(max_wait_sec)` — en Linux usa `os.set_blocking(fd, False)` + `select.select(..., 0.005)` + `os.read(fd, 65536)`; en Windows usa `PeekNamedPipe` (`kernel32.dll` + `msvcrt.get_osfhandle`) con fallback por hilo daemon (`_read_fd_via_thread`) para no colgarse si se invoca sin `EOF` inmediato.
- **Refresco en background (`20s` TTL / `15s` lock):** `fetch_online_quota()` lee `<cache_dir>/quota_cache_<alias>.json` (`0600`). Si el caché supera `CACHE_TTL_SECONDS = 20` o no existe, `spawn_background_refresh()` crea `quota_refreshing_<alias>.lock` (throttle de `REFRESH_LOCK_SECONDS = 15`) y lanza `agyc-statusline --refresh-quota-bg <alias>` vía `platform.spawn_detached()` (`start_new_session=True` en Linux; `CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS` en Windows) con `HOME=REAL_HOME` (y `USERPROFILE=REAL_HOME` en Windows). Nunca bloquea la TUI esperando red.

### 5.2 Cálculo exacto de `% Contexto` (prioridad `current_usage` + fallback O(1))

`get_context_usage()` determina `(fraction, used_tokens, max_tokens)` usando `default_max_tokens_for_model()` (`65_536` para modelos de imagen, `131_072` para `GPT-OSS 120B`, `250_000` para `Claude 4.6/5.5`, `200_000` para otros Claude y `1_048_576` para Gemini):
1. **Prioridad 1 (`stdin_data.context_window.current_usage`):** Suma `input_tokens + cache_creation_input_tokens + cache_read_input_tokens + output_tokens` (nunca acumulados globales `total_*_tokens`). Si `used_percentage` está presente y difiere por compactación post-turno (`pct_tokens < cu_tokens * 0.6`) o crecimiento intra-turno (`pct_tokens > cu_tokens + max(2048, 1%)`), prioriza `used_percentage`.
2. **Prioridad 2 (Fallback O(1) sobre `transcript.jsonl`):** Cuando `current_usage` es `None` (ej. sesión reabierta con `/resume`), `estimate_context_from_transcript()` lee en orden inverso desde EOF en dos ventanas (`128 KB` → `512 KB`), descartando la primera línea parcial si `offset > 0`:
   - Se detiene inmediatamente ante cualquier frontera de compactación (`type` en `CHECKPOINT`, `CONTEXT_SUMMARY`, `COMPACTION`, `# Resuming from a compaction`, `<CONTEXT_SUMMARY>`, o `is_compaction`/`compacted`), calculando `base_tokens` + caracteres posteriores (`/ 4.0`) sin leer megabytes pre-compactación.
   - Si encuentra un `PLANNER_RESPONSE` reciente con contadores de uso (`input_tokens` / `cache_read_*`), suma esos tokens más los caracteres posteriores (`/ 4.0`).

Finalmente, `persist_pane_context()` guarda `<cache_dir>/pane_ctx_<pane|conv>.json` (`0600`) para que `agyc-topbar` consuma el `% Ctx` al instante.

### 5.3 `agyc-titleline`, bordes Herdr (`pane.report_metadata`), `agyc-topbar` y toast `≤15%`

- **`agyc-titleline`:** Configurado en `"title"` de `settings.json`, imprime texto plano sin ANSI (`⚡ agy01 [ULTRA] · Gemini 4 Carbon (high) · 5H: 82% (4h 25m) · Ctx: 36% · Sem: 91% (6d 23h)`). Detecta el modo título por `basename(sys.argv[0])` (sin `.cmd`/`.exe`/`.bat`), `AGYC_INVOKED_AS=agyc-titleline` o `--title`.
- **`pane.report_metadata` (Herdr):** Tanto `statusline` como `titleline` envían JSON mediante `platform.query_herdr_ipc()` (timeout `0.05s`) — por `AF_UNIX` en `~/.config/herdr/herdr.sock` en Linux, o leyendo `<port>:<nonce>` desde `%APPDATA%\herdr\herdr.sock` (o `HERDR_SOCKET_PATH` / `.config/herdr/herdr.sock`) y conectando por TCP `127.0.0.1:<port>` en Windows. Aplica un throttle de `8s` en `herdr_meta_<pane>.json`, con **bypass inmediato** si cambia `account`, `plan`, `model`, `low_quota` o `abs(ctx_pct - prev_ctx) >= 3`.
- **`agyc-topbar`:** Configurado en `[[ui.tab_bar_right]]` de Herdr. Consulta `pane.list` vía `platform.query_herdr_ipc()` + `platform.scan_agy_processes()` (`/proc` en Linux o `CreateToolhelp32Snapshot` + `<run_dir>\<pid>.json` en Windows) para identificar la cuenta del panel enfocado (o pestaña activa), carga `pane_ctx_*.json` (o estima desde `transcript.jsonl`) y muestra ambos grupos `Gemini` y `Claude` en orden `5H → Ctx → Sem`.
- **Alerta `≤15%` y Toast único por ciclo (`maybe_notify_low_quota`):**
  Cuando `quota_initialized` es verdadero y `eff_pct = min(p5, ps) <= 15`:
  - `agyc-statusline` inserta el badge `⚠ ≤15%` (o `⚠ AGOTADA` si `0%`), y `titleline`/`pane.report_metadata` anteponen `⚠`.
  - Adquiere un lock no bloqueante con `platform.acquire_file_lock(..., blocking=False)` sobre `low_quota_<alias>_<familia>.lock` y verifica `low_quota_alert_<alias>_<familia>.json` (`LOW_QUOTA_DEDUP_SECONDS = 5 * 3600` sobre `reset_key = r5 or rs or "active"`).
  - Si no ha notificado en ese ciclo, busca localmente (`<3ms`) la mejor cuenta libre respetando `is_revoked`, `locked`, paneles ocupados en `pane.list` y *Reserva ULTRA*, y llama a `platform.send_low_quota_toast(title, body, herdr_bin=...)`: en Linux/Windows usa `herdr notification show --position top-right --sound none --body ...` desacoplado; en Windows, si `herdr.exe` no está disponible, hace fallback nativo mediante `powershell.exe` + `System.Windows.Forms.NotifyIcon` (`ShowBalloonTip(5000)`).

---

## 6. Capa Multiplataforma Implementada (`lib/platform/`) y Lanzamiento Nativo

La capa `lib/platform/` (`__init__.py`, `linux.py`, `win32.py`) está implementada e integrada en `lib/agyc_core.py`, `bin/agyc`, `bin/agyc-statusline` y `bin/agyc-topbar`, con paridad de API verificada por las **38 pruebas unitarias** de `tests/test_agyc.py` (`test_01`..`test_38`).

| Pieza / Mecanismo | Implementación Linux (`lib/platform/linux.py` + `install.sh`) | Implementación Windows (`lib/platform/win32.py` + `install.ps1`) |
|---|---|---|
| **Rutas base, caché, locks y run** | `resolve_real_home()` vía `AGYC_REAL_HOME`/`REAL_HOME`/`pwd.getpwuid()`/`HOME`; `get_base_dir()` (`~/.gemini/antigravity-cli` o snap); `get_cache_dir()` (`~/.cache/agyc`); `get_locks_dir()`; `get_run_dir()`. | `resolve_real_home()` vía `AGYC_REAL_HOME`/`REAL_HOME`/`USERPROFILE`/`~`/`HOME` limpiando `\.agyc_homes\`; `get_base_dir()` (`%USERPROFILE%\.gemini\antigravity-cli`); `get_cache_dir()` (`%LOCALAPPDATA%\agyc\cache` o `<real_home>\.cache\agyc`, con override `AGYC_CACHE_DIR`); `get_locks_dir()`; `get_run_dir()`. |
| **Permisos privados y ACLs** | `ensure_private_dir(..., 0o700)`, `ensure_private_file(..., 0o600)` con `os.chmod`. `harden_ntfs_acl()` actúa como stub POSIX. | `ensure_private_dir()` / `ensure_private_file()` sin fallar por bits POSIX; `harden_ntfs_acl()` obtiene SID vía `whoami /user /fo csv /nh` y aplica `icacls <path> /inheritance:r /grant:r *<SID>:(OI)(CI)F` (o `*<SID>:F`). |
| **Enlaces de directorios y archivos** | `create_dir_link()` (`os.symlink`), `is_dir_link()` (`os.path.islink`), `read_dir_link()` (`os.readlink`), `create_file_link()` (`os.symlink`). | `create_dir_link()` crea **NTFS Junctions** vía `cmd /c mklink /J` (sin privilegios Admin); `is_dir_link()` usa `os.path.isjunction` / `os.path.islink` / `GetFileAttributesW`; `read_dir_link()` limpia prefijo `\\?\`; `create_file_link()` usa hardlink `os.link()` con fallback `shutil.copy2()`. |
| **Lanzadores y ejecución (`launch_real_agy`)** | Symlinks `agy01..agy15` -> `agyc`, wrapper Bash `bin/agy`, `os.execve()` con `SSH_TTY` para bypass de keyring. | Wrappers `.cmd` (`bin/agy.cmd`, `agi.cmd`, `agyc.cmd`, `agy01.cmd..15.cmd`, `agyc-statusline.cmd`, `agyc-titleline.cmd`, `agyc-topbar.cmd`) en `%LOCALAPPDATA%\agyc\bin` (sin `.ps1` para evitar restricciones de `ExecutionPolicy`); `subprocess.Popen` con `SSH_TTY=/dev/pts/0` (bypass de Windows Credential Manager `wincred` / `gemini:antigravity`), registro `<run_dir>\<pid>.json` y limpieza al salir. |
| **Locks concurrentes** | `acquire_file_lock()` vía `fcntl.flock(..., LOCK_EX | LOCK_NB)` en `_PosixFileLock`. | `acquire_file_lock()` vía `msvcrt.locking(fd, LK_LOCK | LK_NBLCK, 1)` sobre el byte 0 en `_Win32FileLock`, traduciendo contención a `BlockingIOError`. |
| **Detección de procesos (`scan_agy_processes` / `find_ancestor_agy_pid`)** | Escaneo directo de `/proc/<pid>/{comm,stat,environ}` filtrando binarios ELF `agy-real`/`agy`/`antigravity` del UID actual (excluyendo `Z`/`X`). | `_list_win32_processes_with_ppid()` vía `CreateToolhelp32Snapshot` (`Process32FirstW`/`Process32NextW`) filtrando `agy-real.exe`, `agy.exe`, `antigravity.exe` + cruce con `<run_dir>\<pid>.json` y purga de PIDs muertos; `find_ancestor_agy_pid()` escala `th32ParentProcessID` desde `agyc-statusline`. |
| **IPC Herdr (`query_herdr_ipc`)** | `default_herdr_socket_path()` (`~/.config/herdr/herdr.sock`); socket `AF_UNIX` JSON-line (`timeout=0.06`). | `default_herdr_socket_path()` (`%APPDATA%\herdr\herdr.sock` o `.config/herdr/herdr.sock`); conecta vía Windows Named Pipe `\\.\pipe\<herdr.sock>` (`_query_herdr_named_pipe`), con fallback TCP `127.0.0.1:<port>`. Auto-configura `[ui]` (`show_agent_labels_on_pane_borders = true`, `[[ui.tab_bar_right]]` `agyc-topbar.cmd`, `[ui.toast]`) en `install.ps1` y `agyc doctor --fix`. |
| **Lectura no bloqueante de `stdin`** | `read_stdin_nonblocking()` con `os.set_blocking(fd, False)` + `select.select(..., 0.005)`. | `read_stdin_nonblocking()` con Win32 `PeekNamedPipe` (`kernel32.dll` + `msvcrt.get_osfhandle`) y fallback `_read_fd_via_thread()`. |
| **Subprocesos y Toast (`≤15%`)** | `spawn_detached()` (`start_new_session=True`); `send_low_quota_toast()` vía `herdr notification show`. | `spawn_detached()` (`CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS`); `send_low_quota_toast()` vía `herdr.exe` o fallback `powershell.exe` + `System.Windows.Forms.NotifyIcon`. |
| **CloudCode PA y `agyc update`** | `LINUX_AMD64` + `manifests/linux_amd64.json` (`.tar.gz`, `_verify_sha512`, `os.replace`). | `WINDOWS_AMD64` + `manifests/windows_amd64.json` (`.zip` / `agy.exe` local, `_verify_sha512`, rotación `.old`). |

### 6.1 Carga perezosa bajo `python -S` y verificación (`tests/test_agyc.py`)

- **Carga perezosa `<2ms` (`test_30`):** `lib/agyc_core.py` y `lib/platform/__init__.py` difieren las importaciones pesadas (`ctypes`, `subprocess`, `_socket`, `msvcrt`, `pwd`, `fcntl`, `select`, `shutil`, `json`, `threading`) al interior de cada función, y `_plat()` carga `lib.platform` (o `_agyc_platform` vía `importlib.util`) sin sombrear el módulo `platform` de la stdlib.
- **Cobertura de 38 pruebas (`tests/test_agyc.py`):**
  - `TestPathsAliasesAndSecurity` (`test_01`..`test_06`): alias, anti-traversal, `resolve_real_home`, permisos privados, `atomic_write_json` y sanitización `--json`.
  - `TestWindowsDisplayAndContext` (`test_07`..`test_13`): normalización de ventanas, `pct_display` y estimador O(1) de `% Ctx` post-compactación.
  - `TestSmartAutoChoiceEngine` (`test_14`..`test_22`) y `TestHerdrActivePaneScanner` (`test_23`): *Reserva ULTRA + Burn-First + Anti-Colisión*.
  - `TestPlatformAbstractionLayer` (`test_24`..`test_32`): locks concurrentes, NTFS Junctions / symlinks, `create_file_link`, `read_stdin_nonblocking`, `query_herdr_ipc` (`AF_UNIX` / TCP `127.0.0.1:<port>`), `CreateToolhelp32Snapshot` + purga `<pid>.json`, `python -S` lazy imports, `harden_ntfs_acl` / `spawn_detached` / `send_low_quota_toast` y paridad API Linux/Win32.
  - `TestExportAndImport` (`test_33`..`test_38`): exportación individual/global (`agyc-bundle-v1` excluyendo `_*.json` y `config.json`), importación en `HOME` limpio con aislamiento y activación automática, `--alias` en bundles de 1 cuenta (rechazado en multi-cuenta), control de duplicados con/sin `--overwrite`, bypass de Windows Credential Manager (`SSH_TTY=/dev/pts/0` en `launch_real_agy`, `bin/agy.cmd` y `_default_agy_cmd_content`), Named Pipe IPC (`\\.\pipe\...`) y `find_ancestor_agy_pid`.
