# Manual Completo de `agyc`
## Google Antigravity Multi-Account Switcher

> **Versión:** v1.5 | **Fecha:** Noviembre 2026
> **Motor soportado:** Google Antigravity CLI `1.5.10+` (binario nativo o Snap `antigravity-cli`)
> **Suscripciones soportadas:** Google AI Pro (`PRO`) y Google AI Ultra (`ULTRA`)
> **Plataforma:** Ubuntu Linux x86_64

---

## Índice

1. [¿Para qué sirve agyc?](#1-para-qué-sirve-agyc)
2. [Esquema Oficial de Cuotas en Google Antigravity 1.5.10](#2-esquema-oficial-de-cuotas-en-google-antigravity-1510)
3. [Instalación (`v1.5`)](#3-instalación-v15)
4. [Primeros pasos y panel de 6 columnas](#4-primeros-pasos-y-panel-de-6-columnas)
5. [Comandos de referencia](#5-comandos-de-referencia)
6. [Visualización de consumo en vivo: Pie y Barra Superior (Top Bar)](#6-visualización-de-consumo-en-vivo-pie-y-barra-superior-top-bar)
7. [Aislamiento de perfiles HOME](#7-aislamiento-de-perfiles-home)
8. [Uso en múltiples paneles (Herdr / tmux / zellij)](#8-uso-en-múltiples-paneles-herdr--tmux--zellij)
9. [Rotación inteligente de cuotas (`agyc auto`) y Estrategia Agotar y Rotar](#9-rotación-inteligente-de-cuotas-agyc-auto-y-estrategia-agotar-y-rotar)
10. [Gestión de tokens, elegibilidad y keyring](#10-gestión-de-tokens-elegibilidad-y-keyring)
11. [Skill para el agente de Antigravity](#11-skill-para-el-agente-de-antigravity)
12. [agyc wipe — Reinicio limpio](#12-agyc-wipe--reinicio-limpio)
13. [agyc update — Actualizador automático](#13-agyc-update--actualizador-automático)
14. [Historia de versiones y decisiones de diseño](#14-historia-de-versiones-y-decisiones-de-diseño)

---

## 1. ¿Para qué sirve agyc?

Google Antigravity CLI (`agy`) opera por defecto con una única sesión OAuth activa. Al trabajar a tiempo completo con modelos de razonamiento profundo (`Gemini 4 Carbon`, `Gemini 4 Argon`, `Claude Opus 5.5`, `Claude Sonnet 5.5`) o ejecutar enjambres de subagentes en paralelo, las ventanas de cuota de una sola cuenta se consumen rápidamente.

`agyc v1.5` transforma Antigravity en una estación de trabajo **multi-cuenta unificada**:

- Gestiona hasta **15 cuentas correlativas** (`agy01`..`agy15`), combinando cuentas **Google AI Pro (`PRO`)** y **Google AI Ultra (`ULTRA`)**.
- Aísla cada sesión en su propio **perfil `HOME` virtual** — múltiples paneles abiertos en paralelo jamás pisan el token de otro panel.
- Monitorea en tiempo real los **2 grupos unificados de cuotas** de Antigravity `1.5.10` tanto en tabla CLI como en vivo dentro del pie de `agy`, la **Barra Superior (Top Bar)** de ventana/panel y la barra global de **Herdr**.
- Conmuta automáticamente a la mejor cuenta elegible (`agyc auto`), filtrando exclusivamente cuentas `ULTRA` cuando se requiere `Gemini 4 Carbon`.

---

## 2. Esquema Oficial de Cuotas en Google Antigravity 1.5.10

### Niveles de suscripción (`PRO` vs `ULTRA`)

`agyc` detecta y muestra en la columna `PLAN` el nivel real de suscripción de cada cuenta de Google:

| Código | Suscripción | Capacidades en Antigravity 1.5.10 |
|---|---|---|
| **`PRO`** | **Google AI Pro** | Acceso a modelos `Gemini 4 Argon/Hydrogen`, `Gemini 3.8 Flash` y toda la familia `Claude & GPT` con techos estándar Pro. |
| **`ULTRA`** | **Google AI Ultra** | Techos de cuota extendidos + **acceso exclusivo a `Gemini 4 Carbon`** (y `Orchestrator` ejecutando Carbon). |

### Los 2 Grupos Unificados de Cuotas

A partir de Google Antigravity `1.5.10`, todas las cuotas de modelos se consolidan en **2 grupos unificados** por cuenta. Dentro de cada grupo, el uso de cualquiera de sus modelos descuenta de la misma bolsa de forma **proporcional al costo de tokens** del modelo elegido, sobre dos ventanas móviles compartidas:

- **Ventana de 5 Horas (`5H`):** Ventana móvil de corto plazo (se inicia con el primer consumo y se restablece 5 horas después; **no** es un corte diario fijo a medianoche).
- **Ventana Semanal (`Sem`):** Reserva móvil acumulada de 7 días (`168h`).

#### 1) Grupo `GEMINI` (Gemini Models)
Comparte un único par de medidores `5H` / `Sem` entre:
- **`Gemini 4 Carbon`** *(exclusivo para cuentas `ULTRA`)*
- **`Gemini 4 Argon`**
- **`Gemini 4 Hydrogen`**
- **`Orchestrator (Carbon/Argon)`**
- **`Gemini 3.8 Flash`**

#### 2) Grupo `CLAUDE & GPT` (Claude & GPT Models)
Comparte un único par de medidores `5H` / `Sem` entre:
- **`Claude Sonnet 4.6 / 5.5`**
- **`Claude Opus 4.6 / 5.5`**
- **`GPT-OSS 120B`**

### Interpretación de `Disponible` vs Contadores `(4h 25m)` / `(6d 23h)`

- **`100% Disponible`:** La cuenta conserva el 100% íntegro de esa ventana y aún no ha abierto un ciclo de reinicio por consumo reciente.
- **`82% (4h 25m)` / `91% (6d 23h)`:** Existe consumo activo en la ventana; el porcentaje refleja la **cuota restante disponible** y el contador entre paréntesis indica el tiempo exacto faltante para que esa ventana vuelva al 100%.

---

## 3. Instalación (`v1.5`)

### Requisitos

| Requisito | Versión recomendada |
|---|---|
| Ubuntu Linux | 20.04+ (x86_64) |
| Google Antigravity CLI | `1.5.10+` (binario nativo en `agy-real` o Snap) |
| Python | 3.10+ |
| Suscripción Google AI | Al menos 1 cuenta `Google AI Pro` o `Google AI Ultra` |

### Instalación automática desde el repositorio

```bash
git clone https://github.com/russbellc/agyc-antigravity-cli-switcher.git
cd agyc-antigravity-cli-switcher
chmod +x install.sh
./install.sh
source ~/.bashrc
```

### Qué realiza `install.sh` en `v1.5`

1. **Preservación segura del motor y del wrapper `agy`:** Si `~/.local/bin/agy` contiene el binario nativo ELF de Antigravity y aún no existe `~/.gemini/antigravity-cli/bin/agy-real`, lo respalda primero como `agy-real` y coloca el wrapper `bin/agy` en `~/.gemini/antigravity-cli/bin/agy` y `~/.local/bin/agy`.
2. **Instalación de herramientas de barra superior e inferior:**
   - Instala `agyc` y `agyc-statusline` en `~/.gemini/antigravity-cli/bin/` y `~/.local/bin/`.
   - Crea el symlink `agyc-titleline -> agyc-statusline` en **ambos** directorios de binarios (`~/.gemini/antigravity-cli/bin/` y `~/.local/bin/`).
   - Copia y enlaza `bin/agyc-topbar` en `~/.gemini/antigravity-cli/bin/` y `~/.local/bin/`.
3. **Configuración automática de `settings.json`:** Activa tanto `"statusLine"` (`agyc-statusline`) como `"title"` (`agyc-titleline`) en `~/.gemini/antigravity-cli/settings.json` y en los perfiles existentes.
4. **Lanzadores `agy01..agy15` y Skill:** Genera los 15 accesos directos, configura `PATH` + `SSH_TTY` e instala `skills/agyc/SKILL.md`.

### Instalación manual equivalente

```bash
mkdir -p ~/.gemini/antigravity-cli/bin ~/.local/bin ~/.agyc_homes

# Copiar binarios principales
cp -f bin/agyc bin/agy bin/agyc-statusline ~/.gemini/antigravity-cli/bin/
[ -f bin/agyc-topbar ] && cp -f bin/agyc-topbar ~/.gemini/antigravity-cli/bin/
chmod +x ~/.gemini/antigravity-cli/bin/agyc \
         ~/.gemini/antigravity-cli/bin/agy \
         ~/.gemini/antigravity-cli/bin/agyc-statusline
[ -f ~/.gemini/antigravity-cli/bin/agyc-topbar ] && chmod +x ~/.gemini/antigravity-cli/bin/agyc-topbar

# Enlaces en ~/.local/bin y symlinks agyc-titleline -> agyc-statusline
ln -sf ~/.gemini/antigravity-cli/bin/agyc ~/.local/bin/agyc
ln -sf ~/.gemini/antigravity-cli/bin/agy ~/.local/bin/agy
ln -sf ~/.gemini/antigravity-cli/bin/agyc-statusline ~/.local/bin/agyc-statusline
ln -sf agyc-statusline ~/.gemini/antigravity-cli/bin/agyc-titleline
ln -sf agyc-statusline ~/.local/bin/agyc-titleline
[ -f ~/.gemini/antigravity-cli/bin/agyc-topbar ] && \
    ln -sf ~/.gemini/antigravity-cli/bin/agyc-topbar ~/.local/bin/agyc-topbar

# Lanzadores agy01..agy15
for i in $(seq -w 1 15); do
    ln -sf ~/.gemini/antigravity-cli/bin/agyc ~/.local/bin/agy${i}
done
```

---

## 4. Primeros pasos y Panel de 6 Columnas

### Registrar cuentas

```bash
agyc add      # primera cuenta → agy01 (abre navegador para OAuth)
agyc add      # segunda cuenta → agy02
agyc add      # tercera cuenta → agy03
```

### Consultar estado unificado (`agyc` / `agyc list`)

```bash
agyc
```

Salida del nuevo diseño compacto de 6 columnas en `v1.5`:

```text
PANEL DE CUENTAS DE GOOGLE AI PRO & ULTRA (ANTIGRAVITY 1.5.10 / AGYC v1.5)

┌──────────┬──────────────────────┬───────┬─────────────┬───────────────────────────────────┬───────────────────────────────────┐
│ ALIAS    │ CUENTA / EMAIL       │ PLAN  │ ESTADO      │ GEMINI (5H / SEMANAL)             │ CLAUDE & GPT (5H / SEMANAL)       │
├──────────┼──────────────────────┼───────┼─────────────┼───────────────────────────────────┼───────────────────────────────────┤
│ * agy01  │ dev1@gmail.com       │ ULTRA │ *ACTIVA+DEF │ 5H:  [████████░░]  82% (4h 25m)   │ 5H:  [██████████] 100% Disponible │
│          │                      │       │             │ Sem: [█████████░]  91% (6d 23h)   │ Sem: [████████░░]  78% (6d 23h)   │
├──────────┼──────────────────────┼───────┼─────────────┼───────────────────────────────────┼───────────────────────────────────┤
│   agy02  │ dev2@gmail.com       │ PRO   │   LISTA     │ 5H:  [██████████] 100% Disponible │ 5H:  [██████░░░░]  60% (4h 25m)   │
│          │                      │       │             │ Sem: [██████████] 100% Disponible │ Sem: [█████░░░░░]  50% (6d 23h)   │
├──────────┼──────────────────────┼───────┼─────────────┼───────────────────────────────────┼───────────────────────────────────┤
│   agy03  │ dev3@gmail.com       │ PRO   │   LISTA     │ 5H:  [███████░░░]  70% (3h 10m)   │ 5H:  [░░░░░░░░░░]   0% (1h 45m)   │
│          │                      │       │             │ Sem: [████████░░]  84% (5d 12h)   │ Sem: [██░░░░░░░░]  20% (4d 08h)   │
└──────────┴──────────────────────┴───────┴─────────────┴───────────────────────────────────┴───────────────────────────────────┘
```

### Entrar directamente a Antigravity

```bash
agy01    # abre Antigravity aislado en ~/.agyc_homes/agy01 (dev1@gmail.com - ULTRA)
agy02    # abre Antigravity aislado en ~/.agyc_homes/agy02 (dev2@gmail.com - PRO)
agy03    # abre Antigravity aislado en ~/.agyc_homes/agy03 (dev3@gmail.com - PRO)
```

---

## 5. Comandos de Referencia

### Lanzadores directos

```bash
agy01                      # Entra directo a agy01 con --dangerously-skip-permissions
agy02                      # Entra directo a agy02
# ... hasta agy15
agy                        # Entra con la cuenta activa/default usando el wrapper preservado
```

### Gestión y consulta de cuentas

```bash
agyc                       # Panel compacto de 6 columnas (por defecto)
agyc list                  # Equivalente a agyc
agyc list -r               # Refresca cuotas y planes en vivo desde Google (--refresh)
agyc list --json           # Salida JSON estructurada con plan y ambos grupos de cuota
agyc add                   # Registra nueva cuenta correlativa (PRO o ULTRA)
agyc add agy04             # Registra o sobrescribe un alias específico
agyc renew agy03           # Re-vincula OAuth cuando Google pide re-autenticación
agyc reauth agy03          # Alias de renew
agyc rm agy03              # Elimina una cuenta y limpia su perfil aislado
agyc wipe                  # Vacía TODAS las credenciales registradas (con confirmación)
agyc wipe --force          # Limpieza total no interactiva (-y)
```

### Selección y rotación de cuentas

```bash
agyc switch agy02          # Cambia la cuenta activa global sin abrir la TUI
agyc agy02                 # Alias abreviado de switch
agyc default agy01         # Define la cuenta predeterminada para inicios con 'agy'
agyc quota                 # Reporte detallado de modelos y timestamps de reinicio (cuenta activa)
agyc quota agy01           # Reporte detallado de una cuenta específica
agyc auto                  # Rota automáticamente según el modelo activo en settings.json
agyc auto gemini           # Fuerza evaluación sobre el grupo unificado Gemini (PRO + ULTRA)
agyc auto claude           # Fuerza evaluación sobre el grupo unificado Claude & GPT (PRO + ULTRA)
agyc auto carbon           # Filtra EXCLUSIVAMENTE cuentas ULTRA con mayor cuota Gemini/Carbon
agyc auto ultra            # Alias equivalente a 'agyc auto carbon' (solo cuentas ULTRA)
```

### Actualización del ecosistema

```bash
agyc update                # Sincroniza repo, binarios, statusline/titleline/topbar y motor agy
agy update                 # Interceptado por el wrapper bin/agy → delega a agyc update
```

---

## 6. Visualización de Consumo en Vivo: Pie y Barra Superior (Top Bar)

`agyc v1.5` integra monitoreo continuo de consumo sin tener que salir de Antigravity ni ejecutar comandos manuales, cubriendo tanto el **pie de terminal** como la **Barra Superior (Top Bar)**.

### 6.1 Pie de `agy` (`agyc-statusline`)

Configurado en `~/.gemini/antigravity-cli/settings.json` bajo la clave `"statusLine"`:

```json
"statusLine": {
  "type": "command",
  "command": "agyc-statusline",
  "enabled": true
}
```

Renderiza en la parte inferior de la sesión interactiva de `agy`:
- Alias activo y badge de suscripción (`agy01 ULTRA` / `agy02 PRO`).
- Rama Git actual del proyecto (lectura directa ultrarrápida desde `.git/HEAD`).
- Modelo activo y nivel de esfuerzo (`Gemini 4 Carbon (High)`, `Claude Sonnet 5.5`, etc.).
- Barra de progreso coloreada y cuenta regresiva (`5H` y `Sem`) del grupo de cuota correspondiente al modelo en curso.
- Consumo de ventana de contexto de la conversación (`Ctx` con barra de color invertida: verde <50%, amarillo <75%, naranja <85%, rojo ≥85%).

### 6.2 Barra Superior (Top Bar) en `agy` y Metadatos por Panel en Herdr (`agyc-titleline` + `pane.report_metadata`)

Antigravity CLI `1.5.10` soporta un generador dinámico de título de terminal mediante la clave `"title"` en `settings.json` (controlable también con el slash command `/title on` y `/title off`).

`install.sh` crea el enlace simbólico `agyc-titleline -> agyc-statusline` en `~/.gemini/antigravity-cli/bin/` y `~/.local/bin/`, y preconfigura `settings.json`:

```json
"title": {
  "type": "command",
  "command": "agyc-titleline",
  "enabled": true
}
```

De forma combinada:
- Cuando `agy` invoca `agyc-titleline` (o `agyc-statusline --title`), emite la línea OSC de texto limpio para la **Barra Superior de la ventana / pestaña** con alias, plan, modelo y porcentaje `5H`/`Sem`.
- En **Herdr**, `agyc-statusline` sincroniza además los **metadatos dinámicos de cada panel** (`pane.report_metadata`), permitiendo identificar de un vistazo qué cuenta (`agy01 ULTRA`, `agy02 PRO`, etc.) y cuánto saldo queda en cada panel dividido sin cambiar el foco.

### 6.3 Barra Superior Derecha Global en Herdr (`agyc-topbar`)

Además de los metadatos individuales por panel, `agyc v1.5` incluye el widget ultraligero **`agyc-topbar`** (<20ms, sin bloqueo, instalado en `~/.local/bin/agyc-topbar` y `~/.gemini/antigravity-cli/bin/agyc-topbar`) diseñado para la zona derecha de la barra global de pestañas de Herdr (`ui.tab_bar_right`). Detecta automáticamente la cuenta activa del panel enfocado (o de la pestaña actual / cuenta activa por defecto) y renderiza en vivo las cuotas `5H` y `Sem` de Gemini y Claude.

Para activarlo en `~/.config/herdr/config.toml`:

```toml
[[ui.tab_bar_right]]
type = "command"
command = "agyc-topbar"
interval_seconds = 5
timeout_seconds = 2
```

De esta forma, la esquina superior derecha de Herdr muestra permanentemente el resumen consolidado de la cuenta activa, su plan (`PRO`/`ULTRA`) y los porcentajes `5H`/`Sem` de los 2 grupos unificados incluso cuando estás trabajando en un panel de código, logs o terminal Bash fuera de `agy`.

---

## 7. Aislamiento de Perfiles HOME

### El problema en entornos multi-panel

El binario nativo de Antigravity lee y refresca su credencial OAuth en:

```text
$HOME/.gemini/antigravity-cli/antigravity-oauth-token
```

Si dos paneles compartieran el mismo `$HOME`, cambiar de cuenta en un panel sobrescribiría el token en caliente del otro.

### Solución: `prepare_isolated_home(alias)`

Antes de invocar `os.execv()` hacia `agy-real`, `agyc` construye un directorio `HOME` aislado por alias:

```python
if alias:
    isolated_home = prepare_isolated_home(alias)
    os.environ["HOME"] = isolated_home  # ej. ~/.agyc_homes/agy01

os.execv(real_agy, cmd_args)
```

### Mapa de archivos aislados vs. compartidos

```text
~/.agyc_homes/
├── agy01/.gemini/antigravity-cli/
│   ├── antigravity-oauth-token   ← 🔒 Copia exclusiva (0600) — dev1@gmail.com (ULTRA)
│   ├── bin/                      ← 🔗 Symlink → ~/.gemini/antigravity-cli/bin
│   ├── settings.json             ← 🔗 Symlink → ~/.gemini/antigravity-cli/settings.json
│   ├── accounts/                 ← 🔗 Symlink → ~/.gemini/antigravity-cli/accounts/
│   ├── conversations/            ← 🔗 Symlink → historial compartido
│   └── brain/                    ← 🔗 Symlink → artefactos y contexto compartido
├── agy02/.gemini/antigravity-cli/
│   ├── antigravity-oauth-token   ← 🔒 Copia exclusiva (0600) — dev2@gmail.com (PRO)
│   └── ...
└── agy03/.gemini/antigravity-cli/
    ├── antigravity-oauth-token   ← 🔒 Copia exclusiva (0600) — dev3@gmail.com (PRO)
    └── ...
```

| Recurso | Tipo | Propósito |
|---|---|---|
| `antigravity-oauth-token` | 🔒 **Archivo exclusivo por alias** | Blindaje total de credenciales OAuth entre paneles paralelos |
| `settings.json` | 🔗 Symlink compartido | Mantiene `statusLine`, `title` y preferencias sincronizadas |
| `bin/` | 🔗 Symlink compartido | Acceso unificado a `agy-real`, `agy`, `agyc`, `agyc-statusline`, `agyc-titleline`, `agyc-topbar` |
| `accounts/` | 🔗 Symlink compartido | `agyc list` y `agyc-topbar` leen el estado real desde cualquier panel |
| `conversations/` y `brain/` | 🔗 Symlink compartido | Permite retomar (`/resume`) cualquier sesión desde otra cuenta tras rotar |

---

## 8. Uso en Múltiples Paneles (Herdr / tmux / zellij)

### Distribución recomendada combinando `ULTRA` y `PRO`

```text
Herdr (Top Bar derecha: agyc-topbar)
├── Tab Backend
│   ├── Panel Principal → agy01 (ULTRA - dev1@gmail.com) → Arquitectura crítica con Gemini 4 Carbon
│   ├── Panel Monitor   → dev-monitor
│   └── Panel Soporte   → agy02 (PRO   - dev2@gmail.com) → Implementación con Claude Sonnet 5.5
└── Tab Frontend
    ├── Panel Principal → agy03 (PRO   - dev3@gmail.com) → UI/Tests con Gemini 4 Argon / 3.8 Flash
    └── Panel Logs      → npm run dev / playwright
```

Cada panel conserva su propio `HOME` aislado y reporta su propio título dinámico (`agyc-titleline`) al encabezado del panel en Herdr. Y gracias a que `conversations/` y `brain/` están enlazados al directorio común, si una cuenta agota su ventana `5H` puedes cerrar `agy02`, abrir `agy03` y ejecutar `/resume` para continuar exactamente en la misma conversación.

---

## 9. Rotación Inteligente de Cuotas (`agyc auto`) y Estrategia Agotar y Rotar

### Modos de evaluación en `agyc auto [gemini|claude|carbon|ultra]`

`agyc auto` inspecciona todas las cuentas no revocadas y calcula un puntaje ponderado según el modo indicado (o autodetectado leyendo `"model"` en `settings.json`):

1. **Modo `carbon` o `ultra`** (`agyc auto carbon` / `agyc auto ultra`, o automático cuando el modelo activo en `settings.json` es **`Gemini 4 Carbon`**):
   - **Filtro estricto de plan:** Descarta todas las cuentas `PRO` y evalúa **exclusivamente cuentas `ULTRA`** (`Google AI Ultra`).
   - **Puntaje:** `score = (gemini_semanal × 0.7) + (gemini_5h × 0.3)` sobre el grupo unificado Gemini.
   - Si ninguna cuenta `ULTRA` tiene saldo disponible, informa qué cuenta `ULTRA` se recuperará primero sin degradar silenciosamente a una cuenta `PRO` incompatible con Carbon.

2. **Modo `claude`** (`agyc auto claude`, o automático con `Claude Sonnet 4.6/5.5`, `Claude Opus 4.6/5.5` o `GPT-OSS 120B`):
   - **Filtro:** Evalúa cuentas `PRO` y `ULTRA` válidas.
   - **Puntaje:** `score = (claude_semanal × 0.7) + (claude_5h × 0.3)` priorizando preservar reserva semanal de Claude & GPT.

3. **Modo `gemini`** (`agyc auto gemini`, o automático con `Gemini 4 Argon`, `Gemini 4 Hydrogen`, `Orchestrator` estándar o `Gemini 3.8 Flash`):
   - **Filtro:** Evalúa cuentas `PRO` y `ULTRA` válidas.
   - **Puntaje:** Prioriza disponibilidad en la ventana móvil `5H` y utiliza la ventana semanal (`Sem`) como criterio de desempate.

### Estrategia recomendada: Agotar y Rotar

```text
agy02 (100% Disponible) ──► trabajar hasta ~15-20% ──► agyc auto ──► agy03 (100% Disponible)
         │
         └── su ventana móvil 5H corre en segundo plano (4h 25m → 0m → vuelve a 100% Disponible)
```

- **Activa temprano la ventana móvil `5H`** de una cuenta y trabájala de corrido hasta ~15-20% antes de saltar a la siguiente: así el temporizador de 5 horas ya está corriendo mientras consumes otra cuenta.
- **Reserva las cuentas `ULTRA`** para sesiones de `Gemini 4 Carbon` / `Orchestrator (Carbon)` cuando también dispongas de cuentas `PRO` para tareas cotidianas con `Argon`, `3.8 Flash` o `Sonnet`.

---

## 10. Gestión de Tokens, Elegibilidad y Keyring

### Token expirado o revocado (`invalid_grant`)

```bash
agyc renew agy03   # abre el navegador forzando selección de cuenta y renueva el token OAuth
```

### Verificación de elegibilidad (`Eligibility check failed`)

Si Google solicita confirmar elegibilidad o términos al estrenar una cuenta:

```bash
agyc renew agy03
```

### Almacenamiento basado en archivo (Bypass de GNOME Keyring)

`agyc` y el wrapper `bin/agy` aseguran `SSH_TTY="${SSH_TTY:-/dev/pts/0}"` para que Antigravity lea siempre `antigravity-oauth-token` desde el `HOME` correspondiente sin bloquearse esperando prompts gráficos de GNOME Keyring o D-Bus.

---

## 11. Skill para el Agente de Antigravity

El archivo `skills/agyc/SKILL.md` instruye a los agentes de IA sobre cómo operar `agyc v1.5`:

- Interpretar la tabla de 6 columnas (`PLAN` `PRO`/`ULTRA` y los 2 grupos unificados `GEMINI` y `CLAUDE & GPT`), recordando que `5H` es una ventana móvil de 5 horas y no una cuota diaria.
- Usar `agyc auto [gemini|claude|carbon|ultra]` sabiendo que `carbon`/`ultra` filtra exclusivamente cuentas `ULTRA`.
- Conocer la arquitectura de telemetría en vivo (`agyc-statusline`, `agyc-titleline` y `agyc-topbar`).

Instalación manual del skill si fuera necesario:

```bash
mkdir -p ~/proyectos/.agents/skills/agyc
cp -f skills/agyc/SKILL.md ~/proyectos/.agents/skills/agyc/SKILL.md
```

---

## 12. `agyc wipe` — Reinicio Limpio

Purga de forma segura todas las credenciales registradas para empezar desde cero:

```bash
agyc wipe          # solicita confirmación interactiva
agyc wipe --force  # ejecución directa sin confirmación (-y)
```

- **Elimina:** `accounts/*.json`, `antigravity-oauth-token` principal y tokens aislados en `~/.agyc_homes/*`.
- **Conserva intactos:** `settings.json` (`statusLine` y `title`), `conversations/`, `brain/` y `projects/`.

---

## 13. `agyc update` — Actualizador Automático

Mantiene al día todo el ecosistema `agyc` y el binario oficial de Antigravity:

```bash
agyc update      # actualiza repositorio, binarios, barras y motor Antigravity
agy update       # atajo interceptado por el wrapper ~/.local/bin/agy
```

### Fases de actualización

1. **Sincronización con GitHub:** Ejecuta `git pull` en el repositorio local (o descarga directa si se instaló sin Git).
2. **Sincronización de Binarios y Wrappers:** Actualiza `agyc`, preserva el wrapper `bin/agy` en `~/.gemini/antigravity-cli/bin/agy` y `~/.local/bin/agy`, sincroniza `agyc-statusline`, mantiene el symlink `agyc-titleline -> agyc-statusline`, copia `agyc-topbar` y regenera los lanzadores `agy01..agy15`.
3. **Motor Oficial Google Antigravity CLI:** Verifica la versión de `~/.gemini/antigravity-cli/bin/agy-real` contra el manifiesto oficial de releases de Google Antigravity (`1.5.10+`) y actualiza `agy-real` sin sobrescribir el wrapper `~/.local/bin/agy`.
4. **Mantenimiento de Perfiles y `settings.json`:** Sincroniza symlinks en `~/.agyc_homes/*` y verifica que `"statusLine"` y `"title"` sigan activos.

---

## 14. Historia de Versiones y Decisiones de Diseño

### v1.0 — MVP (Oct 13, 2026)
- **Funcionalidades:** `switch`, lanzadores directos `agy01..15`, tabla inicial de cuotas y flujo OAuth local.
- **Decisión clave:** Uso de `os.execv()` en lugar de subprocesos envolventes para preservar señales, colores y redimensionado nativo de la TUI de `agy`.

### v1.1 — Rotación Inteligente (Oct 14, 2026)
- **Funcionalidades:** `agyc auto`, puntaje ponderado y autodetección de modelo desde `settings.json`, más bypass automático de keyring vía `SSH_TTY`.

### v1.2 — Renovación OAuth y Limpieza (Oct 15, 2026)
- **Funcionalidades:** `agyc renew` / `reauth` y `agyc wipe`. Corrección definitiva tras verificar que el binario de Antigravity resuelve `.gemini` desde `$HOME` y no desde `SNAP_USER_COMMON`.

### v1.3 — Aislamiento Real de Perfiles `HOME` (Oct 15, 2026)
- **Funcionalidad central:** `prepare_isolated_home(alias)` inyectando `os.environ["HOME"]` por panel con token exclusivo (`0600`) y symlinks compartidos para conversaciones, `settings.json` y cuentas.

### v1.4 — Soporte Preliminar Gemini 4 Argon y Actualizador (Oct 16, 2026)
- **Funcionalidades:** Columna dedicada temporal para el despliegue inicial de Gemini 4 Argon, comando `agyc update` y wrapper `bin/agy`.

### v1.5 — Esquema Oficial Antigravity 1.5.10, Planes PRO/ULTRA y Top Bar en Vivo (Nov 2026)
- **Soporte completo `PRO` y `ULTRA`:** Detección del plan de suscripción (**Google AI Pro** vs **Google AI Ultra**) con columna dedicada `PLAN` en `agyc list` y soporte para modelos exclusivos Ultra (`Gemini 4 Carbon`).
- **Unificación en 2 grupos oficiales de cuotas:** Alineación con Google Antigravity `1.5.10` consolidando el consumo proporcional en **Gemini Models** (`Gemini 4 Carbon`, `Argon`, `Hydrogen`, `Orchestrator`, `Gemini 3.8 Flash`) y **Claude & GPT Models** (`Claude Sonnet 4.6/5.5`, `Claude Opus 4.6/5.5`, `GPT-OSS 120B`) bajo ventanas compartidas `5H` y `Sem`.
- **Tabla compacta de 6 columnas:** Sustitución de contadores ficticios sin gasto por el estado explícito `Disponible` al 100%, mostrando contadores reales `(4h 25m)` / `(6d 23h)` únicamente cuando hay ventana activa.
- **Rotación selectiva `ULTRA` (`agyc auto [gemini|claude|carbon|ultra]`):** Filtrado estricto de cuentas `ULTRA` cuando se solicita `carbon`/`ultra` o cuando el modelo activo en `settings.json` es `Gemini 4 Carbon`.
- **Ecosistema completo de Telemetría Superior e Inferior:** Incorporación de `agyc-titleline` (symlink a `agyc-statusline` en `"title"` de `settings.json` para Top Bar de `agy` y metadatos dinámicos por panel en Herdr) y `agyc-topbar` (widget global para `ui.tab_bar_right` en Herdr), preservando siempre el wrapper `bin/agy` en `~/.local/bin/agy`.
