#!/usr/bin/env bash
# =============================================================================
# agyc v1.5 — Instalador para Ubuntu Linux (Google Antigravity CLI 1.5.10+)
# Multi-account switcher (Google AI Pro & Ultra) con perfiles HOME aislados
#
# Uso:
#   chmod +x install.sh && ./install.sh
#
# Requisitos:
#   - Ubuntu Linux (x86_64)
#   - Google Antigravity CLI 1.5.10+ (binario nativo o snap antigravity-cli)
#   - Python 3.10+
# =============================================================================

set -e

BOLD="\033[1m"
GREEN="\033[32m"
CYAN="\033[36m"
YELLOW="\033[33m"
RED="\033[31m"
DIM="\033[2m"
RESET="\033[0m"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Resolver HOME real incluso si se ejecuta desde un panel con perfil aislado (~/.agyc_homes/agyXX)
REAL_HOME="$HOME"
if [[ "$REAL_HOME" == *"/.agyc_homes/"* ]]; then
    REAL_HOME="${REAL_HOME%%/.agyc_homes/*}"
fi

AGY_BIN_DIR="$REAL_HOME/.gemini/antigravity-cli/bin"
SNAP_BIN_DIR="$REAL_HOME/snap/antigravity-cli/common/.gemini/antigravity-cli/bin"
SKILL_DIR="$REAL_HOME/proyectos/.agents/skills/agyc"
LOCAL_BIN="$REAL_HOME/.local/bin"

echo ""
echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}${CYAN}║       agyc v1.5 — Instalador Multi-Cuenta            ║${RESET}"
echo -e "${BOLD}${CYAN}║   Google Antigravity 1.5.10+ (AI Pro & AI Ultra)     ║${RESET}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════════════╝${RESET}"
echo ""

# ── Paso 1: Verificar requisitos ──────────────────────────────────────────────
echo -e "${BOLD}[1/7] Verificando requisitos...${RESET}"

if ! command -v python3 &>/dev/null; then
    echo -e "${RED}✗ Python3 no encontrado. Instalar con: sudo apt install python3${RESET}"
    exit 1
fi

PYTHON_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo -e "  ${DIM}Python: $PYTHON_VER${RESET}"

AGY_REAL=""
for path in \
    "$AGY_BIN_DIR/agy-real" \
    "$LOCAL_BIN/agy" \
    /snap/antigravity-cli/current/bin/agy \
    /snap/antigravity-cli/23/bin/agy; do
    if [ -f "$path" ]; then
        AGY_REAL="$path"
        break
    fi
done

if [ -z "$AGY_REAL" ]; then
    echo -e "${YELLOW}⚠ Binario agy no encontrado en ~/.gemini/antigravity-cli/bin, ~/.local/bin ni snap.${RESET}"
    echo -e "${DIM}  Asegúrate de tener instalado Google Antigravity CLI (o ejecuta luego 'agyc update').${RESET}"
    echo -e "${DIM}  El instalador continuará preparando los wrappers y lanzadores.${RESET}"
else
    echo -e "  ${DIM}Motor Antigravity detectado: $AGY_REAL${RESET}"
fi

echo -e "${GREEN}✓ Requisitos verificados${RESET}"
echo ""

# ── Paso 2: Crear directorios ─────────────────────────────────────────────────
echo -e "${BOLD}[2/7] Creando directorios...${RESET}"
mkdir -p "$AGY_BIN_DIR"
mkdir -p "$LOCAL_BIN"
mkdir -p "$REAL_HOME/.agyc_homes"
if [ -d "$SNAP_BIN_DIR" ] || mkdir -p "$SNAP_BIN_DIR" 2>/dev/null; then
    echo -e "  ${DIM}$SNAP_BIN_DIR${RESET}"
fi
echo -e "${GREEN}✓ Directorios creados${RESET}"
echo ""

# ── Paso 3: Instalar agyc, wrapper agy y barras de estado/título ──────────────
echo -e "${BOLD}[3/7] Instalando agyc, wrapper agy, statusline, titleline y topbar...${RESET}"

# Si ~/.local/bin/agy es el binario nativo real (no symlink ni wrapper) y aún no existe agy-real,
# respaldarlo en $AGY_BIN_DIR/agy-real antes de colocar el wrapper bin/agy en ~/.local/bin/agy.
if [ -f "$LOCAL_BIN/agy" ] && [ ! -L "$LOCAL_BIN/agy" ] && ! grep -q "agyc update" "$LOCAL_BIN/agy" 2>/dev/null; then
    if [ ! -x "$AGY_BIN_DIR/agy-real" ]; then
        cp -f "$LOCAL_BIN/agy" "$AGY_BIN_DIR/agy-real"
        chmod +x "$AGY_BIN_DIR/agy-real"
        echo -e "  ${DIM}→ Binario nativo preservado en $AGY_BIN_DIR/agy-real${RESET}"
    fi
