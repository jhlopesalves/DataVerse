# Belo Horizonte's housing market in ITBI records

[Notebook](dataverse_001.ipynb) · [Portfolio](../../README.md)

The notebook studies declared property values and tax bases, spatial price
patterns, characteristics-adjusted indices and round-number clustering. It
treats declared values and tax bases as administrative measures.
Filters, estimators and interval assumptions are explained beside the analysis.

## Reproduce locally

From the DataVerse root:

```bash
cd projects/001-bh-itbi
uv sync
```

Select `.venv/bin/python` in this directory as the notebook kernel and run the
notebook from here. The project has its own lockfile. Its house style is in
[`house_style.py`](house_style.py), which registers the IBM Plex fonts from the
repository's [`fonts/`](../../fonts/) directory for the session.

The dataset and base-map tiles are fetched on the first run and cached. The
repository keeps the notebook and the rendered PNGs; downloaded inputs, tile
caches and environments stay local.

## Input identity and attribution

- Source table: `pracadata/brazil-itbi`, `data/belo_horizonte_transactions.parquet`.
- Pinned revision: `5908d77ed56fc9adb6dbafaf2cb38f34245bcd76`.
- Included input: 516,725 Belo Horizonte records, January 2008–September 2026.
- Analysis period: 2016–2025, with narrower periods explicitly selected for individual figures.
- Input SHA-256: `386a922d539e78538cd31dd21f7f3ed32db7505ecc70d16a683f69aadf7dbe86`.

The pinned dataset card describes the transformations, geography and city-specific
terms. The municipal catalogue uses the `cc-by` label, and the dataset card
describes Belo Horizonte's source as CC BY 4.0. The publisher requests the credit
“Fonte: Prefeitura de Belo Horizonte, dados abertos” and identification of the work
as derived and unofficial. [Pinned dataset card](https://huggingface.co/datasets/pracadata/brazil-itbi/blob/5908d77ed56fc9adb6dbafaf2cb38f34245bcd76/README.md) · [Municipal ITBI catalogue](https://ckan.pbh.gov.br/dataset/0e13bf71-5355-47ce-8607-966413b08c0a)

The notebook displays aggregate tables and figures. The transaction Parquet
stays in the local cache. The publisher warns that source URLs and combinations
of transaction attributes can link rows back to the municipal records. The map
uses generalised street-face centroids and shows a value band for each face,
including faces with a single sale.

## Publication checks

- Confirm the municipal licence version, the terms that apply to redistribution
  of the harmonised data and required credit on public derivatives. Review the
  level of spatial detail in the map before release.
- Confirm how the municipal assessment rules and Tema 1.113 were applied during
  the study period before attributing the observed gap to a valuation rule.
  [Municipal legislation](https://fazenda.pbh.gov.br/legislacao/formkey.asp?key=17) · [STJ Tema 1.113](https://processo.stj.jus.br/repetitivos/temas_repetitivos/pesquisa.jsp?cod_tema_final=1113&cod_tema_inicial=1113&novaConsulta=true&tipo_pesquisa=T)
- Confirm the Esri World Topo Map conditions for fetching and caching tiles
  through Contextily, modifying the imagery and publishing the rendered maps.
  Both map figures carry a provider credit. Confirm the exact contributor
  attribution required for release. [Esri static-map terms](https://doc.esri.com/en/arcgis-online/latest/reference/static-maps.html)

## Outputs

[`figures/`](figures/) contains the ten rendered PNG figures (five compositions
in Brazilian Portuguese and English) produced by the notebook.
