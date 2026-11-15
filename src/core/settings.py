"""Runtime configuration for Vocalize."""

import argparse
import os
from dataclasses import dataclass
from pathlib import Path

SAMPLE_RATE = 16000
BLOCK_SIZE = 1600
DEBOUNCE_S = 1.2
DEFAULT_RMS_THRESHOLD = 300.0
RU_MODEL_ENV = "VOCALIZE_MODEL_RU"
EN_MODEL_ENV = "VOCALIZE_MODEL_EN"
LEGACY_MODEL_ENV = "VOCALIZE_MODEL"

DEFAULT_MODELS = {
    "ru": Path("models/vosk-model-small-ru-0.22"),
    "en": Path("models/vosk-model-small-en-us-0.15"),
}
MODEL_SOURCES = {
    "ru": (
        "vosk-model-small-ru-0.22",
        "https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip",
    ),
    "en": (
        "vosk-model-small-en-us-0.15",
        "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip",
    ),
}


@dataclass(frozen=True)
class Settings:
    list_devices: bool = False
    device: int | None = None
    lang: str = "both"
    models: dict = None
    rms_threshold: float = DEFAULT_RMS_THRESHOLD
    dry_run: bool = False
    verbose: bool = True
    debounce_s: float = DEBOUNCE_S
    sample_rate: int = SAMPLE_RATE
    block_size: int = BLOCK_SIZE


def model_help(lang: str, path: Path) -> str:
    name, url = MODEL_SOURCES[lang]
    return (
        f"модель {lang} не найдена: {path}\n"
        "Скачайте её:\n"
        "  mkdir -p models\n"
        f"  curl -L -o models/{name}.zip {url}\n"
        f"  unzip models/{name}.zip -d models"
    )


def resolve_models(lang: str, ru_model: Path | None, en_model: Path | None) -> dict[str, Path]:
    models = {
        "ru": ru_model or _from_env(RU_MODEL_ENV, LEGACY_MODEL_ENV) or DEFAULT_MODELS["ru"],
        "en": en_model or _from_env(EN_MODEL_ENV) or DEFAULT_MODELS["en"],
    }
    if lang == "both":
        return models
    return {lang: models[lang]}


def _from_env(*names: str) -> Path | None:
    for name in names:
        value = os.environ.get(name)
        if value:
            return Path(value)
    return None


def load_settings(argv=None) -> Settings:
    parser = argparse.ArgumentParser(
        prog="vocalize",
        description="Голосовые команды нажимают медиа-клавиши play/pause, next и previous.",
    )
    parser.add_argument("--list-devices", action="store_true", help="показать устройства записи")
    parser.add_argument("--device", type=int, default=None, help="индекс микрофона из --list-devices")
    parser.add_argument("--lang", choices=("ru", "en", "both"), default="both", help="язык команд")
    parser.add_argument("--model", type=Path, default=None, help="каталог русской модели Vosk")
    parser.add_argument("--en-model", type=Path, default=None, help="каталог английской модели Vosk")
    parser.add_argument(
        "--rms-threshold",
        type=float,
        default=DEFAULT_RMS_THRESHOLD,
        help="порог громкости, ниже — тишина",
    )
    parser.add_argument("--dry-run", action="store_true", help="печатать команды и не нажимать клавиши")
    parser.add_argument("--quiet", action="store_true", help="скрыть покадровый TRACE")
    args = parser.parse_args(argv)
    return Settings(
        list_devices=args.list_devices,
        device=args.device,
        lang=args.lang,
        models=resolve_models(args.lang, args.model, args.en_model),
        rms_threshold=args.rms_threshold,
        dry_run=args.dry_run,
        verbose=not args.quiet,
    )