fi

# 1. Instalar agyc
rm -f "$AGY_BIN_DIR/agyc"
cp -f "$SCRIPT_DIR/bin/agyc" "$AGY_BIN_DIR/agyc"
chmod +x "$AGY_BIN_DIR/agyc"
echo -e "  ${DIM}→ $AGY_BIN_DIR/agyc${RESET}"

rm -f "$LOCAL_BIN/agyc"
ln -sf "$AGY_BIN_DIR/agyc" "$LOCAL_BIN/agyc" 2>/dev/null || \
    cp -f "$AGY_BIN_DIR/agyc" "$LOCAL_BIN/agyc"
chmod +x "$LOCAL_BIN/agyc"
echo -e "  ${DIM}→ $LOCAL_BIN/agyc${RESET}"

# 2. Instalar y preservar wrapper bin/agy en ~/.gemini/antigravity-cli/bin/agy y ~/.local/bin/agy
if [ -f "$SCRIPT_DIR/bin/agy" ]; then
    rm -f "$AGY_BIN_DIR/agy"
    cp -f "$SCRIPT_DIR/bin/agy" "$AGY_BIN_DIR/agy"
    chmod +x "$AGY_BIN_DIR/agy"
    echo -e "  ${DIM}→ $AGY_BIN_DIR/agy${RESET}"

    rm -f "$LOCAL_BIN/agy"
    ln -sf "$AGY_BIN_DIR/agy" "$LOCAL_BIN/agy" 2>/dev/null || \
        cp -f "$AGY_BIN_DIR/agy" "$LOCAL_BIN/agy"
    chmod +x "$LOCAL_BIN/agy"
    echo -e "  ${DIM}→ $LOCAL_BIN/agy (wrapper preservado)${RESET}"
fi

# 3. Instalar agyc-statusline y crear symlink agyc-titleline -> agyc-statusline en ambos directorios
if [ -f "$SCRIPT_DIR/bin/agyc-statusline" ]; then
    rm -f "$AGY_BIN_DIR/agyc-statusline"
    cp -f "$SCRIPT_DIR/bin/agyc-statusline" "$AGY_BIN_DIR/agyc-statusline"
    chmod +x "$AGY_BIN_DIR/agyc-statusline"
    echo -e "  ${DIM}→ $AGY_BIN_DIR/agyc-statusline${RESET}"

    rm -f "$LOCAL_BIN/agyc-statusline"
    ln -sf "$AGY_BIN_DIR/agyc-statusline" "$LOCAL_BIN/agyc-statusline" 2>/dev/null || \
        cp -f "$AGY_BIN_DIR/agyc-statusline" "$LOCAL_BIN/agyc-statusline"
    chmod +x "$LOCAL_BIN/agyc-statusline"
    echo -e "  ${DIM}→ $LOCAL_BIN/agyc-statusline${RESET}"

    rm -f "$AGY_BIN_DIR/agyc-titleline"
    ln -sf agyc-statusline "$AGY_BIN_DIR/agyc-titleline"
    echo -e "  ${DIM}→ $AGY_BIN_DIR/agyc-titleline -> agyc-statusline${RESET}"

    rm -f "$LOCAL_BIN/agyc-titleline"
    ln -sf agyc-statusline "$LOCAL_BIN/agyc-titleline"
    echo -e "  ${DIM}→ $LOCAL_BIN/agyc-titleline -> agyc-statusline${RESET}"
fi

# 4. Instalar agyc-topbar en ~/.gemini/antigravity-cli/bin/ y ~/.local/bin/
if [ -f "$SCRIPT_DIR/bin/agyc-topbar" ]; then
    rm -f "$AGY_BIN_DIR/agyc-topbar"
    cp -f "$SCRIPT_DIR/bin/agyc-topbar" "$AGY_BIN_DIR/agyc-topbar"
    chmod +x "$AGY_BIN_DIR/agyc-topbar"
    echo -e "  ${DIM}→ $AGY_BIN_DIR/agyc-topbar${RESET}"

    rm -f "$LOCAL_BIN/agyc-topbar"
    ln -sf "$AGY_BIN_DIR/agyc-topbar" "$LOCAL_BIN/agyc-topbar" 2>/dev/null || \
        cp -f "$AGY_BIN_DIR/agyc-topbar" "$LOCAL_BIN/agyc-topbar"
    chmod +x "$LOCAL_BIN/agyc-topbar"
    echo -e "  ${DIM}→ $LOCAL_BIN/agyc-topbar${RESET}"
