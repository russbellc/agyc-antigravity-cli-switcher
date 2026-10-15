#!/usr/bin/env bash
# =============================================================================
# agyc — Instalador para Ubuntu con Snap antigravity-cli
# Multi-account switcher con perfiles HOME aislados por cuenta
#
# Uso:
#   chmod +x install.sh && ./install.sh
#
# Requisitos:
#   - Ubuntu Linux (x86_64)
#   - snap install antigravity-cli (Google Antigravity CLI)
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
AGY_BIN_DIR="$HOME/.gemini/antigravity-cli/bin"
SNAP_BIN_DIR="$HOME/snap/antigravity-cli/common/.gemini/antigravity-cli/bin"
SKILL_DIR="$HOME/proyectos/.agents/skills/agyc"
LOCAL_BIN="$HOME/.local/bin"

echo ""
echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}${CYAN}║         agyc — Instalador Multi-Cuenta               ║${RESET}"
echo -e "${BOLD}${CYAN}║   Google Antigravity Switcher para Ubuntu             ║${RESET}"
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
for path in /snap/antigravity-cli/current/bin/agy /snap/antigravity-cli/23/bin/agy; do
    if [ -f "$path" ]; then
        AGY_REAL="$path"
        break
    fi
done

if [ -z "$AGY_REAL" ]; then
    echo -e "${YELLOW}⚠ Binario agy no encontrado en rutas de snap.${RESET}"
    echo -e "${DIM}  Asegúrate de tener instalado: snap install antigravity-cli${RESET}"
    echo -e "${DIM}  El instalador continuará, pero los lanzadores no funcionarán hasta instalar agy.${RESET}"
else
    echo -e "  ${DIM}Binario agy: $AGY_REAL${RESET}"
fi

echo -e "${GREEN}✓ Requisitos verificados${RESET}"
echo ""

# ── Paso 2: Crear directorios ─────────────────────────────────────────────────
echo -e "${BOLD}[2/7] Creando directorios...${RESET}"
mkdir -p "$AGY_BIN_DIR"
mkdir -p "$LOCAL_BIN"
mkdir -p "$HOME/.agyc_homes"
if [ -d "$SNAP_BIN_DIR" ] || mkdir -p "$SNAP_BIN_DIR" 2>/dev/null; then
    echo -e "  ${DIM}$SNAP_BIN_DIR${RESET}"
fi
echo -e "${GREEN}✓ Directorios creados${RESET}"
echo ""

# ── Paso 3: Instalar agyc ─────────────────────────────────────────────────────
echo -e "${BOLD}[3/7] Instalando agyc...${RESET}"

cp -f "$SCRIPT_DIR/bin/agyc" "$AGY_BIN_DIR/agyc"
chmod +x "$AGY_BIN_DIR/agyc"
echo -e "  ${DIM}→ $AGY_BIN_DIR/agyc${RESET}"

# Sincronizar a ruta snap si existe
if [ -d "$(dirname "$SNAP_BIN_DIR")" ]; then
    cp -f "$SCRIPT_DIR/bin/agyc" "$SNAP_BIN_DIR/agyc" 2>/dev/null && \
    chmod +x "$SNAP_BIN_DIR/agyc" && \
    echo -e "  ${DIM}→ $SNAP_BIN_DIR/agyc${RESET}" || true
fi

# Symlink global
ln -sf "$AGY_BIN_DIR/agyc" "$LOCAL_BIN/agyc" 2>/dev/null || \
    cp -f "$AGY_BIN_DIR/agyc" "$LOCAL_BIN/agyc"
chmod +x "$LOCAL_BIN/agyc"
echo -e "${GREEN}✓ agyc instalado${RESET}"
echo ""

# ── Paso 4: Crear lanzadores directos agy01..agy15 ───────────────────────────
echo -e "${BOLD}[4/7] Creando lanzadores directos agy01..agy15...${RESET}"
for i in $(seq -w 1 15); do
    alias="agy${i}"
    target="$LOCAL_BIN/$alias"
    ln -sf "$AGY_BIN_DIR/agyc" "$target" 2>/dev/null || \
        cp -f "$AGY_BIN_DIR/agyc" "$target"
    chmod +x "$target"
done
echo -e "${GREEN}✓ Lanzadores agy01..agy15 creados en $LOCAL_BIN${RESET}"
echo ""

# ── Paso 5: Configurar PATH ───────────────────────────────────────────────────
echo -e "${BOLD}[5/7] Configurando PATH...${RESET}"
SHELL_RC="$HOME/.bashrc"
[ -n "$ZSH_VERSION" ] && SHELL_RC="$HOME/.zshrc"

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
if [ -d "$HOME/proyectos/.agents/skills" ]; then
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
python3 -m py_compile "$AGY_BIN_DIR/agyc" && echo -e "  ${GREEN}✓ Sintaxis Python correcta${RESET}"

# Aplicar PATH en sesión actual
export PATH="$HOME/.local/bin:$HOME/.gemini/antigravity-cli/bin:$PATH"
export SSH_TTY="${SSH_TTY:-/dev/pts/0}"

echo ""
echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}${GREEN}║           ✅ agyc instalado correctamente            ║${RESET}"
echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════════════════╝${RESET}"
echo ""
echo -e "${BOLD}Próximos pasos:${RESET}"
echo ""
echo -e "  ${CYAN}1.${RESET} Recargar el shell:"
echo -e "     ${DIM}source ~/.bashrc${RESET}"
echo ""
echo -e "  ${CYAN}2.${RESET} Registrar tu primera cuenta Google AI Pro:"
echo -e "     ${DIM}agyc add${RESET}"
echo ""
echo -e "  ${CYAN}3.${RESET} Entrar a Antigravity con tu cuenta:"
echo -e "     ${DIM}agy01${RESET}"
echo ""
echo -e "  ${CYAN}4.${RESET} Ver el estado de todas tus cuentas:"
echo -e "     ${DIM}agyc${RESET}"
echo ""
echo -e "${DIM}Documentación completa: docs/MANUAL.md${RESET}"
echo -e "${DIM}GitHub: https://github.com/russbellc/antigravity-switcher${RESET}"
echo ""
