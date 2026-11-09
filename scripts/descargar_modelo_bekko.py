# -*- coding: utf-8 -*-
"""Descarga Bekko durante el Build, sin cargar el modelo en memoria.

En Render: pip install -r requirements.txt && python scripts/descargar_modelo_bekko.py
Los archivos quedan en /opt/render/project/src/modelos/bekko (directorio de código).
"""
from pathlib import Path
from huggingface_hub import hf_hub_download

REPO = "hotchpotch/bekko-embedding-v1-a8m"
DESTINO = Path(__file__).resolve().parents[1] / "modelos" / "bekko"


def main():
    for nombre in ("onnx/model.onnx", "tokenizer.json"):
        ruta = hf_hub_download(repo_id=REPO, filename=nombre, local_dir=str(DESTINO))
        print("Preparado:", Path(ruta).relative_to(DESTINO),
              "MB:", round(Path(ruta).stat().st_size / 1024**2, 1), flush=True)
    modelo = DESTINO / "onnx" / "model.onnx"
    tokenizer = DESTINO / "tokenizer.json"
    if modelo.stat().st_size < 20_000_000 or tokenizer.stat().st_size < 1_000_000:
        raise RuntimeError("Archivos Bekko incompletos; build cancelado")
    print("BEKKO_ARCHIVOS_LISTOS", flush=True)


if __name__ == "__main__":
    main()
