# Manual Completo de `agyc`
## Google Antigravity Multi-Account Switcher

> **Versión:** v1.4 | **Fecha:** Octubre 2026
> **Plataforma:** Ubuntu Linux x86_64 con Snap `antigravity-cli`

---

## Índice

1. [¿Para qué sirve agyc?](#1-para-qué-sirve-agyc)
2. [Instalación](#2-instalación)
3. [Primeros pasos](#3-primeros-pasos)
4. [Comandos de referencia](#4-comandos-de-referencia)
5. [Aislamiento de perfiles HOME](#5-aislamiento-de-perfiles-home)
6. [Uso en múltiples paneles (herdr / tmux / zellij)](#6-uso-en-múltiples-paneles)
7. [Rotación inteligente de cuotas](#7-rotación-inteligente-de-cuotas)
8. [Estrategia: Agotar y Rotar](#8-estrategia-agotar-y-rotar)
9. [Gestión de tokens y elegibilidad](#9-gestión-de-tokens-y-elegibilidad)
10. [Skill para el agente de Antigravity](#10-skill-para-el-agente-de-antigravity)
11. [agyc wipe — Reinicio limpio](#11-agyc-wipe--reinicio-limpio)
12. [agyc update — Actualizador automático](#12-agyc-update--actualizador-automático)
13. [Historia de versiones y decisiones de diseño](#13-historia-de-versiones-y-decisiones-de-diseño)

---

## 1. ¿Para qué sirve agyc?

Google Antigravity CLI (`agy`) está diseñado para operar con una sola cuenta de Google a la vez. Al desarrollar a tiempo completo con modelos de alto consumo (Claude Sonnet 4.6 Thinking, Gemini Pro, etc.), las cuotas de una sola suscripción de Google AI Pro se agotan en horas o días.

`agyc` resuelve esto transformando Antigravity en una estación de trabajo **multi-cuenta**:

- Gestiona hasta **15 cuentas correlativas** (`agy01`..`agy15`)
- Cada cuenta tiene un **perfil HOME aislado** — dos paneles con cuentas distintas nunca compiten por el mismo token
- **Rotación automática** cuando se agota la cuota
- **Panel visual de cuotas** con barras de progreso

---

## 2. Instalación

### Requisitos

| Requisito | Versión mínima |
|---|---|
| Ubuntu Linux | 20.04+ |
| Google Antigravity CLI | Cualquier versión snap |
| Python | 3.10+ |
| Google AI Pro | Al menos 1 cuenta activa |

### Instalación desde GitHub

```bash
git clone https://github.com/russbellc/agyc-antigravity-cli-switcher.git
cd agyc-antigravity-cli-switcher
chmod +x install.sh
./install.sh
source ~/.bashrc
```

### Instalación manual

```bash
# 1. Copiar agyc a la ruta de binarios
mkdir -p ~/.gemini/antigravity-cli/bin
cp bin/agyc ~/.gemini/antigravity-cli/bin/agyc
chmod +x ~/.gemini/antigravity-cli/bin/agyc

# 2. Añadir al PATH en ~/.bashrc
echo 'export PATH="$HOME/.local/bin:$HOME/.gemini/antigravity-cli/bin:$PATH"' >> ~/.bashrc
echo 'export SSH_TTY="${SSH_TTY:-/dev/pts/0}"' >> ~/.bashrc
source ~/.bashrc

# 3. Crear lanzadores directos
for i in $(seq -w 1 15); do
    ln -sf ~/.gemini/antigravity-cli/bin/agyc ~/.local/bin/agy${i}
done
```

---

## 3. Primeros pasos

### Registrar cuentas

```bash
agyc add      # primera cuenta → agy01 (abre navegador para OAuth)
agyc add      # segunda cuenta → agy02
agyc add      # tercera cuenta → agy03
```

### Ver estado de cuentas

```bash
agyc
```

Salida:

```
PANEL DE CUENTAS DE GOOGLE AI PRO (ANTIGRAVITY / AGYC)

┌──────────┬─────────────────────────┬─────────────┬──────────────────────────────────┬──────────────────────────────────┬──────────────────────────────────┐
│ ALIAS    │ CUENTA / EMAIL          │ ESTADO      │ GEMINI (DIARIO / SEM)            │ GEMINI 4 (DIARIO / SEM)          │ CLAUDE & GPT (DIARIO / SEM)      │
├──────────┼─────────────────────────┼─────────────┼──────────────────────────────────┼──────────────────────────────────┼──────────────────────────────────┤
│ * agy01  │ dev1@gmail.com          │ *ACTIVA+DEF │ 5H:  [██████████] 100% (4h 51m)  │ 5H:  [██████████] 100% (4h 51m)  │ 5H:  [██████████] 100% (4h 51m)  │
│          │                         │             │ Sem: [██████░░░░]  63% (2d 8h)   │ Sem: [██████████] 100% (168h)    │ Sem: [█████░░░░░]  50% (6d 0h)   │
├──────────┼─────────────────────────┼─────────────┼──────────────────────────────────┼──────────────────────────────────┼──────────────────────────────────┤
│   agy02  │ dev2@gmail.com          │   LISTA     │ 5H:  [██████████] 100% (4h 51m)  │ 5H:  [██████████] 100% (4h 51m)  │ 5H:  [██████████] 100% (4h 51m)  │
│          │                         │             │ Sem: [██████████]  99% (6d 2h)   │ Sem: [██████████] 100% (168h)    │ Sem: [█████░░░░░]  46% (4d 11h)  │
└──────────┴─────────────────────────┴─────────────┴──────────────────────────────────┴──────────────────────────────────┴──────────────────────────────────┘
```

### Entrar a Antigravity

```bash
agy01    # entra con la cuenta agy01 directamente
agy02    # entra con la cuenta agy02 directamente
```

---

## 4. Comandos de Referencia

### Lanzadores directos

```bash
agy01          # Entra directo a agy01 con --dangerously-skip-permissions
agy02          # Entra directo a agy02
# ... hasta agy15
```

### Gestión de cuentas

```bash
agyc                      # Panel visual de cuotas (por defecto)
agyc list                 # Igual que arriba
agyc list -r              # Refresca cuotas desde Google en tiempo real
agyc add                  # Registra nueva cuenta (auto-correlativo)
agyc add agy02            # Re-registra una cuenta específica
agyc renew agy03          # Re-vincula cuando Google pide re-autenticación
agyc reauth agy03         # Alias de renew
agyc rm agy03             # Elimina una cuenta
agyc wipe                 # Vacía TODAS las credenciales (con confirmación)
agyc wipe --force         # Sin confirmación
```

### Cambio de cuenta

```bash
agyc switch agy02         # Cambia la cuenta activa sin abrir Antigravity
agyc agy02                # Alias directo de switch
agyc default agy01        # Fija la cuenta predeterminada para `agy` a secas
```

### Cuotas y rotación

```bash
agyc quota                # Reporte detallado de la cuenta activa
agyc quota agy02          # Reporte de una cuenta específica
agyc auto                 # Rota a la cuenta con mayor cuota (detecta Claude/Gemini/Argon)
agyc auto claude          # Fuerza evaluación para modelos Claude & GPT
agyc auto gemini          # Fuerza evaluación para modelos Gemini Pro/Flash
agyc auto argon           # Fuerza evaluación para Gemini 4 Argon (límite semanal independiente)
```

### Actualización del sistema

```bash
agyc update               # Actualiza agyc desde GitHub, sincroniza binarios y verifica Snap
agy update                # Alias directo interceptado por el wrapper de agy
```

---

## 5. Aislamiento de Perfiles HOME

### El problema que resuelve

Cuando abres múltiples paneles del terminal con cuentas distintas, el token de autenticación (`antigravity-oauth-token`) podría ser sobreescrito por `agyc switch`, causando que un panel use el token de otra cuenta.

### La solución: HOME virtual por cuenta

El binario `agy` construye la ruta de su token a partir de `$HOME`:

```
$HOME/.gemini/antigravity-cli/antigravity-oauth-token
```

`agyc` inyecta un `HOME` virtual por cuenta **antes** del `os.execv()`:

```python
# En launch_real_agy() — la clave del aislamiento
if alias:
    isolated_home = prepare_isolated_home(alias)
    os.environ["HOME"] = isolated_home   # cada proceso de agy lee su propio HOME

os.execv(real_agy, cmd_args)
```

### Estructura resultante

```
~/.agyc_homes/
├── agy01/
│   └── .gemini/antigravity-cli/
│       ├── antigravity-oauth-token   ← 🔒 token exclusivo (dev1@gmail.com)
│       ├── settings.json             ← 🔗 symlink → ~/.gemini/antigravity-cli/settings.json
│       ├── accounts/                 ← 🔗 symlink → ~/.gemini/antigravity-cli/accounts/
│       └── brain/                    ← 🔗 symlink → ~/.gemini/antigravity-cli/brain/
├── agy02/
│   └── .gemini/antigravity-cli/
│       ├── antigravity-oauth-token   ← 🔒 token exclusivo (dev2@gmail.com)
│       └── ...
└── agy03/
    └── ...
```

### Recursos compartidos vs. exclusivos

| Recurso | Tipo | Razón |
|---|---|---|
| `antigravity-oauth-token` | 🔒 **Exclusivo por cuenta** | Evita colisiones entre paneles |
| `settings.json` | 🔗 Symlink compartido | El modelo activo aplica a todos |
| `accounts/` | 🔗 Symlink compartido | `agyc list` ve todas las cuentas |
| `brain/` | 🔗 Symlink compartido | El historial es común |
| `projects/` | 🔗 Symlink compartido | Los proyectos no cambian |

### Función `prepare_isolated_home(alias)`

Se ejecuta automáticamente al lanzar `agy01`, `agy02`, etc.:

1. Crea `~/.agyc_homes/<alias>/.gemini/antigravity-cli/` si no existe
2. Copia el token activo del alias (ya preparado por `switch_active_account`) como archivo propio
3. Crea symlinks a los recursos compartidos
4. Retorna la ruta del HOME aislado

---

## 6. Uso en Múltiples Paneles

### Setup recomendado en herdr

```
herdr
├── Proyecto 1  (backend)
│   ├── Vista 1 — Tab 1: editor / código
│   ├── Vista 1 — Tab 2: git / tests
│   ├── Vista 2 — Tab 1: agy02  ← escribe solo esto
│   └── Vista 2 — Tab 2: logs / servidor
└── Proyecto 2  (frontend)
    ├── Vista 1 — Tab 1: editor / código
    ├── Vista 1 — Tab 2: git / tests
    ├── Vista 2 — Tab 1: agy03  ← escribe solo esto
    └── Vista 2 — Tab 2: logs / servidor
```

### Lo que sucede internamente

```
Panel con agy02:
  HOME = ~/.agyc_homes/agy02
  Token → dev2@gmail.com (fijo, no cambia aunque hagas agyc switch en otro panel)

Panel con agy03:
  HOME = ~/.agyc_homes/agy03
  Token → dev3@gmail.com (completamente independiente)
```

### Cuándo usar la misma cuenta en 2 paneles

Puedes abrir `agy02` en dos paneles distintos simultáneamente sin problema. Ambos comparten el mismo token (misma cuenta), que es lo esperado. Cada sesión genera su propio `conversation-id` único.

---

## 7. Rotación Inteligente de Cuotas

### Algoritmo de selección

`agyc auto` evalúa todas las cuentas registradas y selecciona la mejor según el modelo en uso:

```
Para Claude & GPT:
  score = (cuota_semanal × 0.7) + (cuota_5h × 0.3)
  → Prioriza reserva semanal, usa la ventana de 5H como desempate

Para Gemini 4 Argon:
  score = (cuota_semanal × 0.8) + (cuota_5h × 0.2)
  → Prioriza la cuota semanal independiente de Argon (168h)

Para Gemini Pro / Flash:
  → Prioriza cuota de 5H (ventana más corta)
  → Desempata con cuota semanal
```

Descarta automáticamente cuentas con token revocado (`is_revoked=True`).

### Detección automática del modelo

`agyc auto` (sin argumentos) lee `settings.json` para detectar el modelo activo y aplica el algoritmo correspondiente:

```bash
agyc auto          # detecta: Claude, Gemini o Argon y rota inteligentemente
agyc auto claude   # fuerza evaluación Claude & GPT
agyc auto gemini   # fuerza evaluación Gemini Pro/Flash
agyc auto argon    # fuerza evaluación Gemini 4 Argon
```

---

## 8. Estrategia: Agotar y Rotar

La estrategia recomendada para maximizar tiempo de desarrollo continuo:

```
agy02 (100%) → usar hasta ~20% → agyc auto → agy03 (100%) → usar hasta ~20%
                                                ↑
                                    agy02 se recupera solo en 5h
                                    (ventana de reinicio automático de Google)
```

**En lugar de rotar por reloj**, rotar cuando la cuota baja de ~20%. Esto maximiza el uso de cada cuenta y las deja recuperarse mientras trabajas con la siguiente.

---

## 9. Gestión de Tokens y Elegibilidad

### Token expirado (invalid_grant)

```bash
agyc renew agy03   # re-vincula: abre navegador, solicita re-autenticación
```

### Eligibility Check de Google

Si Google muestra `Eligibility check failed` al entrar con una cuenta:

```bash
agyc renew agy03   # completa la verificación de elegibilidad en el navegador
```

Esto ocurre normalmente la **primera vez** que una cuenta usa Antigravity, o después de un período de inactividad prolongado.

### Bypass de Keyring

`agyc` configura automáticamente la variable `SSH_TTY` para que el binario `agy` use almacenamiento basado en archivo en lugar del GNOME Keyring:

```bash
export SSH_TTY="${SSH_TTY:-/dev/pts/0}"
```

Esto se añade automáticamente a `~/.bashrc` durante la instalación.

---

## 10. Skill para el Agente de Antigravity

El archivo `skills/agyc/SKILL.md` le enseña al agente de Antigravity a:

- Ejecutar `agyc auto` automáticamente cuando detecta error 429 (cuota agotada)
- Indicar `agyc renew <alias>` cuando Google pide re-autenticación
- Mostrar `agyc list` cuando el usuario pregunta por sus cuotas
- Recomendar la estrategia "Agotar y Rotar"

### Instalación del skill

```bash
# El instalador lo hace automáticamente si existe ~/proyectos/.agents/skills/
# Para instalación manual:
mkdir -p ~/proyectos/.agents/skills/agyc
cp skills/agyc/SKILL.md ~/proyectos/.agents/skills/agyc/SKILL.md
```

---

## 11. agyc wipe — Reinicio Limpio

Elimina todas las credenciales, cuentas y caché de sesión:

```bash
agyc wipe          # pide confirmación interactiva
agyc wipe --force  # sin confirmación (para scripts)
agyc wipe -y       # alias de --force
```

**Elimina:**
- Todos los archivos en `accounts/`
- El `antigravity-oauth-token` compartido
- Los tokens blindados en `~/.agyc_homes/`
- La configuración activa de `agyc`

**No elimina:**
- `settings.json` (modelo, tema, etc.)
- `brain/` (historial de conversaciones)
- `projects/` (proyectos de Antigravity)

---

---

## 12. agyc update — Actualizador Automático

Permite mantener `agyc` y las herramientas del ecosistema Antigravity siempre al día:

```bash
agyc update      # actualiza repositorio, binarios y perfiles
agy update       # wrapper directo equivalente
```

### Proceso de actualización en 4 fases

1. **GitHub Sync**: Detecta si el repositorio local está clonado de Git y ejecuta `git pull --rebase`. Si se instaló sin Git, descarga la última versión estable del binario desde GitHub.
2. **Sincronización de Binarios**: Copia la versión actualizada a todas las rutas activas:
   - `~/.gemini/antigravity-cli/bin/agyc`
   - `~/snap/antigravity-cli/common/.gemini/antigravity-cli/bin/agyc`
   - `~/.local/bin/agy01..15`
   - `~/proyectos/backup_agyc/`
3. **Inspección de Snap Antigravity**: Consulta `snap list antigravity-cli` para alertar si hay actualizaciones pendientes del motor principal de Antigravity o sugerir `snap refresh`.
4. **Mantenimiento de Perfiles**: Verifica y sincroniza los symlinks compartidos en todos los perfiles de `~/.agyc_homes/`.

---

## 13. Historia de Versiones y Decisiones de Diseño

### v1.0 — MVP (Oct 13, 2026)

**Funcionalidades:** switch, lanzadores directos, tabla de cuotas, OAuth con navegador.

**Decisión clave:** Usar `os.execv()` en lugar de `subprocess.run()` para preservar la TUI de Antigravity (colores, señales, redimensionamiento de terminal).

### v1.1 — Rotación Inteligente (Oct 14, 2026)

**Funcionalidades:** `agyc auto`, algoritmo de score, detección automática del modelo desde `settings.json`.

**Decisión clave:** Algoritmo diferente para Claude (prioriza semanal) vs Gemini (prioriza 5H) porque los patrones de consumo son distintos.

### v1.2 — Corrección y Nuevos Comandos (Oct 15, 2026)

**Problema resuelto:** `PermissionError: [Errno 13] Permission denied: '/home/common-agy02'` — causado por cálculo incorrecto de rutas en un intento previo de aislamiento via `SNAP_USER_COMMON`.

**Solución:** Eliminar la función `prepare_isolated_env()` defectuosa. El binario `agy` ignora completamente `SNAP_USER_COMMON`; solo respeta `$HOME`.

**Descubrimiento crítico:** El binario Go de Antigravity usa `$HOME` (no `SNAP_USER_COMMON`) para construir la ruta de `.gemini`. Verificado con `lsof`.

**Nuevos comandos:** `agyc renew` / `agyc reauth` — re-vincula cuentas con Eligibility Check fallido.

### v1.3 — Aislamiento Real de Perfiles (Oct 15, 2026)

**Funcionalidad central:** `prepare_isolated_home(alias)` + inyección de `$HOME` en `launch_real_agy()`.

**Decisión clave:** En lugar de aislar via `SNAP_USER_COMMON` (que el binario ignora), se inyecta `os.environ["HOME"]` antes del `os.execv()`. Esto hace que el binario `agy` use un directorio `.gemini` completamente independiente por cuenta.

**Eliminación del Guardián Anti-Colisiones:** Con perfiles aislados, el aviso de confirmación al abrir una cuenta no activa es fricción innecesaria. Se eliminó. El lanzador ahora entra directo sin preguntas.

**Por qué symlinks y no copias completas:** Solo el token es exclusivo por cuenta. El resto (`settings.json`, `accounts/`, `brain/`) son symlinks al directorio compartido para que `agyc list`, `agyc auto` y el historial funcionen correctamente desde cualquier perfil.

### v1.4 — Gemini 4 Argon y Actualizador Automático (Oct 16, 2026)

**Funcionalidades:**
- **Soporte para `Gemini 4 Argon`**: Reconoce la nueva cuota semanal separada (168h) introducida por Google en Antigravity. Visualización en barra `Arg:` en `agyc list` y rotación inteligente con `agyc auto argon` o autodetección cuando el modelo activo es Argon.
- **Comando `agyc update` / `agy update`**: Actualizador de 4 fases que descarga desde GitHub, sincroniza binarios locales, inspecciona Snap y refresca perfiles aislados.
- **Wrapper `bin/agy`**: Intercepta `agy update` y `agy upgrade` ejecutando `agyc update`.
