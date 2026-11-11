# Личные переменные окружения Fish

[Каталог](README.md) · [Решения](feedback.md)

Цель пользователя — один личный файл с API-ключами, подключаемый во всех новых
интерактивных Fish, независимо от текущего проекта. Для этого используется штатный
`source`, без собственного dotenv-парсера, нового пакета или project allow-list.

## Что управляется декларативно

[shell.nix](../../home/core-set/shell.nix) задаёт только подключение:

```fish
# Optional trusted Fish code, intentionally not managed by Nix/Home Manager.
# Manual setup (preserves existing content):
#   mkdir -p ~/.config/fish
#   touch ~/.config/fish/local-env.fish
#   chmod 600 ~/.config/fish/local-env.fish
# In ~/.config/fish/local-env.fish (permissions 600), add lines such as:
#   set -gx EXAMPLE_API_KEY 'replace-with-your-key'
# __fish_config_dir also respects a custom XDG_CONFIG_HOME.
if test -f "$__fish_config_dir/local-env.fish"
    source "$__fish_config_dir/local-env.fish"
end
```

По умолчанию это `~/.config/fish/local-env.fish`; при заданном `XDG_CONFIG_HOME`
используется Fish config directory из него. Файл необязателен. Home Manager его
**не создаёт, не перезаписывает и не удаляет**: нет `home.file`/`xdg.configFile`
entry или activation migration. Содержимое хранится вручную, вне Git/Nix store.
Другие управляемые Fish-файлы в том же каталоге не делают этот файл managed.

Это доверенный **Fish-код**, не `.env`: `source` способен выполнять команды.
Добавлять следует свои `set -gx NAME 'value'`, не подключать так файлы из чужих
репозиториев. Одинарные кавычки оставляют `$`, `=`, пробелы и скобки буквальными;
если значение содержит одинарную кавычку, внутри одинарных кавычек её экранируют
как `\'`, а буквальный обратный слеш — как `\\`.
Примерный ключ выше — не реальный секрет. Права `600` ограничивают чтение файла,
но не шифруют его и не скрывают экспортированные ключи от дочерних процессов.

## Ручная подготовка и применение

1. Создать файл, не затирая возможное существующее содержимое:

   ```fish
   mkdir -p ~/.config/fish
   touch ~/.config/fish/local-env.fish
   chmod 600 ~/.config/fish/local-env.fish
   nvim ~/.config/fish/local-env.fish
   ```

   При custom `XDG_CONFIG_HOME` использовать свой Fish config directory.
   Добавить строки `set -gx NAME 'value'` по необходимости. Старый
   `~/.config/llm-secrets/env` остаётся нетронутым, но **больше не загружается**:
   нужные записи перенести вручную, меняя синтаксис, а не просто имя файла.
   Агент настоящий файл с секретами не читает и не конвертирует.
2. Проверить синтаксис локально: `fish --no-config -n ~/.config/fish/local-env.fish`.
   Не отправлять содержимое или диагностику со значениями ключей в чат.
3. После review применить HM нужного хоста: на Acer
   `home-manager switch --flake .#samov-laptop-old`, на desktop/Mac — соответствующий
   профиль на своей машине; server HM — на VPS по SSH. Lenovo draft на Acer не применять.
   NixOS rebuild не нужен. Сам личный файл не переносится между машинами через Nix.
4. Открыть новый Fish. Для проверки наличия ключа без печати значения:
   `set -q EXAMPLE_API_KEY; and echo 'present'` (подставить имя своего ключа).
   Изменения не обновляют уже запущенные оболочки/службы; удаление строки из файла
   не отменяет переменную, уже экспортированную в работающий процесс.

## Проверки и границы

```fish
python3 -B home/core-set/tests/test_fish_local_env.py
nix eval --impure --offline --json --option allow-import-from-derivation false --file home/core-set/tests/test-fish-local-env.nix
```

Семь тестов запускают реальный Fish `--no-config` с hook, извлечённым из настоящего
Nix-модуля, во временном HOME. Только искусственные ключи: проверяются `=`, URL,
пробелы, пустые значения, кавычки/Unicode/буквальные shell-метасимволы, экспорт,
повторный запуск, сохранность содержимого/mode/inode/mtime и custom XDG path с
пробелами. Старый dotenv не читается; отсутствующий новый файл не создаётся.
Это запуск самого hook, не всей установленной HM Fish-конфигурации.

Выборочная merged HM evaluation подтверждает hook и отсутствие managed personal
file/родительского directory target во всех пяти профилях. Полные HM builds,
activation и загрузка настоящих ключей агентом не выполнялись.
