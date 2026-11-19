# Arquitectura y Funcionalidad Técnica de `agyc` (`v1.6`)

> **Repositorio:** `agyc-antigravity-cli-switcher`
> **Motor soportado:** Google Antigravity CLI `1.5.10+` (`PRO` / `ULTRA`)
> **Plataforma actual:** Ubuntu Linux `x86_64` (Python `3.10+` stdlib puro)

Este documento describe la arquitectura interna, el modelo de seguridad y aislamiento, el protocolo OAuth2 y de cuotas CloudCode PA, el motor de rotación inteligente, la telemetría en vivo en 4 superficies y el *blueprint* de portabilidad a Windows 10/11. Todo lo aquí descrito corresponde directamente al código fuente del repositorio.

---

## 1. Visión General y Mapa de Componentes

`agyc` separa la lógica de dominio pura (`lib/agyc_core.py`), el CLI administrativo y lanzador (`bin/agyc`), el wrapper de seguridad de `agy` (`bin/agy`), y los renderizadores de telemetría de baja latencia (`bin/agyc-statusline`, `agyc-titleline`, `bin/agyc-topbar`).

| Componente | Ubicación en repo | Ubicación instalada | Rol exacto |
|---|---|---|---|
| **Núcleo compartido** | `lib/agyc_core.py` (`lib/__init__.py`) | `~/.gemini/antigravity-cli/lib/agyc_core.py` (`0644`) | Lógica pura en Python stdlib (`<2ms` bajo `python3 -S`, imports pesados diferidos): resolución de `REAL_HOME`, validación de alias, escritura atómica `0600`, sanitización `--json`, normalización de ventanas, estimación O(1) de `% Ctx` desde EOF, escáner `/proc` + Herdr (`scan_active_herdr_panes`) y motor `compute_smart_auto_choice`. |
| **CLI y lanzador** | `bin/agyc` | `~/.gemini/antigravity-cli/bin/agyc` + symlink `~/.local/bin/agyc` + symlinks `agy01..agy15` / `agi01..agi15` | Interfaz de usuario (`list`, `add`, `renew`, `switch`, `default`, `auto`, `note`, `lock`, `unlock`, `quota`, `doctor`, `rm`, `wipe`, `update`) y lanzador directo cuando se invoca por alias (`os.path.basename(sys.argv[0])`), preparando el `HOME` aislado y ejecutando `agy-real` vía `os.execv`. |
| **Wrapper `agy`** | `bin/agy` | `~/.gemini/antigravity-cli/bin/agy` + symlink `~/.local/bin/agy` | Script Bash que intercepta `agy update`/`agy upgrade` hacia `agyc update`, resuelve `REAL_HOME`, localiza el binario nativo `agy-real` (o Snap `/snap/antigravity-cli/current/bin/agy`) sin recursión sobre `~/.local/bin/agy`, inyecta `SSH_TTY` si falta para evitar prompts de GNOME Keyring y ejecuta `--dangerously-skip-permissions` por defecto. |
| **Barra inferior TUI** | `bin/agyc-statusline` | `~/.gemini/antigravity-cli/bin/agyc-statusline` + symlink `~/.local/bin/agyc-statusline` | Script `#!/usr/bin/python3 -S` invocado por Antigravity (`settings.json -> statusLine`). Lee `stdin` de forma no bloqueante, renderiza la barra ANSI `5H → Ctx → Sem`, persiste `pane_ctx_*.json`, reporta `pane.report_metadata` a Herdr, dispara refresco de cuota en background (`--refresh-quota-bg`) y emite toast único al `≤15%`. |
| **Título OSC** | Symlink `agyc-titleline` → `agyc-statusline` | `~/.gemini/antigravity-cli/bin/agyc-titleline` y `~/.local/bin/agyc-titleline` | Invocado por Antigravity (`settings.json -> title`). Detecta `basename(sys.argv[0]) == "agyc-titleline"` (o `--title`) y emite texto plano sin códigos ANSI para el título OSC de ventana/pestaña, sincronizando también `pane_ctx_*`, `pane.report_metadata` y alerta `≤15%`. |
| **Barra global Herdr** | `bin/agyc-topbar` | `~/.gemini/antigravity-cli/bin/agyc-topbar` + symlink `~/.local/bin/agyc-topbar` | Widget `#!/usr/bin/python3 -S` (`<20ms`) para `[[ui.tab_bar_right]]` de Herdr (`~/.config/herdr/config.toml`). Identifica la cuenta del panel enfocado (o pestaña activa) y renderiza cuotas `Gemini` y `Claude` intercalando `Ctx` en orden `5H → Ctx → Sem` (soporta `--json` y `--account`). |
| **Instalador** | `install.sh` | Raíz del repo | Instalador en 7 pasos: verifica Python 3.10+ y motor `agy`, crea directorios `0700`/`0600`, deduplica `.npm`, instala `lib/`, binarios, wrapper `agy` (respaldando el binario nativo en `agy-real`), symlinks `agyc-titleline` y `agy01..agy15`, configura `settings.json`, `PATH`, skill `SKILL.md` y ejecuta `unittest`. |
| **Suite de tests** | `tests/test_agyc.py` | Raíz del repo (`tests/`) | 23 pruebas unitarias herméticas sobre `lib/agyc_core.py` (sin red, usando `tempfile.TemporaryDirectory`, mocks de `pwd.getpwuid`, `/proc` sintético y socket `AF_UNIX` real en memoria). |

