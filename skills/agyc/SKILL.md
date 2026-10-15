---
name: agyc
description: >-
  Administrador multi-cuenta de Google AI Pro para Google Antigravity (agyc).
  Usa esta habilidad cuando el usuario pregunte por el estado de sus cuentas,
  desee cambiar de cuenta (switch), consultar cuotas de tokens disponibles
  o rotar a la cuenta con mayor saldo.
---

# Administrador Multi-Cuenta `agyc`

Esta habilidad permite al agente consultar y administrar múltiples cuentas de Google AI Pro en Antigravity.

## Comandos Disponibles

- `agyc` o `agyc list`: Muestra la tabla completa de cuentas con barras de progreso de consumo de tokens:
  - Gemini: 5H (diario) y Semanal.
  - Claude & GPT: 5H (diario) y Semanal.
  - Estado de cada cuenta (ACTIVA, DEFAULT, LISTA, EXPIRADA).
- `agyc list -r`: Fuerza la consulta en vivo a los servidores de Google para refrescar contadores de cuota y renovar tokens de acceso.
- `agyc <alias>` o `agyc switch <alias>`: Cambia la sesión activa a otra cuenta (ej. `agyc agy02`).
- `agyc auto`: Evalúa el saldo restante de todas las cuentas y cambia automáticamente a la que tenga mayor cuota disponible según el modelo activo en `settings.json`.
- `agyc auto claude` o `agyc auto gemini`: Fuerza la rotación evaluando específicamente esa familia de modelos.
- `agyc add [alias]`: Registra una nueva cuenta asignando automáticamente el correlativo (`agy02`, `agy03`, etc.). Abre el navegador forzando la selección de cuenta y consentimiento (`select_account consent`).
- `agyc renew <alias>` o `agyc reauth <alias>`: Re-vincula y renueva la autenticación de una cuenta existente cuando Google solicita verificación de elegibilidad o cuando el token expira (ej. `agyc renew agy03`).
- `agyc quota [alias]`: Muestra el reporte detallado de modelos y ventanas de reinicio exactas.
- `agyc default <alias>`: Fija la cuenta por defecto para futuros inicios.
- `agyc wipe`: Limpia y purga de forma segura todas las credenciales, cuentas registradas, sesión activa y caché para reiniciar desde cero con confirmación (soporta `--force` o `-y`).
- `agyc rm <alias>`: Elimina una cuenta específica y previene residuos huérfanos.

## Lanzadores Directos

- `agy01`, `agy02`, `agy03`... hasta `agy15`: Entra directamente a la cuenta con `--dangerously-skip-permissions` activo por defecto.
- Cuentan con Guardián Anti-Colisiones: si se intenta abrir una cuenta distinta a la activa, pide confirmación previa para no cruzar sesiones.

## Casos de Uso del Agente

1. **Cuando el usuario pregunte por sus cuotas o consumo:**
   Ejecutar `agyc` (o `agyc --json` para procesar programáticamente) y resumir el estado al usuario.

2. **Cuando se agote la cuota de la cuenta actual (Error 429 RESOURCE_EXHAUSTED o cuota al 0%):**
   Ejecutar `agyc auto` para rotar de inmediato a la cuenta con mayor saldo de tokens.
   Recomendar la estrategia **"Agotar y Rotar"**: usar una cuenta hasta que baje de 20%, y luego rotar a la siguiente mientras la primera se recupera sola en segundo plano (ventana de 5 horas).

3. **Cuando Google muestre 'Eligibility check failed' o pida re-autenticar:**
   Indicar al usuario ejecutar `agyc renew <alias>` (ej. `agyc renew agy03`) para completar la verificación de Google en el navegador.

4. **Cuando el usuario pida cambiar de cuenta:**
   Ejecutar `agyc <alias>` (ej. `agyc agy02`) para aplicar el switch sin reiniciar el entorno.

## Arquitectura de Perfiles Aislados (Opción B — Activa)

Cada lanzador directo (`agy01`, `agy02`, `agy03`) usa perfiles HOME aislados en `~/.agyc_homes/<alias>/`:

- **Token blindado:** Cada cuenta tiene su propio `antigravity-oauth-token` exclusivo. Dos paneles de herdr con cuentas distintas **nunca compiten** por el mismo token.
- **Recursos compartidos via symlink:** `settings.json`, `accounts/`, `projects/` y `brain/` apuntan al directorio compartido real (`~/.gemini/antigravity-cli/`).
- **Mecanismo:** Antes del `os.execv()`, se inyecta `os.environ["HOME"] = ~/.agyc_homes/<alias>`. El binario `agy` usa `$HOME` para construir la ruta de `.gemini`.
- **Inicialización automática:** `prepare_isolated_home(alias)` crea la estructura al primer uso del lanzador.

### Uso en múltiples paneles de herdr

```
Panel 1 → agy01   (HOME=~/.agyc_homes/agy01, token: dev1@gmail.com)
Panel 2 → agy02   (HOME=~/.agyc_homes/agy02, token: dev2@gmail.com)
Panel 3 → agy03   (HOME=~/.agyc_homes/agy03, token: dev3@gmail.com)
```

Los 3 paneles trabajan en paralelo sin colisión de tokens. ✅

