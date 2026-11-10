# GitHub CLI: timeout keyring и pinentry

## Вывод на 10.11.2026

Воспроизведённый пользователем сценарий — первая проверка `gh` не видит авторизацию
ещё до завершения ввода в pinentry, пользователь заканчивает ввод после ошибки,
немедленный повтор работает без pinentry — хорошо объясняется **timeout чтения keyring в `gh`**, а не
утратой авторизации или слишком коротким временем GPG-кеша.

Подтверждены реализация установленной версии, живой provider и пользовательское
воспроизведение cold/warm-сценария. Агент не выполнял authentication и не снимал
D-Bus trace; точное число/порядок lookup остаётся выводом из source, а не трассировки.

## Проверенные звенья

1. Установлен `gh 2.96.0 (nixpkgs)`, команда из `~/.nix-profile/bin/gh`.
   [Локальный модуль](../../home/core-set/devtools/github.nix) только включает `gh`;
   wrapper/token configuration в проверенных `home/` sources не найден.
   В окружении **агента** GH/GITHUB token variables и `GH_CONFIG_DIR` отсутствуют.
   Это не утверждение об окружении каждого пользовательского Fish.
   Проверено лишь существование `config.yml`/`hosts.yml`, их содержимое не читалось.
2. D-Bus name `org.freedesktop.secrets` принадлежит процессу с тем же PID, что и
   активный `pass-secret-service.service` (`Type=dbus`, `WantedBy/PartOf=default.target`).
   Значит, живой Secret Service provider — именно pass-secret-service, не GNOME Keyring.
3. [Исходник `gh v2.96.0`](https://github.com/cli/cli/blob/v2.96.0/internal/keyring/keyring.go#L36-L59)
   оборачивает каждое `Get` в goroutine и `time.After(3 * time.Second)`.
   Ошибка — `timeout while trying to get secret from keyring`.
   Это фиксированный timeout **одного обращения**, не общий лимит всей команды:
   возможны несколько чтений, fallback и отдельная проверка GitHub API.
   Wrapper не передаёт отмену нижележащему вызову при срабатывании таймера.
4. `gh` использует `github.com/zalando/go-keyring v0.2.8`; его
   [Linux provider](https://github.com/zalando/go-keyring/blob/v0.2.8/keyring_unix.go)
   обращается к Secret Service, включая поиск/unlock/`GetSecret`.
   В установленном pass-secret-service `0-unstable-2023-12-16` проверены только
   package-owned Python sources: `interfaces/item.py:52–58,101–111`,
   `interfaces/service.py:184–205`, `common/pass_store.py:89–93`.
   `GetSecret` вызывает `_get_password` → `pypass.PasswordStore.get_decrypted_password`;
   `Locked` item возвращает false, `Unlock` возвращает prompt `/`.
   Следовательно, ожидание GPG/pinentry может происходить **внутри `GetSecret`**,
   а не как отдельный видимый Secret Service unlock-dialog.
5. [AuthConfig.ActiveToken](https://github.com/cli/cli/blob/v2.96.0/internal/config/config.go#L237-L266)
   сначала проверяет env/config, затем user-specific keyring, при ошибке — legacy
   keyring. Ошибка чтения может оставить пустой токен. Поэтому «не авторизован»
   не доказывает, что сохранённого токена нет или он отозван.

Вероятная последовательность: `gh` запрашивает секрет → GPG запускает pinentry →
один keyring lookup не успевает за три секунды → `gh` не получает токен для этого
запуска. Ввод пароля может тем временем прогреть GPG cache, и следующий запуск
получает секрет быстро. Точный порядок fallback/dialog/process exit не трассировали.

[Текущая GPG policy](../../home/core-set/security.nix) задаёт default/max cache TTL
3600 секунд. `noAllowExternalCache` запрещает внешний pinentry cache, **не** внутренний
cache gpg-agent. Часовой TTL не заставляет `gh` ждать час и не отменяет его timeout.
Увеличение TTL само по себе не исправляет первый cold lookup.

## Минимальная ручная проверка, если нужна

**Уже выполнена пользователем 10.11.2026:** два последовательных `time gh auth status`
в одном терминале, без `--hostname`. Первый завершился с exit 1 за **6.40 secs**
и сообщением `The token in default is invalid.` ещё до завершения ввода пароля.
Пользователь закончил ввод и нажал Enter после ошибки. Повтор за **681.98 millis**
успешно показал авторизацию из `keyring`, без нового pinentry. Полный account/token
output сюда не копируется. Времена совместимы с двумя ожиданиями по три секунды,
но сами по себе не доказывают точное количество вызовов. Повторять этот тест ради
того же evidence не требуется; успешный второй запуск подтверждает работоспособность
полученного токена на момент проверки, перелогин не нужен.

Ниже сохранена процедура для нового релевантного симптома или проверки будущего fix.
Не сбрасывать GPG cache ради теста. Дождаться естественного cold state и выполнить
в своём обычном терминале:

1. `time gh auth status --hostname github.com` — ввести пароль в pinentry обычным
   темпом; записать исход и примерное время. Не добавлять `--show-token` или debug logging.
2. Сразу повторить ту же команду. Cold failure после ожидания и warm success
   дополнительно поддержат диагноз; это не измерение точного D-Bus вызова.
3. Если повтор тоже неуспешен, не перелогиниваться автоматически: отдельно отличить
   проблему keyring от сети/API/отозванного токена. Для обсуждения достаточно исхода
   и времени; токен и private config присылать не нужно.

Это инструкция пользователю, **не выполненная агентом проверка**. `gh auth status`
может обращаться к GitHub API. Агент не запускал credential-using команды,
`gh auth token`, login/logout, GPG cache reset или secret retrieval; чтение public
upstream sources само по себе не проверяет действительность пользовательского токена.

## Что менять сейчас

**Upstream fix уже есть:** исходный timeout добавлен в
[PR #7580](https://github.com/cli/cli/pull/7580) против зависающих keyring calls
на Windows/WSL, не как ограничение времени ввода пароля для безопасности.
[PR #13787](https://github.com/cli/cli/pull/13787) увеличил `Get`/`Set`/`Delete`
с 3 до 60 секунд; это подтверждено в
[source `gh v2.97.0`](https://github.com/cli/cli/blob/v2.97.0/internal/keyring/keyring.go).
Минутное ожидание не обходит пароль и не меняет cache TTL, но замедляет отказ при
действительно зависшем backend; несколько lookup могут суммировать эти ожидания.
API go-keyring не сообщает `gh` прогресс. У текущего pass-secret-service pinentry
возникает внутри `GetSecret`, без отдельного prompt из `Unlock`, поэтому отличить
ввод пользователя от зависания простым осмотром ответа нельзя. Поиск чужого процесса
pinentry не является надёжным решением.

Пользователь откладывает изменение пакета до полного input update перед установкой
Lenovo. Если выбранный `gh` содержит upstream fix, локальный patch не нужен;
свежая установка со старым lock сама по себе версию не обновляет. [План](lenovo-checklist.md).
Повтор после успешного pinentry — временный обход, не полноценный fix и не повод
просить пользователя вводить пароль за три секунды. У wrapper в просмотренном
source v2.96.0 нет параметра timeout; токен не переносить в plaintext/env ради обхода.
Не добавлены wrapper, patch, credential fallback или новый keyring.

Только документация; NixOS/HM switch и service restart не нужны.