---

## 2. Modelo de Almacenamiento, Aislamiento y Seguridad

### 2.1 Estructura de directorios y permisos (`0700` / `0600`)

`agyc` resuelve el directorio real del usuario mediante `resolve_real_home()` (priorizando `AGYC_REAL_HOME`, `REAL_HOME`, `pwd.getpwuid(os.getuid()).pw_dir` y `HOME`, limpiando cualquier segmento `/.agyc_homes/*`) para que los subprocesos lanzados dentro de un perfil aislado sigan encontrando el almacén maestro.

```text
~/.gemini/antigravity-cli/                 # Directorio maestro (base_dir)
├── accounts/                              # 0700 — Almacén maestro de credenciales
│   ├── config.json                        # 0600 — {"active_account": "agy01", "default_account": "agy01"}
│   ├── agy01.json                         # 0600 — Perfil, email, plan_type, note, locked, token_data, quota
│   └── agy02.json                         # 0600 — ...
├── lib/                                   # 0755 — agyc_core.py (0644), __init__.py (0644)
├── bin/                                   # Binarios y symlinks (agy-real, agyc, agy, statusline, titleline, topbar, agy01..15)
├── settings.json                          # 0600 — Configuración base (statusLine + title)
└── conversations/, brain/, projects/, skills/, builtin/, mcp/

~/.cache/agyc/                             # 0700 — Caché privada y locks
├── locks/                                 # 0700 — Locks flock por alias (*.oauth.lock, low_quota_*.lock)
├── quota_cache_<alias>.json               # 0600 — Caché local de cuotas (TTL 20s)
├── quota_refreshing_<alias>.lock          # 0600 — Throttle de refresco en background (15s)
├── pane_ctx_<pane|conv>.json              # 0600 — Snapshot de % Ctx y modelo del panel/conversación
├── herdr_meta_<pane>.json                 # 0600 — Estado previo para throttle de 8s hacia Herdr
└── low_quota_alert_<alias>_<fam>.json     # 0600 — Deduplicación de toast ≤15% por ciclo (5h)

~/.agyc_homes/<alias>/                     # 0700 — HOME aislado por cuenta
```

Toda escritura JSON crítica usa `atomic_write_json()` (`os.open(..., os.O_CREAT | os.O_TRUNC, 0o600)` en archivo temporal + `os.chmod(0o600)` + `os.replace()`), garantizando atomicidad ante lecturas concurrentes y ausencia de fugas de permisos.