fi

# 5. Sincronizar a ruta snap si existe
if [ -d "$(dirname "$SNAP_BIN_DIR")" ]; then
    rm -f "$SNAP_BIN_DIR/agyc" 2>/dev/null || true
    cp -f "$SCRIPT_DIR/bin/agyc" "$SNAP_BIN_DIR/agyc" 2>/dev/null && \
        chmod +x "$SNAP_BIN_DIR/agyc" && \
        echo -e "  ${DIM}→ $SNAP_BIN_DIR/agyc${RESET}" || true

    if [ -f "$SCRIPT_DIR/bin/agy" ]; then
        rm -f "$SNAP_BIN_DIR/agy" 2>/dev/null || true
        cp -f "$SCRIPT_DIR/bin/agy" "$SNAP_BIN_DIR/agy" 2>/dev/null && \
            chmod +x "$SNAP_BIN_DIR/agy" || true
    fi

    if [ -f "$SCRIPT_DIR/bin/agyc-statusline" ]; then
        rm -f "$SNAP_BIN_DIR/agyc-statusline" "$SNAP_BIN_DIR/agyc-titleline" 2>/dev/null || true
        cp -f "$SCRIPT_DIR/bin/agyc-statusline" "$SNAP_BIN_DIR/agyc-statusline" 2>/dev/null && \
            chmod +x "$SNAP_BIN_DIR/agyc-statusline" && \
            ln -sf agyc-statusline "$SNAP_BIN_DIR/agyc-titleline" 2>/dev/null || true
    fi

    if [ -f "$SCRIPT_DIR/bin/agyc-topbar" ]; then
        rm -f "$SNAP_BIN_DIR/agyc-topbar" 2>/dev/null || true
        cp -f "$SCRIPT_DIR/bin/agyc-topbar" "$SNAP_BIN_DIR/agyc-topbar" 2>/dev/null && \
            chmod +x "$SNAP_BIN_DIR/agyc-topbar" || true
    fi
fi

# 6. Preconfigurar statusLine (agyc-statusline) y title (agyc-titleline) en settings.json
REAL_HOME="$REAL_HOME" python3 -c '
import json, os, glob

real_home = os.environ["REAL_HOME"]
main_settings = os.path.join(real_home, ".gemini", "antigravity-cli", "settings.json")
os.makedirs(os.path.dirname(main_settings), exist_ok=True)
if not os.path.exists(main_settings):
    with open(main_settings, "w", encoding="utf-8") as f:
        json.dump({}, f, indent=2)

configs = glob.glob(os.path.join(real_home, ".agyc_homes", "*", ".gemini", "antigravity-cli", "settings.json")) + [
    main_settings,
]

