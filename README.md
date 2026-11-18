# agyc — Google Antigravity Multi-Account Switcher (v1.5)

> **Administrador multi-cuenta para Google Antigravity CLI 1.5.10+ en Ubuntu Linux**
> Soporte Google AI Pro (`PRO`) & Google AI Ultra (`ULTRA`) | Cuotas unificadas en vivo (Pie + Top Bar) | Perfiles HOME aislados

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version: v1.5](https://img.shields.io/badge/Version-v1.5-brightgreen.svg)](#historia-de-versiones)
[![Platform: Ubuntu](https://img.shields.io/badge/Platform-Ubuntu%20Linux-orange.svg)](https://ubuntu.com)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![Antigravity: 1.5.10+](https://img.shields.io/badge/Google%20Antigravity-1.5.10%2B-red.svg)](https://antigravity.google/docs/cli/reference)

---

## ¿Qué es agyc?

`agyc` convierte Google Antigravity CLI (`agy`) en una estación de trabajo **multi-cuenta de alto rendimiento**. Nació para resolver un cuello de botella real: al programar a tiempo completo con modelos intensivos como `Gemini 4 Carbon`, `Claude Opus 5.5` o `Claude Sonnet 5.5`, las cuotas de una sola suscripción se agotan en mitad de la jornada.

**La solución:** gestionar hasta **15 cuentas (`agy01`..`agy15`)** combinando suscripciones **Google AI Pro (`PRO`)** y **Google AI Ultra (`ULTRA`)** con perfiles `HOME` completamente aislados, telemetría en vivo en barra inferior y superior, y rotación inteligente para trabajar en **múltiples paneles en paralelo** sin colisiones de tokens.

---

## Características Principales (v1.5)

- 💎 **Soporte Google AI Pro (`PRO`) & Google AI Ultra (`ULTRA`)** — Identificación automática del nivel de suscripción por cuenta y filtrado exclusivo de cuentas `ULTRA` para modelos restringidos como `Gemini 4 Carbon`.
- 📊 **2 Grupos Unificados de Cuotas (Antigravity 1.5.10)** — Panel compacto de 6 columnas alineado al esquema oficial de consumo proporcional en ventanas móviles de **5 Horas (`5H`)** y **Semanal (`Sem`)**: **Gemini Models** y **Claude & GPT Models**.
- 🖥️ **Telemetría en Vivo (Pie + Top Bar + Herdr)** — Visualización simultánea en el pie de `agy` (`agyc-statusline`), en la **Barra Superior / título dinámico por panel** (`agyc-titleline` vía `"title"` en `settings.json`) y en la esquina superior derecha global de Herdr (`agyc-topbar` en `ui.tab_bar_right`).
- 🔒 **Perfiles HOME aislados** — Cada cuenta opera con su propio `antigravity-oauth-token` blindado en `~/.agyc_homes/<alias>/`. Dos paneles con cuentas distintas nunca compiten por el mismo token.
- ⚡ **Lanzadores directos** — Escribe `agy01`, `agy02`... hasta `agy15` para entrar directo con `--dangerously-skip-permissions` sin menús ni fricción.
- 🔄 **Rotación inteligente (`agyc auto`)** — Detecta el modelo activo (`gemini`, `claude`, `carbon`/`ultra`) y conmuta a la cuenta elegible con mayor saldo ponderado.
- 🚀 **Actualizador integrado** — `agyc update` (o `agy update`) sincroniza binarios, wrappers, barras de estado y motor oficial de Antigravity CLI.
- 🔑 **Sin keyring** — Autenticación basada en archivo (`SSH_TTY`), sin bloqueos de GNOME Keyring ni D-Bus.
- 🤖 **Skill para agentes** — Permite al agente consultar saldos, distinguir planes `PRO`/`ULTRA` y rotar cuentas bajo política autorizada.

---

## Esquema Unificado de Cuotas (Google Antigravity 1.5.10)

En Antigravity `1.5.10`, Google unifica el consumo en **2 bolsas globales de cuota** por cuenta. Dentro de cada grupo, todos sus modelos comparten la misma ventana móvil de **5 Horas (`5H`)** y la misma reserva **Semanal (`Sem`, 168h)**, descontando saldo de forma **proporcional al costo de tokens** de cada modelo:

| Grupo de Cuota | Modelos Incluidos | Ventanas Compartidas | Disponibilidad por Plan |
|---|---|---|---|
| **1. Gemini Models** | • `Gemini 4 Carbon` *(exclusivo Ultra)*<br>• `Gemini 4 Argon`<br>• `Gemini 4 Hydrogen`<br>• `Orchestrator (Carbon/Argon)`<br>• `Gemini 3.8 Flash` | Móvil **5H** + **Semanal** | `PRO` y `ULTRA`<br>*(Carbon requiere `ULTRA`)* |
| **2. Claude & GPT Models** | • `Claude Sonnet 4.6 / 5.5`<br>• `Claude Opus 4.6 / 5.5`<br>• `GPT-OSS 120B` | Móvil **5H** + **Semanal** | `PRO` y `ULTRA` |

> **Nota importante sobre las ventanas:** La ventana `5H` es una **ventana móvil de 5 horas** desde el primer consumo activo (no un reinicio fijo diario). Cuando una ventana no registra gasto activo (100% íntegro), `agyc` muestra **`Disponible`**; en cuanto inicia el consumo, muestra el tiempo real restante para el reinicio, por ejemplo `(4h 25m)` o `(6d 23h)`.

---

## Instalación Rápida

```bash
git clone https://github.com/russbellc/agyc-antigravity-cli-switcher.git
cd agyc-antigravity-cli-switcher
chmod +x install.sh
./install.sh
```

Luego recargar el shell:

```bash
source ~/.bashrc
```

El instalador `v1.5` configura automáticamente:
- `agyc`, el wrapper preservado `agy` (`~/.local/bin/agy` → `agy-real`), `agyc-statusline`, el symlink `agyc-titleline -> agyc-statusline` y `agyc-topbar` tanto en `~/.gemini/antigravity-cli/bin/` como en `~/.local/bin/`.
- Lanzadores directos `agy01`..`agy15`.
- Bloques `"statusLine"` (`agyc-statusline`) y `"title"` (`agyc-titleline`) activos en `~/.gemini/antigravity-cli/settings.json`.

### Requisitos

- Ubuntu Linux (x86_64)
- [Google Antigravity CLI](https://antigravity.google/docs/cli/reference) `1.5.10+` (binario nativo o snap)
- Python 3.10+
- Al menos 1 cuenta de [Google AI Pro o Google AI Ultra](https://one.google.com/about/plans)

---

## Uso

### Registrar tus cuentas (`PRO` o `ULTRA`)

```bash
agyc add      # abre el navegador para OAuth → guarda como agy01 (detecta PRO / ULTRA)
agyc add      # segunda cuenta → guarda como agy02
agyc add      # tercera cuenta → guarda como agy03
```

### Entrar a Antigravity

```bash
agy01         # entra con dev1@gmail.com (perfil aislado ~/.agyc_homes/agy01)
agy02         # entra con dev2@gmail.com (perfil aislado ~/.agyc_homes/agy02)
agy03         # entra con dev3@gmail.com (perfil aislado ~/.agyc_homes/agy03)
```

### Ver estado unificado de cuotas (`agyc` / `agyc list`)

```bash
agyc          # tabla compacta de 6 columnas con plan y barras unificadas
agyc list -r  # fuerza refresco en vivo desde los servidores de Google
```

Ejemplo de salida en `v1.5`:

```text
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

### Rotación automática inteligente (`agyc auto`)

```bash
agyc auto         # detecta el modelo activo en settings.json (Gemini, Claude o Carbon)
agyc auto gemini  # evalúa el grupo unificado Gemini en cuentas PRO y ULTRA
agyc auto claude  # evalúa el grupo unificado Claude & GPT en cuentas PRO y ULTRA
agyc auto carbon  # filtra EXCLUSIVAMENTE cuentas ULTRA con mejor cuota Gemini/Carbon
agyc auto ultra   # alias de 'carbon': rota únicamente entre cuentas Google AI Ultra
```

> **Filtrado exclusivo `ULTRA`:** Cuando ejecutas `agyc auto carbon` / `agyc auto ultra` —o ejecutas `agyc auto` sin argumentos teniendo `Gemini 4 Carbon` como modelo activo—, `agyc` descarta automáticamente las cuentas `PRO` y selecciona únicamente entre cuentas **`ULTRA`** válidas.

---

## Visualización en Vivo: Pie (`statusLine`) y Barra Superior (`Top Bar`)

`agyc v1.5` ofrece monitoreo de consumo en tiempo real en **tres superficies complementarias**:

### 1. Pie de terminal en `agy` y metadatos en Herdr (`agyc-statusline`)
Muestra al pie del prompt de Antigravity la cuenta activa, plan (`ULTRA`/`PRO`), rama Git, modelo + nivel de esfuerzo, cuota en vivo (`5H` / `Sem`) del grupo activo y uso de ventana de contexto (`Ctx`), además de sincronizar metadatos dinámicos por panel en Herdr (`pane.report_metadata`).

### 2. Barra Superior de `agy` (`agyc-titleline`)
Mediante el symlink `agyc-titleline -> agyc-statusline` configurado en el bloque `"title"` de `~/.gemini/antigravity-cli/settings.json` (activable/desactivable en caliente con `/title on` o `/title off`), Antigravity `1.5.10` emite dinámicamente la línea OSC de título compacto (cuenta, plan, modelo y cuota) a la **Barra Superior de la ventana / pestaña**.

Configuración inyectada automáticamente por `install.sh` en `settings.json`:

```json
{
  "statusLine": {
    "type": "command",
    "command": "agyc-statusline",
    "enabled": true
  },
  "title": {
    "type": "command",
    "command": "agyc-titleline",
    "enabled": true
  }
}
```

### 3. Barra Superior Global en Herdr (`agyc-topbar`)
Para visualizar el pulso en vivo (<20ms, sin bloqueo) de la cuenta enfocada en el extremo derecho de la barra global de pestañas de **Herdr** (`ui.tab_bar_right`), añade en `~/.config/herdr/config.toml`:

```toml
[[ui.tab_bar_right]]
type = "command"
command = "agyc-topbar"
interval_seconds = 5
timeout_seconds = 2
```

Así dispones simultáneamente de:
- **Metadatos dinámicos por panel** (qué `agyXX` + plan + saldo corre en cada panel dividido).
- **Widget global superior derecho** (`agyc-topbar` en `ui.tab_bar_right`).
- **Barra detallada inferior** (`agyc-statusline` dentro de cada TUI de `agy`).

---

## Flujo en Múltiples Paneles (Herdr / tmux / zellij)

Con el aislamiento de perfiles cada panel trabaja de forma completamente independiente:

```text
Panel 1 → agy01   (HOME=~/.agyc_homes/agy01, ULTRA: dev1@gmail.com → Gemini 4 Carbon)
Panel 2 → agy02   (HOME=~/.agyc_homes/agy02, PRO:   dev2@gmail.com → Claude Sonnet 5.5)
Panel 3 → agy03   (HOME=~/.agyc_homes/agy03, PRO:   dev3@gmail.com → Gemini 4 Argon)
                   ← tokens blindados por panel, cero colisiones ✅
```

---

## Comandos Disponibles

| Comando | Descripción |
|---|---|
| `agyc` / `agyc list` | Tabla compacta de 6 columnas (`PLAN`, `GEMINI`, `CLAUDE & GPT`) |
| `agyc list -r` / `--refresh` | Fuerza refresco en vivo de cuotas y plan desde Google |
| `agyc list --json` | Salida estructurada JSON para scripts y agentes |
| `agy01` .. `agy15` | Entra directo a esa cuenta con perfil `HOME` aislado |
| `agyc add [alias]` | Registra una nueva cuenta `PRO` o `ULTRA` (OAuth en navegador) |
| `agyc renew <alias>` | Re-vincula una cuenta cuando Google solicita re-autenticación |
| `agyc auto` | Rota a la mejor cuenta según el modelo activo en `settings.json` |
| `agyc auto gemini` | Rota priorizando el grupo unificado **Gemini Models** |
| `agyc auto claude` | Rota priorizando el grupo unificado **Claude & GPT Models** |
| `agyc auto carbon` / `ultra` | Rota filtrando **exclusivamente cuentas `ULTRA`** |
| `agyc update` / `agy update` | Actualiza `agyc`, barras (`statusline`/`titleline`/`topbar`) y motor `agy` |
| `agyc switch <alias>` | Cambia la cuenta activa global sin lanzar Antigravity |
| `agyc default <alias>` | Fija la cuenta predeterminada para `agy` |
| `agyc quota [alias]` | Desglose detallado por modelo y hora exacta de reinicio |
| `agyc rm <alias>` | Elimina una cuenta registrada y limpia su perfil |
| `agyc wipe` | Purga todas las credenciales registradas (con confirmación) |

---

## Arquitectura

### Aislamiento de perfiles `HOME`

El binario nativo de Antigravity (`agy-real`) resuelve su credencial OAuth a partir de `$HOME`:

```text
$HOME/.gemini/antigravity-cli/antigravity-oauth-token
```

`agyc` prepara e inyecta un `HOME` virtual exclusivo antes de ejecutar `os.execv()`:

```python
os.environ["HOME"] = prepare_isolated_home(alias)  # ~/.agyc_homes/<alias>
os.execv(real_agy, cmd_args)
```

Estructura resultante:

```text
~/.agyc_homes/
├── agy01/.gemini/antigravity-cli/
│   ├── antigravity-oauth-token   ← 🔒 token exclusivo (dev1@gmail.com - ULTRA)
│   ├── settings.json             ← 🔗 symlink compartido (statusLine + title)
│   ├── accounts/                 ← 🔗 symlink compartido
│   ├── conversations/            ← 🔗 symlink compartido
│   └── brain/                    ← 🔗 symlink compartido
├── agy02/...                     ← 🔒 token exclusivo (dev2@gmail.com - PRO)
└── agy03/...                     ← 🔒 token exclusivo (dev3@gmail.com - PRO)
```

### Algoritmo de Rotación (`agyc auto`)

```text
Modo Carbon / Ultra (o modelo activo Gemini 4 Carbon):
  filtro = solo cuentas con plan == ULTRA y token válido
  score  = (gemini_semanal × 0.7) + (gemini_5h × 0.3)

Modo Claude & GPT:
  filtro = cuentas PRO + ULTRA válidas
  score  = (claude_semanal × 0.7) + (claude_5h × 0.3)

Modo Gemini (Argon / Hydrogen / Orchestrator / 3.8 Flash):
  filtro = cuentas PRO + ULTRA válidas
  prioriza ventana 5H disponible y desempata con reserva semanal
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
| **v1.5** | Nov 2026 | Esquema oficial **Antigravity 1.5.10**: soporte cuentas **`PRO` / `ULTRA`**, **2 grupos unificados de cuotas** (`Gemini` y `Claude & GPT`), tabla compacta de 6 columnas (`Disponible` al 100%), `agyc auto [gemini\|claude\|carbon\|ultra]`, **Top Bar en vivo** (`agyc-titleline` en `"title"` + metadatos Herdr + `agyc-topbar` en `ui.tab_bar_right`) |

---

## Documentación Adicional y Licencia

- Manual completo de operación y arquitectura: [docs/MANUAL.md](docs/MANUAL.md)
- Skill para agentes: [skills/agyc/SKILL.md](skills/agyc/SKILL.md)
- Licencia: MIT — ver [LICENSE](LICENSE)