### 2.2 Qué se comparte por symlink vs qué es exclusivo por perfil

Al lanzar una cuenta (`prepare_isolated_home(alias)`), `agyc` inyecta `HOME=~/.agyc_homes/<alias>` antes de ejecutar `agy-real` con `os.execv()`. Dentro de ese `HOME` aislado:

| Recurso dentro de `~/.agyc_homes/<alias>/` | Tipo | Destino / Origen | Propósito |
|---|---|---|---|
| `.gemini/antigravity-cli/antigravity-oauth-token` | **Exclusivo (`0600`)** | Copia atómica desde `accounts/<alias>.json -> token_data` | Aísla la sesión OAuth de cada cuenta; jamás es symlink para evitar colisiones entre paneles simultáneos. |
| `.gemini/antigravity-cli/settings.json` | **Exclusivo (`0600`)** | Archivo propio por perfil | Preserva el modelo elegido por cuenta (si la cuenta es `PRO`/`FREE` y heredó `carbon`, degrada automáticamente a `Gemini 4 Argon (High)`), manteniendo activos `statusLine` y `title`. |
| `.gemini/antigravity-cli/accounts` | **Symlink** | `~/.gemini/antigravity-cli/accounts` | Permite que comandos `agyc` dentro del panel vean toda la flota. |
| `.gemini/antigravity-cli/conversations`, `brain`, `projects`, `annotations`, `history.jsonl`, `conversation_summaries.db*`, `jetbox_summaries_proto.pb`, `jetski_state.pbtxt`, `installation_id` | **Symlink** | `~/.gemini/antigravity-cli/<item>` | Unifica el historial de conversaciones (`/resume`), artefactos y memoria entre todas las cuentas. |
| `.gemini/antigravity-cli/skills`, `builtin`, `mcp`, `bin`, `lib` | **Symlink** | `~/.gemini/antigravity-cli/<item>` | Comparte skills, herramientas integradas, servidores MCP (`mcp` y `builtin` se fuerzan a symlink), binarios y `agyc_core.py`. |
| `.gemini/config` | **Symlink** | `~/.gemini/config` | Comparte configuración global de servidores MCP. |
| `.npm` | **Symlink** | `~/.npm` | Deduplica cachés de `npx`/MCP entre perfiles aislados. |
| `.gitconfig`, `.git-credentials`, `.ssh`, `.config/gh`, `.config/herdr` | **Symlink** | `~/<dotfile>` | Mantiene credenciales Git, llaves SSH, GitHub CLI e IPC de Herdr operativos dentro del `HOME` aislado. |

### 2.3 Validación de alias (`validate_alias`) y sanitización de `--json`

- **Validación anti-traversal (`validate_alias`):**
  1. Normaliza alias correlativos mediante `normalize_alias()` (`agy1` → `agy01`, `agi2` → `agy02`).
  2. Rechaza cadenas vacías, `..`, `/`, `\`, bytes nulos `\x00` y longitudes `> 32` o caracteres fuera de `^[a-zA-Z0-9][a-zA-Z0-9_-]{0,31}$`.
  3. Rechaza nombres reservados definidos en `RESERVED_ALIASES` (`config`, `agy`, `agi`, `agyc`, `agy-real`, `agyc-statusline`, `agyc-titleline`, `agyc-topbar`, `list`, `switch`, `auto`, `doctor`, `wipe`, `update`, etc.).
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

### 3.2 Refresh concurrente con `fcntl.flock` y Double-Checked Locking

Cuando varios paneles consultan cuotas o lanzan `agyc-statusline` simultáneamente y el token está próximo a expirar (`< 300s` respecto a `expiry` o `force=True`):
1. `refresh_token_if_needed(..., alias=alias)` abre `~/.cache/agyc/locks/<alias>.oauth.lock` (`0600`) y adquiere un lock exclusivo bloqueante (`fcntl.flock(lock_fd, fcntl.LOCK_EX)`).
2. **Double-checked locking:** Ya dentro del lock, vuelve a leer `accounts/<alias>.json` desde disco. Si otro proceso ya renovó el token mientras esperaba el lock (margen `>= 300s`, o `>= 3570s` en caso de `force=True`), reutiliza el token fresco de disco y sincroniza `~/.agyc_homes/<alias>/.gemini/antigravity-cli/antigravity-oauth-token` sin hacer otra petición a Google.
3. Si aún requiere renovación, hace `POST https://oauth2.googleapis.com/token` con `grant_type=refresh_token`. Si Google responde `400`/`401` con `invalid_grant`, marca `is_revoked = True` en `accounts/<alias>.json` y lanza `TokenRevokedError`.
4. Si la renovación tiene éxito, guarda `token_data` actualizado (`is_revoked = False`) en `accounts/<alias>.json` y sincroniza atómicamente el `antigravity-oauth-token` del `HOME` aislado antes de liberar el lock.

