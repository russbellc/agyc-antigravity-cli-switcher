# agyc — Google Antigravity Multi-Account Switcher

> **Administrador multi-cuenta para Google Antigravity CLI en Ubuntu Linux**
> Perfiles HOME aislados por cuenta | Rotación inteligente de cuotas | Múltiples paneles en paralelo

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform: Ubuntu](https://img.shields.io/badge/Platform-Ubuntu%20Linux-orange.svg)](https://ubuntu.com)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![Antigravity: CLI](https://img.shields.io/badge/Google-Antigravity%20CLI-red.svg)](https://developers.google.com/gemini-code-assist)

---

## ¿Qué es agyc?

`agyc` convierte Google Antigravity CLI en una estación de trabajo **multi-cuenta**. Nació para resolver un problema concreto: al desarrollar a tiempo completo con modelos como Claude Sonnet 4.6 Thinking, las cuotas de una sola cuenta de Google AI Pro se agotan rápidamente.

**La solución:** gestionar hasta 15 cuentas (`agy01`..`agy15`) con perfiles completamente aislados, permitiendo trabajar en **múltiples paneles del terminal en paralelo** sin colisiones de tokens.

---

## Características

- 🔒 **Perfiles HOME aislados** — Cada cuenta tiene su propio `antigravity-oauth-token` blindado. Dos paneles con cuentas distintas nunca compiten por el mismo token.
- ⚡ **Lanzadores directos** — Escribe `agy02` para entrar directo a esa cuenta. Sin menús, sin preguntas.
- 📊 **Panel visual de cuotas** — Barras de progreso en tiempo real para Gemini (5H/Semanal), Gemini 4 Argon (Semanal) y Claude & GPT (5H/Semanal).
- 🔄 **Rotación automática inteligente** — `agyc auto` detecta el modelo activo (Claude, Gemini o Argon) y conmuta a la cuenta con mayor saldo disponible.
- 🚀 **Actualizador integrado** — `agyc update` (o `agy update`) sincroniza cambios desde GitHub, actualiza todos los binarios locales y verifica Snap.
- 🔑 **Sin keyring** — File-based auth. No requiere GNOME Keyring ni D-Bus.
- 🤖 **Skill para agentes** — El agente de Antigravity puede ejecutar `agyc auto` automáticamente cuando detecta cuota agotada.

---

## Instalación Rápida

```bash
git clone https://github.com/russbellc/antigravity-switcher.git
cd antigravity-switcher
chmod +x install.sh
./install.sh
```

Luego recargar el shell:

```bash
source ~/.bashrc
```

### Requisitos

- Ubuntu Linux (x86_64)
- [Google Antigravity CLI](https://developers.google.com/gemini-code-assist) instalado via snap
- Python 3.10+
- Al menos 1 cuenta de [Google AI Pro](https://one.google.com/about/plans)

---

## Uso

### Registrar tu primera cuenta

```bash
agyc add      # abre el navegador para autenticación OAuth → guarda como agy01
agyc add      # segunda cuenta → guarda como agy02
agyc add      # tercera cuenta → guarda como agy03
```

### Entrar a Antigravity

```bash
agy01         # entra con dev1@gmail.com
agy02         # entra con dev2@gmail.com
agy03         # entra con dev3@gmail.com
```

### Ver estado de cuotas

```bash
agyc          # tabla visual con barras de consumo

# Ejemplo de salida:
# ┌──────────┬──────────────────────────┬──────────────┬───────────────────────────────────┐
# │   agy01  │ dev1@gmail.com           │   DEFAULT    │ 5H:  [█████████░]  87% (1h 32m)   │
# │   agy02  │ dev2@gmail.com           │   LISTA      │ 5H:  [██████████] 100% (4h 19m)   │
# │ * agy03  │ dev3@gmail.com           │ * ACTIVA     │ 5H:  [██████████] 100% (4h 46m)   │
# └──────────┴──────────────────────────┴──────────────┴───────────────────────────────────┘
```

### Rotación automática

```bash
agyc auto         # rota a la cuenta con más cuota (detecta Claude, Gemini o Argon automáticamente)
agyc auto claude  # fuerza evaluación para modelos Claude
agyc auto gemini  # fuerza evaluación para modelos Gemini Pro/Flash
agyc auto argon   # fuerza evaluación para Gemini 4 Argon (límite semanal independiente)
```

---

## Flujo en Múltiples Paneles (herdr / tmux / zellij)

Con el aislamiento de perfiles cada panel trabaja de forma completamente independiente:

```
Panel 1 → agy02   (HOME=~/.agyc_homes/agy02, token: dev2@gmail.com)
Panel 2 → agy03   (HOME=~/.agyc_homes/agy03, token: dev3@gmail.com)
                   ← tokens independientes, nunca se mezclan ✅
```

**Setup típico en herdr:**

```
herdr
├── Proyecto 1
│   ├── Vista 1 — código / git
│   └── Vista 2 → escribe: agy02
└── Proyecto 2
    ├── Vista 1 — código / git
    └── Vista 2 → escribe: agy03
```

---

## Comandos Disponibles

| Comando | Descripción |
|---|---|
| `agyc` / `agyc list` | Panel visual con barras de consumo de todas las cuentas |
| `agyc list -r` | Fuerza refresco de cuotas desde los servidores de Google |
| `agy01` / `agy02` / ... | Entra directo a esa cuenta en Antigravity |
| `agyc add` | Registra una nueva cuenta (OAuth en navegador) |
| `agyc renew <alias>` | Re-vincula una cuenta cuando Google pide re-autenticación |
| `agyc auto` | Rota automáticamente a la cuenta con mayor cuota disponible |
| `agyc auto claude` | Rota priorizando cuota de Claude & GPT |
| `agyc auto gemini` | Rota priorizando cuota de Gemini Pro/Flash |
| `agyc auto argon` | Rota priorizando cuota semanal de Gemini 4 Argon |
| `agyc update` / `agy update` | Actualiza `agyc` desde GitHub, sincroniza binarios y verifica Snap |
| `agyc switch <alias>` | Cambia la cuenta activa sin abrir Antigravity |
| `agyc default <alias>` | Fija la cuenta predeterminada para `agy` a secas |
| `agyc quota <alias>` | Reporte detallado de modelos y ventanas de reinicio |
| `agyc rm <alias>` | Elimina una cuenta registrada |
| `agyc wipe` | Vacía todas las credenciales (con confirmación) |

---

## Arquitectura

### Cómo funciona el aislamiento de perfiles

El binario de Antigravity (`agy`) usa `$HOME` para encontrar su token:

```
$HOME/.gemini/antigravity-cli/antigravity-oauth-token
```

`agyc` inyecta un `HOME` virtual por cuenta antes del `os.execv()`:

```python
os.environ["HOME"] = f"~/.agyc_homes/{alias}"
os.execv(real_agy, cmd_args)
```

Esto crea perfiles completamente aislados:

```
~/.agyc_homes/
├── agy01/.gemini/antigravity-cli/
│   ├── antigravity-oauth-token   ← 🔒 token exclusivo
│   ├── settings.json             ← 🔗 symlink compartido
│   ├── accounts/                 ← 🔗 symlink compartido
│   └── brain/                    ← 🔗 symlink compartido
├── agy02/...
└── agy03/...
```

**Recursos compartidos via symlink:** `settings.json` (modelo activo), `accounts/` (lista de cuentas), `brain/` (historial de conversaciones). Solo el token es exclusivo por cuenta.

### Algoritmo de Rotación (`agyc auto`)

```
Para Claude/GPT:       score = (semanal × 0.7) + (5H × 0.3)
Para Gemini 4 Argon:   score = (semanal × 0.8) + (5H × 0.2)
Para Gemini Pro/Flash: prioriza 5H, desempata con semanal
```

Selecciona siempre la cuenta con mayor score y descarta cuentas con token revocado.

---

## Origen y Desarrollo

Este proyecto nació en una sesión de pair-programming con Google Antigravity (AGY) el 13-16 de Octubre de 2026.

- **Conversación de origen:** `328759be-6f6e-439e-a6c5-e98f6d138850`
- **Entorno:** Ubuntu Linux x86_64, Snap `antigravity-cli` v23
- **Workspace:** `/home/aidev/proyectos`
- **Modelo utilizado:** Claude Sonnet 4.6 (Thinking)

### Historia de versiones

| Versión | Fecha | Cambios principales |
|---|---|---|
| v1.0 | Oct 13, 2026 | MVP: switch, lanzadores, tabla de cuotas |
| v1.1 | Oct 14, 2026 | `agyc auto`, rotación inteligente, bypass keyring |
| v1.2 | Oct 15, 2026 | `agyc renew`, `agyc wipe`, corrección bug PermissionError |
| v1.3 | Oct 15, 2026 | Perfiles HOME aislados (`prepare_isolated_home()`), eliminación del guardián, README GitHub |
| v1.4 | Oct 16, 2026 | Soporte para Gemini 4 Argon (cuota semanal independiente) y comando `agyc update` / `agy update` |

---

## Licencia

MIT License — ver [LICENSE](LICENSE)

---

## Contribuir

Issues y PRs bienvenidos. Si encuentras un bug o quieres añadir soporte para otra distribución, abre un issue.

```bash
git clone https://github.com/russbellc/antigravity-switcher.git
cd antigravity-switcher
# Editar bin/agyc
# Probar con: python3 -m py_compile bin/agyc
```
