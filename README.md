# Vocalize

Голосовые команды нажимают те же медиа-клавиши, что и кнопки на клавиатуре: play/pause, next, previous. Какой плеер их получит, решает операционная система.

## Установка

Зависимости ставятся только в `.venv` в корне репозитория:

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

Модели распознавания в git не входят. Нужны русская и английская модели Vosk:

```bash
mkdir -p models
curl -L -o models/vosk-model-small-ru-0.22.zip \
  https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip
curl -L -o models/vosk-model-small-en-us-0.15.zip \
  https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip models/vosk-model-small-ru-0.22.zip -d models
unzip models/vosk-model-small-en-us-0.15.zip -d models
```

На Linux Vocalize создаёт виртуальную клавиатуру через `/dev/uinput` (стандартная библиотека, без пакета `evdev`: ему для сборки нужен `python3-dev`). Если при запуске нет прав:

```bash
sudo tee /etc/udev/rules.d/99-vocalize-uinput.rules >/dev/null <<'EOF'
KERNEL=="uinput", GROUP="input", MODE="0660", OPTIONS+="static_node=uinput"
EOF
sudo udevadm control --reload-rules && sudo udevadm trigger
sudo usermod -aG input "$USER"
```

После `usermod` нужно выйти из сессии и зайти снова.

## Запуск

```bash
.venv/bin/vocalize --list-devices
.venv/bin/vocalize --dry-run
.venv/bin/vocalize
.venv/bin/vocalize --device 1 --rms-threshold 400
.venv/bin/vocalize --lang en
.venv/bin/vocalize --lang ru
```

По умолчанию слушаются оба языка. `--model` и `VOCALIZE_MODEL` / `VOCALIZE_MODEL_RU` задают русскую модель, `--en-model` и `VOCALIZE_MODEL_EN` — английскую.

В терминале:

- `[HEARD]` — распознанный текст
- `[ACTION]` — нажатая команда: `play_pause`, `next`, `previous`
- `[SKIP]` — та же команда повторилась раньше чем через 1.2 с
- `[ERROR]` — клавишу отправить не удалось

Команды по-русски: «пауза», «стоп», «играй», «включи», «дальше», «следующий», «назад», «предыдущий». По-английски: play, pause, stop, next, skip, forward, previous, back. Ctrl+C останавливает программу и убирает виртуальную клавиатуру.

## Проверка

```bash
.venv/bin/pytest
```

Руками: запустите музыку и скажите «дальше» и «пауза». Реакция должна совпасть с кнопками клавиатуры. На Windows код шлёт `VK_MEDIA_*` через `SendInput`; на этой машине проверяется только Linux.