### 3.3 APIs de Google CloudCode PA, fusión `min()` y normalización

`fetch_quota_summary(access_token)` usa `User-Agent: antigravity/1.5.10 (aidev_client; os_type=linux; arch=amd64; cl=999999999)` y ejecuta tres pasos:

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

`cmd_update` (invocado también por `agy update` / `agy upgrade`) ejecuta `git pull` sobre el repo (o descarga `bin/agyc` por HTTPS), resincroniza binarios, `lib/`, `agyc-titleline` y lanzadores `agy01..15`, consulta el manifiesto oficial `manifests/linux_amd64.json` de Google Antigravity CLI, verifica la integridad del tarball/binario con `_verify_sha512()` (hexadecimal de 128 chars o Base64) y reemplaza `agy-real` atómicamente (`os.replace`) sin sobrescribir jamás el wrapper `~/.local/bin/agy`.

---

## 5. Telemetría en Vivo (4 Superficies) y Alerta `≤15%`

Todas las superficies muestran las métricas en el orden unificado **`5H → Ctx → Sem`**.

### 5.1 `agyc-statusline` (pie TUI) y refresco asíncrono

- Ejecuta con `#!/usr/bin/python3 -S` (sin `site.py`) y sin importar `agyc_core` en el hot-path para mantener latencia `<3ms`.
- **`read_stdin_json(max_wait_sec=0.020)`:** Configura `os.set_blocking(fd, False)` y lee `stdin` con `select.select(..., 0.005)` + `os.read(fd, 65536)` con tope total de `20ms` para no colgarse si se invoca sin `EOF` inmediato.
- **Refresco en background (`20s` TTL / `15s` lock):** `fetch_online_quota()` lee `~/.cache/agyc/quota_cache_<alias>.json` (`0600`). Si el caché supera `CACHE_TTL_SECONDS = 20` o no existe, `spawn_background_refresh()` crea `quota_refreshing_<alias>.lock` (throttle de `REFRESH_LOCK_SECONDS = 15`) y lanza `agyc-statusline --refresh-quota-bg <alias>` con `subprocess.Popen(..., start_new_session=True)` y `HOME=REAL_HOME`. Nunca bloquea la TUI esperando red (a diferencia de implementaciones con locks largos).

### 5.2 Cálculo exacto de `% Contexto` (prioridad `current_usage` + fallback O(1))

