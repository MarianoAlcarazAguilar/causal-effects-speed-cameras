---
name: figuras-tesis
description: Figuras de esta tesis (cámaras de velocidad, ITAM) con su estilo — un artículo de economía en escala de grises con un solo acento, tipografía Latin Modern y matplotlib. Usar cuando pida una figura, gráfica o mapa nuevo para la tesis, o revisar o rehacer una que "no se ve como el resto". Aquí vive el estilo que importan los scripts de scripts/figuras/ (mplstyle, fuentes y módulo), las convenciones con su porqué, qué figura usar para qué, cómo insertarla en LaTeX y cinco ejemplos que corren solos.
---

# Figuras con el estilo de la tesis

Las figuras de la tesis se ven como las de un artículo de economía: la misma tipografía
que el texto, escala de grises, un solo color de acento para lo que el texto señala y
ningún título dentro de la figura, porque el título va en el `\caption`. Esta skill trae
todo lo necesario para hacer figuras nuevas que se vean igual.

## Qué hay aquí

| Ruta | Qué es |
| --- | --- |
| `assets/tesis.mplstyle` | El estilo de matplotlib |
| `assets/fonts/` | Latin Modern Roman (regular, negrita, cursiva) |
| `scripts/estilo_tesis.py` | Registra las fuentes y aplica el estilo; expone `ANCHO`, `OSCURO`, `CLARO`, `ACENTO`, `ACENTO_CLARO`, `FONDO`, `cero()`, `menos()`, `pct()` y `guardar()`. **Los scripts de `scripts/figuras/` lo importan de aquí**: si lo mueves o lo cambias, cambian todas las figuras de la tesis |
| `references/convenciones.md` | Las reglas, cada una con su porqué. **Léelo antes de la primera figura** |
| `references/tipos-de-figura.md` | Qué figura usar para qué y lo que se probó y no funcionó |
| `references/latex.md` | El bloque `figure`, qué va en la nota y cómo evitar que mueva páginas |
| `examples/*.py` | Escalera de coeficientes, event study, distribuciones (histograma y acumulada), love plot y mapa resaltado, con datos sintéticos. Cada uno deja su PNG en `examples/png/` |

Las figuras reales de la tesis están en `scripts/figuras/` (`intro_figures.py`,
`capitulo3_figures.py`, `capitulo4_figures.py`, `apendice_figures.py`) y escriben sus PDF
en `tesis/Imagenes/`. Son la mejor referencia para una figura que no esté en los ejemplos.

## Flujo

1. **Elige el tipo de figura** en `references/tipos-de-figura.md` y parte del ejemplo
   más cercano.
2. **Escribe la figura como una función** en el script del capítulo que corresponda en
   `scripts/figuras/`, que devuelva una `Figure`, y agrégala al diccionario que guarda el
   `__main__`. El script ya importa el estilo de esta skill:
   ```python
   sys.path.insert(0, str(Path(__file__).resolve().parents[2] / ".claude" / "skills" / "figuras-tesis" / "scripts"))
   from estilo_tesis import ANCHO, OSCURO, CLARO, ACENTO, cero, pct, guardar
   ```
3. **Córrelo con `--png`** desde la raíz del repo y mira la vista previa en `scripts/figuras/png/`.
4. **Insértala en LaTeX** con el bloque de `references/latex.md`, con su nota.
5. **Compila y revisa la página** (el visor: `python3 scripts/visor`): que quepan el
   caption y la nota, que la figura no haya movido páginas y que un número de la figura
   coincida con el texto.

## Las reglas que más se olvidan

- Sin título dentro; paneles como `(a) …` a la izquierda.
- Ancho = `ANCHO`, insertada a `\linewidth` sin escalar; nunca más de ~5.7 in de alto si
  lleva nota.
- Gris oscuro para lo principal, gris claro para la comparación, el acento solo para lo
  que el texto señala; capas encima de datos en `ACENTO_CLARO` y delgadas.
- Variables con cola larga: ni escala continua ni quintiles en mapas densos; resalta el
  20% más alto. Distribuciones con cola: acumulada.
- Cero punteado (`cero(ax)`), signo menos tipográfico (`menos()`, `pct()`), leyenda sin
  marco y afuera si tapa datos.
- Figuras paralelas con el mismo formato y en el mismo orden que su cuadro.

El detalle y el porqué de cada una están en `references/convenciones.md`.
