# DataVerse

**Explorations in data, statistics and visualisation.**

DataVerse is where I collect short, independent analytical projects published as part of **#SextaDeDados**. Each exploration starts with a question and develops it through data, code and statistical reasoning, with particular attention to how the results are communicated visually.

The subjects vary, from language and the humanities to urban and social data. Each project has its own methods, data sources and limitations.

## Explorations

| Project | What it explores | Materials |
| --- | --- | --- |
| **001 · Belo Horizonte property transactions** | Declared property values, spatial variation, quality-adjusted trends and clustering around round numbers in municipal ITBI records. | [Project notes](projects/001-bh-itbi/README.md) · [Notebook](projects/001-bh-itbi/dataverse_001.ipynb) |

## Exploring the work

Each project lives in a numbered directory under [`projects/`](projects/). Start with its README for the research question, data provenance, setup instructions and methodological limitations, then open the notebook to follow the analysis and its figures. Some projects require separately obtained data or map resources.

## Plotting style

The figures use the reusable Matplotlib style in [`src/dataverse_style/`](src/dataverse_style/).
For local development, `uv sync` installs the package in editable mode and includes the `dev` dependency group.

`Theme.accent` colours the header bar and is the default highlight for `plot_line` and
`plot_band`. `Theme.palette` independently defines the categorical cycle used by native
Matplotlib calls such as `ax.plot()` when they take a colour from the axes' cycle.
`editorial_subplots()` creates its axes with the figure theme's cycle. Other native defaults,
such as the font for new annotations, follow the current Matplotlib `rcParams`. Use `use()`
for session-wide defaults or `theme_context(get_theme(fig))` when adding native axes and
artists under a particular figure's theme. Native calls still accept explicit styles and
`ax.set_prop_cycle()`.

Package helpers resolve a supplied theme first, then the figure's theme, then the active
theme. `style_axes()` retains its resolved theme for the managed bottom spine on redraw
and export. Pass colours to individual helpers or use `Theme.line_style()` and
`Theme.band_style()` with native Matplotlib calls for more control.