`get_context_usage()` determina `(fraction, used_tokens, max_tokens)` usando `default_max_tokens_for_model()` (`65_536` para modelos de imagen, `131_072` para `GPT-OSS 120B`, `250_000` para `Claude 4.6/5.5`, `200_000` para otros Claude y `1_048_576` para Gemini):
1. **Prioridad 1 (`stdin_data.context_window.current_usage`):** Suma `input_tokens + cache_creation_input_tokens + cache_read_input_tokens + output_tokens` (nunca acumulados globales `total_*_tokens`). Si `used_percentage` está presente y difiere por compactación post-turno (`pct_tokens < cu_tokens * 0.6`) o crecimiento intra-turno (`pct_tokens > cu_tokens + max(2048, 1%)`), prioriza `used_percentage`.
2. **Prioridad 2 (Fallback O(1) sobre `transcript.jsonl`):** Cuando `current_usage` es `None` (ej. sesión reabierta con `/resume`), `estimate_context_from_transcript()` lee en orden inverso desde EOF en dos ventanas (`128 KB` → `512 KB`), descartando la primera línea parcial si `offset > 0`:
   - Se detiene inmediatamente ante cualquier frontera de compactación (`type` en `CHECKPOINT`, `CONTEXT_SUMMARY`, `COMPACTION`, `# Resuming from a compaction`, `<CONTEXT_SUMMARY>`, o `is_compaction`/`compacted`), calculando `base_tokens` + caracteres posteriores (`/ 4.0`) sin leer megabytes pre-compactación.
   - Si encuentra un `PLANNER_RESPONSE` reciente con contadores de uso (`input_tokens` / `cache_read_*`), suma esos tokens más los caracteres posteriores (`/ 4.0`).

Finalmente, `persist_pane_context()` guarda `~/.cache/agyc/pane_ctx_<pane|conv>.json` (`0600`) para que `agyc-topbar` consuma el `% Ctx` al instante.

### 5.3 `agyc-titleline`, bordes Herdr (`pane.report_metadata`), `agyc-topbar` y toast `≤15%`

- **`agyc-titleline`:** Configurado en `"title"` de `settings.json`, imprime texto plano sin ANSI (`⚡ agy01 [ULTRA] · Gemini 4 Carbon (high) · 5H: 82% (4h 25m) · Ctx: 36% · Sem: 91% (6d 23h)`).
- **`pane.report_metadata` (Herdr):** Tanto `statusline` como `titleline` envían JSON por el UNIX socket `~/.config/herdr/herdr.sock` (timeout `0.05s`) con `display_agent` y `tokens`. Aplica un throttle de `8s` en `herdr_meta_<pane>.json`, con **bypass inmediato** si cambia `account`, `plan`, `model`, `low_quota` o `abs(ctx_pct - prev_ctx) >= 3`.
- **`agyc-topbar`:** Configurado en `[[ui.tab_bar_right]]` de `~/.config/herdr/config.toml`. Consulta `pane.list` en `herdr.sock` + `/proc` para identificar la cuenta del panel enfocado (o de la pestaña activa), carga `pane_ctx_*.json` (o estima desde `transcript.jsonl` si falta) y muestra ambos grupos `Gemini` y `Claude` en orden `5H → Ctx → Sem`.
- **Alerta `≤15%` y Toast único por ciclo (`maybe_notify_low_quota`):**
  Cuando `quota_initialized` es verdadero y `eff_pct = min(p5, ps) <= 15`:
  - `agyc-statusline` inserta el badge `⚠ ≤15%` (o `⚠ AGOTADA` si `0%`), y `titleline`/`pane.report_metadata` anteponen `⚠`.
  - Dentro de Herdr, adquiere `fcntl.flock(..., LOCK_EX | LOCK_NB)` sobre `low_quota_alert_<alias>_<familia>.lock` y verifica `low_quota_alert_<alias>_<familia>.json` (`LOW_QUOTA_DEDUP_SECONDS = 5 * 3600` sobre `reset_key = r5 or rs or "active"`).
  - Si no ha notificado en ese ciclo, busca localmente (`<3ms`) la mejor cuenta libre respetando `is_revoked`, `locked`, paneles ocupados en `pane.list` y *Reserva ULTRA*, y lanza de forma desacoplada (`subprocess.Popen(..., start_new_session=True)`) `herdr notification show --position top-right --sound none --body ...`.

