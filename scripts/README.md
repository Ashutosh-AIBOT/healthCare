# Learn data imports

Large source files are intentionally not committed to Git. Download them to a
private working directory, review their license, then import them with the
scripts in this directory.

## Official sources

- MedlinePlus Web Service: https://medlineplus.gov/about/developers/webservices/
- USDA FoodData Central downloads: https://fdc.nal.usda.gov/download-datasets/
- ICMR-NIN Indian Food Composition Tables: https://www.nin.res.in/ebooks/IFCT2017.pdf
- India MoHFW NCD screening guidance: https://www.mohfw.gov.in/sites/default/files/Operational%20Guidelines%20on%20Prevention%2C%20Screening%20and%20Control%20of%20Common%20NCDs_1.pdf

Do not use an unlicensed Kaggle/Hugging Face health dataset as a clinical
source. Those datasets may be useful for experiments, but published Learn
content must retain a first-party source, version, license, and review status.

## Import a reviewed CSV

The CSV importer accepts `name` or `title` plus optional columns such as
`summary`, `content`, `calories`, `protein_g`, `carbohydrates_g`, `fat_g`,
`fiber_g`, and `serving_size`. It stores each row as a Learn food item and
records provenance in `learn_sources`.

```bash
cd backend
PYTHONPATH=. ../backend/.venv/bin/python ../scripts/import_learn_data.py \
  --food-csv /private/path/reviewed-foods.csv \
  --source-name "USDA FoodData Central" \
  --source-url "https://fdc.nal.usda.gov/" \
  --source-version "2026-04" \
  --license "USDA public data"
```

## Import official MedlinePlus seed content

This downloads a small set of health-topic records through the official XML
service and stores the cleaned content in the `test_info` Learn category. It
is intentionally term-based so it can be reviewed before expanding coverage.

```bash
cd backend
PYTHONPATH=. ../backend/.venv/bin/python ../scripts/import_medlineplus.py
```

The importer is idempotent by source and slug. Run migrations first:

```bash
cd backend
alembic upgrade head
```
