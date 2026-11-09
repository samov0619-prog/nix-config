# Запуск TUI: терминал, окружение и права

## Исправление открытия текстовых файлов

Общий Linux GUI module `home/linux/gui-set/xdg.nix` связывает `text/plain`
с отдельным `nvim-xdg.desktop`:

```desktop
Exec=kitty -- nvim -- %F
Terminal=false
NoDisplay=true
```

Первый `--` отделяет команду от опций Kitty, второй — файлы от опций Neovim.
`Terminal=false` здесь правильно: команда **сама** открывает терминал, launcher
не должен добавлять второй. `NoDisplay=true` скрывает дополнительный пункт меню,
но не мешает открывать файл через MIME association. Штатный `nvim.desktop`
остаётся: Tofi по-прежнему добавляет к его `Terminal=true` настроенный `kitty --`.
Pinned Tofi 0.9.1 явно исключает `NoDisplay` entries в
[`desktop_vec_add_file`](https://github.com/philj56/tofi/blob/v0.9.1/src/desktop_vec.c).

Это устраняет подтверждённую проблему installed xdg-utils 1.2.1:
generic-функция `search_desktop_file` игнорирует `Terminal=true` и запускает
прежний `Exec=nvim %F` без терминала. Правка касается Acer/desktop/Lenovo HM;
Mac/server, браузерные и архивные associations, внешний Neovim config и Mason
не меняются. Это не настройка всех возможных text MIME types.

## Где именно возникают различия

| Вход | Цепочка в конфигурации | Права и ограничения |
| ---- | --------------------- | ------------------ |
| `text/plain` через XDG | Новый handler → Kitty → Neovim | Обычный пользователь; launcher передаёт файлы, Fish не запускается |
| `Super+N` | Hyprland → Kitty → Neovim | Обычный пользователь, прямой запуск без Fish |
| `Super+E` | Hyprland → Kitty → `env EDITOR=nvim yazi` | Обычный пользователь, прямой запуск без Fish |
| `Super+Shift+E` | Hyprland → Kitty → sh → **sudo** → Yazi | Намеренно root; потенциально root и дочерние редакторы/команды |
| Tofi, пункт Neovim | Tofi добавляет `kitty --` → UWSM → Kitty → Neovim | Обычный пользователь; сложный quoted Exec имеет отдельный известный риск |
| FileManager1 | User D-Bus service → wrapper → Kitty → Yazi | User service, не системный root-daemon; окружение от user service manager |
| Обычное окно Kitty без команды | Kitty → Fish → вручную запущенный TUI | Интерактивный Fish читает `local-env.fish`, включена интеграция direnv |

Это source/declaration audit указанных путей, не полный аудит всех приложений
и не доказательство безопасности их внутренних команд/плагинов.

### Терминал не равен shell и не повышает права

Kitty предоставляет окну PTY — терминальный интерфейс, нужный TUI для ввода
и вывода. В `kitty -- nvim` запускается именно `nvim`, а не `fish -c nvim`.
`shell fish` в настройках Kitty выбирает shell **когда команда не задана**.
Shell aliases/functions и interactive init не применяются к прямому запуску.

Обычный дочерний процесс наследует UID/GID, окружение и cwd родителя;
терминал сам по себе не превращает пользователя в root. Переход прав требует
отдельного механизма: например, `sudo`, setuid или capabilities. В текущем
sudo-Yazi shortcut повышается Yazi, не сам GUI Kitty. Запущенный из root-Yazi
редактор/плагин тоже может работать как root. Запуск GUI из него дополнительно
может упереться в доступ к Wayland/D-Bus или создать root-owned файлы.

Этот shortcut и его F1-подсказка сохранены, не запускались в проверке.
Значения HOME/PATH/config после sudo зависят от sudo policy; наличие
`EDITOR=nvim` не гарантирует доступность пользовательского nvim в root PATH.
Не следует «чинить» это слепым `sudo -E`, переносом личных ключей в root
или запуском всего Kitty от root. Для отдельных административных файлов
обычно стоит рассмотреть `sudoedit` с пользовательским редактором отдельно;
текущий workflow без согласования не заменён.

### Окружение процесса не равно окружению проекта

- `home/core-set/shell.nix` читает доверенный unmanaged `local-env.fish`
  только в интерактивном Fish. Прямой Neovim/Yazi из GUI не выполняет этот код.
  Если переменная уже экспортирована родителем, она наследуется и без Fish;
  но экспорт в одном терминале не меняет compositor, соседние окна или службы.
- Пользовательские systemd/D-Bus службы получают окружение своего manager,
  не shell, из которого когда-то пришёл запрос. UWSM помогает управлять
  графической сессией, но не загружает за TUI произвольный `.envrc`.
- Открыть файл внутри проекта — не то же самое, что `cd` в проект и вход
  в одобренное direnv/devenv окружение. Новый handler намеренно не меняет cwd,
  не выполняет `.envrc` и не обходит `direnv allow`.
- Автоимпорт окружения при смене проекта в уже работающем Neovim — отдельная
  существующая todo-задача; эта правка её не реализует. Не добавлен Fish-wrapper
  ко всем TUI: это меняло бы startup, область доступа к ключам и trust boundary.

«Окружение» — перегруженное слово. Переменные процесса, shell/session setup,
проектный toolchain, venv и контейнер — разные уровни. Linux namespaces задают
изолированные представления ресурсов (PID, mount, network, user и другие).
Docker использует их вместе с cgroups, capabilities, seccomp, filesystem layers
и runtime/orchestration. «Docker — это namespaces» полезно как упрощение,
но не полное описание и не гарантия изоляции. Эта учебная тема сохранена отдельно.

## Проверки и границы

```fish
set desktop_file (mktemp /tmp/opencode/nvim-xdg.XXXXXX.desktop)
nix eval --impure --offline --raw --option allow-import-from-derivation false --file home/linux/gui-set/test-xdg-declarations.nix --apply 'profiles: profiles.samov-laptop.desktopText' > "$desktop_file"
python3 -B home/linux/gui-set/test_xdg_text.py --desktop-file "$desktop_file"
```

Nix evaluation проверяет выбранные merged declarations пяти HM-профилей и
возвращает настоящий generated desktop text из `makeDesktopItem/writeTextFile`
без реализации derivation. Проверяются scope, MIME association, `Terminal=false`,
скрытый handler, неизменные upstream Neovim entry, Yazi и HTML association.

Шесть Python tests выполняют **извлечённые настоящие функции installed xdg-open**
с этим desktop text, fake Kitty/nvim и изолированными HOME/PATH. Старый
`Exec=nvim %F`/`Terminal=true` contract служит контролем отсутствующего терминала.
Проверяются Kitty argv и передача имени файла в Neovim, пробелы, кириллица,
кавычки, literal shell characters, option-like имя, отсутствие смены UID/EUID,
cwd и синтетической exported переменной. Тест не читает личное окружение/ключи.
Три mutation controls ожидаемо отвергнуты: удаление Kitty из Exec,
`Terminal=true` и `NoDisplay=false`.

Fake Kitty только проверяет/передаёт argv; это **не** тест настоящего PTY,
отрисовки Kitty, runtime Neovim, Fish/direnv, sudo policy, полной MIME discovery,
нескольких файлов через `%F`, portal или браузера. Реальные команды sudo,
службы и GUI не запускаются. Полный HM build и installed layout оставлены
пользователю; после обновления xdg-utils тест требует review изменившихся функций.

## Применение и живая приёмка

1. Пользователь применяет HM: на Acer `home-manager switch --flake .#samov-laptop`;
   desktop использует `.#samov-desktop`. Lenovo draft на Acer не применять.
   NixOS rebuild и рестарт FileManager1 не нужны.
2. Проверить `xdg-mime query default text/plain`: ожидается `nvim-xdg.desktop`.
3. В обычном пользовательском Fish создать безопасный текстовый файл и открыть его:

   ```fish
   set check_dir (mktemp -d /tmp/opencode/xdg-text-check.XXXXXX)
   printf 'Neovim XDG check\n' > "$check_dir/текст с пробелами.txt"
   xdg-open "$check_dir/текст с пробелами.txt"
   ```

   Ожидается одно окно Kitty с Neovim и нужным файлом. В Neovim
   `:echo getpid()` покажет PID; в другом обычном терминале
   `ps -o pid,euid,egid,comm -p <PID>` должен показать UID/GID пользователя,
   не root. Закрыть Neovim через `:q`.
4. Проверить `Super+N`, `Super+E` и обычный пункт Neovim в Tofi: без лишнего
   второго терминала/дубликата пункта. Привилегированный shortcut для этого
   теста не нужен. Если требуется project environment, отдельно проверить
   запуск из уже подготовленного Fish; этот handler не обещает его автоимпорт.