---

## 6. Guía de Portabilidad a Windows (Blueprint para futura versión Windows)

El núcleo algorítmico de `lib/agyc_core.py` ya está escrito en Python stdlib puro. Para portar `agyc` a **Windows 10/11**, se recomienda extraer las primitivas dependientes del SO a una capa `lib/platform/` (`linux.py` y `win32.py`) según la siguiente matriz de equivalencias:

| Pieza / Mecanismo | Implementación Linux actual | Equivalente exacto en Windows 10/11 |
|---|---|---|
| **Rutas base y usuario** | `resolve_real_home()` vía `$HOME`, `AGYC_REAL_HOME` y `pwd.getpwuid()` (`~/.gemini/antigravity-cli`, `~/.cache/agyc`). | `%USERPROFILE%\.gemini\antigravity-cli`, caché y locks en `%LOCALAPPDATA%\agyc\cache` y `%LOCALAPPDATA%\agyc\locks`; configuración roaming opcional en `%APPDATA%`. Resolución vía `os.path.expanduser("~")` / `SHGetFolderPathW` (`CSIDL_PROFILE`), limpiando `\.agyc_homes\`. |
| **Aislamiento de perfiles** | `HOME=~/.agyc_homes/<alias>` + `os.symlink()` para carpetas (`accounts`, `conversations`, `brain`, `skills`, `builtin`, `mcp`, `.npm`) y archivos (`settings.json` exclusivo, `antigravity-oauth-token` exclusivo). | Inyectar `USERPROFILE` y `HOME` (y `ANTIGRAVITY_HOME` si aplica) apuntando a `%USERPROFILE%\.agyc_homes\<alias>`. Para directorios compartidos usar **NTFS Junctions** (`mklink /J` o `New-Item -ItemType Junction` / `DeviceIoControl FSCTL_SET_REPARSE_POINT`), que **no requieren privilegios de Administrador ni Developer Mode** en Windows 10/11 (a diferencia de symlinks de archivo). Para archivos compartidos puntuales (`.gitconfig`, `history.jsonl`), usar hardlinks (`os.link`) si están en el mismo volumen NTFS o copia sincronizada. |
| **Lanzadores (`agy01..agy15` y `agy`)** | Symlinks `agy01..agy15 -> agyc` + `os.execv(agy_real, ...)` y script Bash `bin/agy`. | **Wrappers `.cmd`** (`agy01.cmd`..`agy15.cmd`, `agy.cmd`, `agyc.cmd`) en `%LOCALAPPDATA%\agyc\bin` (añadido al `User PATH`), o shims `.exe` ligeros. **Evitar `.ps1`** como punto de entrada directo para no chocar con `ExecutionPolicy Restricted` en PowerShell. Reemplazar `os.execv` por `subprocess.run([agy_real, ...], env=env).returncode` seguido de `sys.exit(rc)`. |
| **Locks concurrentes** | `fcntl.flock(fd, LOCK_EX)` / `LOCK_NB` sobre `*.oauth.lock` y `low_quota_*.lock`. | `msvcrt.locking(fd, msvcrt.LK_LOCK | msvcrt.LK_NBLCK, 1)` sobre el archivo `.lock` (asegurando al menos 1 byte escrito) o Win32 Named Mutex (`ctypes.windll.kernel32.CreateMutexW` + `WaitForSingleObject`) para evitar bloqueos de lectura simultánea en Windows. |
| **Permisos privados** | `0700` / `0600` vía `os.chmod` / `os.open`. | `os.chmod` en Windows solo controla el bit `read-only`. Endurecer directorios de credenciales (`accounts\`, `*.json`, `antigravity-oauth-token`) mediante ACLs NTFS restringidas al SID del usuario actual (`icacls <ruta> /inheritance:r /grant:r "%USERNAME%:(OI)(CI)F"` o API `SetNamedSecurityInfoW`). |
| **Detección de procesos y paneles (`EN USO`)** | `os.scandir('/proc')` + lectura de `comm`, `stat`, `environ` + UNIX socket `AF_UNIX` de Herdr (`~/.config/herdr/herdr.sock`). | Enumeración de procesos vía `CreateToolhelp32Snapshot` (`ctypes` sobre `kernel32.dll`) o `psutil` / WMI (`Win32_Process`) filtrando `agy-real.exe` / `agy.exe`; lectura de variables de entorno del proceso mediante `NtQueryInformationProcess` (PEB) o pasando `AGYC_ALIAS`/`HERDR_PANE_ID` en un registro local por PID en `%LOCALAPPDATA%\agyc\run\`. Para Herdr en Windows, abstraer el transporte IPC hacia **Named Pipe** (`\\.\pipe\herdr`) o socket TCP local `127.0.0.1` manteniendo el mismo protocolo JSON-RPC (`pane.list`, `pane.report_metadata`). |
| **Lectura no bloqueante de `stdin` (`agyc-statusline`)** | `os.set_blocking(fd, False)` + `select.select([fd], ...)` (en Windows `select.select` solo soporta sockets, no pipes de `stdin`). | Hilo lector daemon (`threading.Thread`) con `sys.stdin.buffer.read()` y `thread.join(timeout=0.020)`, o lectura Win32 `PeekNamedPipe` vía `ctypes.windll.kernel32` antes de `os.read`. |
| **Notificaciones Toast (`≤15%`)** | `herdr notification show --position top-right ...` vía `subprocess.Popen(..., start_new_session=True)`. | Si Herdr está disponible en Windows, mantener `herdr notification show`; como fallback nativo sin dependencias externas, emitir Windows Toast (`WinRT` `Windows.UI.Notifications`) o `System.Windows.Forms.NotifyIcon` vía `powershell.exe -NoProfile -ExecutionPolicy Bypass` en proceso desacoplado (`CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS`). |
| **Actualizador (`agyc update`)** | Manifiesto `manifests/linux_amd64.json`, extracción `.tar.gz`, `_verify_sha512`, `os.replace`. | Consultar `manifests/windows_amd64.json`, extraer `.zip` (`zipfile`), reutilizar `_verify_sha512()` y reemplazar `agy-real.exe` atómicamente (si `agy-real.exe` está en ejecución en otro panel, renombrar el binario antiguo a `.old` y limpiarlo en el siguiente arranque). |

### 6.1 Puntos ya portables vs capa `platform/` sugerida

- **100% portables hoy en `lib/agyc_core.py` (cero cambios de lógica):**
  `normalize_alias`, `validate_alias`, `extract_agy_alias`, `_scrub_secrets`, `sanitize_account_for_json`, `parse_iso_datetime`, `normalize_window`, `pct_display`, `default_max_tokens_for_model`, `estimate_context_from_transcript`, `compute_smart_auto_choice`, y las funciones puras de `fetch_quota_summary` / `extract_quota_metrics`.
- **A abstraer en `lib/platform/` (`linux.py` / `win32.py`):**
  1. `paths.py`: `resolve_real_home()`, `get_base_dir()`, `get_cache_dir()`, `ensure_private_dir()`, `ensure_private_file_permissions()`.
  2. `fs_links.py`: `create_dir_link(src, dst)` (`os.symlink` vs NTFS Junction) y `create_file_link(src, dst)`.
  3. `locking.py`: `acquire_file_lock(path, blocking=True)` (`fcntl.flock` vs `msvcrt.locking` / Win32 Mutex).
  4. `ipc_proc.py`: `scan_agy_processes()`, `query_herdr_ipc(method, params)` (`AF_UNIX` vs Named Pipe/TCP) y `read_stdin_nonblocking(timeout_sec)`.
  5. `notify.py`: `send_low_quota_toast(title, body)` y `spawn_detached(cmd)`.