seen = set()
for p in configs:
    if not os.path.exists(p):
        continue
    rp = os.path.realpath(p)
    if rp in seen:
        continue
    seen.add(rp)
    try:
        with open(rp, "r", encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        d = {}
    d["statusLine"] = {"type": "command", "command": "agyc-statusline", "enabled": True}
    d["title"] = {"type": "command", "command": "agyc-titleline", "enabled": True}
    try:
        with open(rp, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2)
    except Exception:
        pass
' 2>/dev/null || true

echo -e "${GREEN}✓ agyc, wrapper agy, agyc-statusline, agyc-titleline y agyc-topbar instalados${RESET}"
echo ""

# ── Paso 4: Crear lanzadores directos agy01..agy15 ───────────────────────────
echo -e "${BOLD}[4/7] Creando lanzadores directos agy01..agy15...${RESET}"
for i in $(seq -w 1 15); do
    alias="agy${i}"
    for dir in "$AGY_BIN_DIR" "$LOCAL_BIN"; do
        target="$dir/$alias"
        rm -f "$target"
        ln -sf "$AGY_BIN_DIR/agyc" "$target" 2>/dev/null || \
            cp -f "$AGY_BIN_DIR/agyc" "$target"
        chmod +x "$target"
    done
done
echo -e "${GREEN}✓ Lanzadores agy01..agy15 creados en $AGY_BIN_DIR y $LOCAL_BIN${RESET}"
echo ""

# ── Paso 5: Configurar PATH ───────────────────────────────────────────────────
echo -e "${BOLD}[5/7] Configurando PATH...${RESET}"
SHELL_RC="$REAL_HOME/.bashrc"
[ -n "$ZSH_VERSION" ] && SHELL_RC="$REAL_HOME/.zshrc"

PATH_LINE='export PATH="$HOME/.local/bin:$HOME/.gemini/antigravity-cli/bin:$PATH"'
SSH_LINE='export SSH_TTY="${SSH_TTY:-/dev/pts/0}"'

if ! grep -qF '.gemini/antigravity-cli/bin' "$SHELL_RC" 2>/dev/null; then
    echo "" >> "$SHELL_RC"
    echo "# agyc — multi-account switcher para Google Antigravity" >> "$SHELL_RC"
    echo "$PATH_LINE" >> "$SHELL_RC"
    echo "$SSH_LINE" >> "$SHELL_RC"
    echo -e "  ${DIM}PATH añadido a $SHELL_RC${RESET}"
else
    echo -e "  ${DIM}PATH ya configurado en $SHELL_RC${RESET}"
fi
echo -e "${GREEN}✓ PATH configurado${RESET}"
echo ""

# ── Paso 6: Instalar skill para agentes ───────────────────────────────────────
echo -e "${BOLD}[6/7] Instalando skill de agente...${RESET}"
if [ -d "$REAL_HOME/proyectos/.agents/skills" ]; then
    mkdir -p "$SKILL_DIR"
    cp -f "$SCRIPT_DIR/skills/agyc/SKILL.md" "$SKILL_DIR/SKILL.md"
    echo -e "  ${DIM}→ $SKILL_DIR/SKILL.md${RESET}"
    echo -e "${GREEN}✓ Skill instalado${RESET}"
else
    echo -e "  ${YELLOW}⚠ Directorio .agents/skills no encontrado. Skill no instalado.${RESET}"
    echo -e "  ${DIM}Instalar manualmente: mkdir -p ~/proyectos/.agents/skills/agyc${RESET}"
    echo -e "  ${DIM}cp skills/agyc/SKILL.md ~/proyectos/.agents/skills/agyc/${RESET}"
fi
echo ""

# ── Paso 7: Verificación final ────────────────────────────────────────────────
echo -e "${BOLD}[7/7] Verificación final...${RESET}"
python3 -m py_compile "$AGY_BIN_DIR/agyc" && echo -e "  ${GREEN}✓ Sintaxis Python correcta (agyc)${RESET}"
if [ -f "$AGY_BIN_DIR/agyc-statusline" ]; then
    python3 -m py_compile "$AGY_BIN_DIR/agyc-statusline" && echo -e "  ${GREEN}✓ Sintaxis Python correcta (agyc-statusline / agyc-titleline)${RESET}"
fi
if [ -f "$AGY_BIN_DIR/agyc-topbar" ] && head -n 1 "$AGY_BIN_DIR/agyc-topbar" 2>/dev/null | grep -q "python"; then
    python3 -m py_compile "$AGY_BIN_DIR/agyc-topbar" && echo -e "  ${GREEN}✓ Sintaxis Python correcta (agyc-topbar)${RESET}"
fi

# Aplicar PATH en sesión actual
export PATH="$REAL_HOME/.local/bin:$REAL_HOME/.gemini/antigravity-cli/bin:$PATH"
export SSH_TTY="${SSH_TTY:-/dev/pts/0}"

echo ""
echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}${GREEN}║        ✅ agyc v1.5 instalado correctamente          ║${RESET}"
echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════════════════╝${RESET}"
echo ""
echo -e "${BOLD}Próximos pasos:${RESET}"
echo ""
echo -e "  ${CYAN}1.${RESET} Recargar el shell:"
echo -e "     ${DIM}source ~/.bashrc${RESET}"
echo ""
echo -e "  ${CYAN}2.${RESET} Registrar tu primera cuenta Google AI Pro o Google AI Ultra:"
echo -e "     ${DIM}agyc add${RESET}"
echo ""
echo -e "  ${CYAN}3.${RESET} Entrar a Antigravity con tu cuenta:"
echo -e "     ${DIM}agy01${RESET}"
echo ""
echo -e "  ${CYAN}4.${RESET} Ver el estado unificado de todas tus cuentas:"
echo -e "     ${DIM}agyc${RESET}"
echo ""
echo -e "${DIM}Documentación completa: docs/MANUAL.md${RESET}"
echo -e "${DIM}GitHub: https://github.com/russbellc/agyc-antigravity-cli-switcher${RESET}"
echo ""
