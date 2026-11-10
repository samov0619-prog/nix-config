# Штатный Polkit: Blueman и графический агент

## Что меняется

- NixOS Acer/Lenovo: overlay `blueman-polkit` добавляет Polkit в build inputs
  существующего stable Blueman и передаёт `--enable-polkit`. Версия, source,
  интерфейсы D-Bus и штатные policy/rules не заменяются. Overlay в `flake.nix`
  подключён только к `laptop`/`laptop-next`; desktop/server/installer и HM package
  sets его не получают. Обычный desktop по-прежнему без Bluetooth/Blueman.
- Linux GUI HM Acer/desktop/Lenovo: native `services.hyprpolkitagent.enable=true`.
  Штатный HM module запускает агент через user service, привязанный к
  `graphical-session.target` UWSM; нет отдельного `exec-once` или второго агента.
  Это интерфейс запросов Polkit для GUI-приложений, не Bluetooth pairing agent
  и не pinentry GPG. Mac/server HM не меняются.

Ранее в репозитории не было настроено ни hyprpolkitagent, ни polkit-gnome.
Узкий snapshot process names текущего пользователя также не нашёл Polkit agent;
это не аудит всех ручных autostart/environment overrides. Декларативный маршрут
теперь задан явно, но реальный запуск и диалоги ещё требуют приёмки.

## Штатная политика Blueman 2.4.6

Важное уточнение к первоначальному объяснению: Polkit здесь разграничивает
пользователей/сессии, а **не изолирует приложения одного пользователя**.

Upstream устанавливает четыре actions: `org.blueman.network.setup`,
`org.blueman.dhcp.client`, `org.blueman.pppd.pppconnect`,
`org.blueman.rfkill.setstate`. Их defaults — отказ неактивной сессии и
`auth_admin_keep` для активной. Но поставляемый upstream `blueman.rules`
**разрешает эти четыре actions группе wheel без пароля**, без дополнительного
условия active/local. Правило обрабатывается прежде defaults.

`samov` уже состоит в wheel на Acer/Lenovo, поэтому эта штатная льгота сохраняется.
Не обещается password prompt для этих действий samov или защита от всех процессов,
запущенных с его UID. Другие пользователи больше не обходят проверку только
потому, что Blueman был собран с `POLKIT=False`. Это не исправление доказанного
удалённого exploit и не изменение PIN/подтверждений при сопряжении BlueZ.

Не добавлены собственные allow-all rules, новые группы, sudo wrappers, PAM
изменения, второй Bluetooth manager, правила блокировки экрана или fingerprint.
Сужение штатной wheel-льготы было бы отдельной policy, сейчас оно не согласовано.

Источники для точной версии: [configure.ac](https://github.com/blueman-project/blueman/blob/2.4.6/configure.ac),
[actions](https://github.com/blueman-project/blueman/blob/2.4.6/data/configs/org.blueman.policy.in),
[wheel rule](https://github.com/blueman-project/blueman/blob/2.4.6/data/configs/blueman.rules).

## Проверки и границы

- `pkgs/blueman-polkit/test_verify.py`: девять небольших fixture tests настоящего
  install verifier, без импорта Blueman. Принимается включённая поддержка и
  неизменённая policy; отвергаются False, отсутствующий/non-boolean flag,
  отсутствующие/изменённые actions или rules.
- Отдельный отрицательный контроль отверг настоящий старый installed package
  по `POLKIT=False`; он не подменяет проверку нового результата сборки.
- `verify.py` включён в installCheck будущей сборки. Он читает AST установленного
  `Constants.py` (`POLKIT is True`), сравнивает action IDs/defaults с исходной
  policy и rules побайтно с upstream source. Ничего не вызывает через D-Bus,
  не запускает root helper/agent и не использует сеть. Это защита от silent
  fallback configure при недостающей `polkit-agent-1` зависимости.
- `test-declarations.nix` проверяет выбранные system declarations: неизменённые
  version/source/прежние configure flags, новый dependency/flag/installCheck,
  один пакет Blueman в system/D-Bus/systemd registration на обоих ноутбуках,
  прежние wheel admin identities и отсутствие собственных Blueman rules.
  Desktop и desktop-next сохраняют upstream package и отсутствие Blueman.
- `home/linux/gui-set/test-polkit-declarations.nix` проверяет три GUI HM:
  единственный ExecStart, WantedBy/PartOf/After graphical-session, отсутствие
  конкурирующего polkit-gnome и второго HM compositor start. Mac/server — без
  этого агента. Это declarations/recipe evidence, не запуск UI или authentication.
- Все выбранные declarations прошли отдельными ограниченными evaluation.
  Попытка общей baseline evaluation пяти HM profiles превысила 15 секунд;
  совместная system evaluation Lenovo+двух desktops — 25 секунд. Они не
  считаются успешными; после сужения system/HM проверки прошли.

Из корня репозитория, Fish, без builds/IFD:

```fish
python3 -B pkgs/blueman-polkit/test_verify.py
for host in laptop lenovo desktop desktopTemplate
    nix eval --impure --offline --json --option allow-import-from-derivation false --expr "(import ./pkgs/blueman-polkit/test-declarations.nix).$host"
end
for profile in samov-laptop samov-desktop samov-laptop-next samov-mac samov-server
    nix eval --impure --offline --json --option allow-import-from-derivation false --expr "(import ./home/linux/gui-set/test-polkit-declarations.nix).$profile"
end
```

На этапе реализации агент не запускал сборки/installCheck настоящего нового
package и не проверял installed layout или живой парольный диалог. Последующая
проверка Acer описана ниже; реальные действия Blueman и устройства всё ещё
не проверены. Сопряжения, адреса, scan/connect, network sharing/rfkill и Bluetooth
streams не читались/не менялись.

## Применение и приёмка

1. Пользователь проверяет diff. Минимальная сборка исправленного пакета с его
   installCheck: `nix build --no-link .#nixosConfigurations.laptop.pkgs.blueman`.
   Она не применяет систему или HM и агентом не запускалась.
   Lenovo draft на Acer не применять.
2. Завершить Bluetooth-передачи и применить NixOS:
   `sudo nixos-rebuild switch --flake .#laptop`. Это обновит Blueman/policies.
   Затем `home-manager switch --flake .#samov-laptop` добавит user agent.
   Desktop получает только HM-изменение: `home-manager switch --flake .#samov-desktop`.
3. Сохранив работу, выйти и войти в графическую сессию: это даст свежий
   Blueman applet и проверит штатный запуск агента. Затем
   `systemctl --user status hyprpolkitagent.service` должен показать active.
   Не добавлять параллельный ручной запуск агента, если штатный не запустился.
4. Проверить результат пакета без обращений к Bluetooth:

   ```fish
   set blueman_package (dirname (dirname (readlink -f /run/current-system/sw/bin/blueman-applet)))
   rg '^POLKIT = ' "$blueman_package"/lib/python*/site-packages/blueman/Constants.py
   test -f "$blueman_package/share/polkit-1/actions/org.blueman.policy"
   test -f "$blueman_package/share/polkit-1/rules.d/blueman.rules"
   ```

   Ожидается `POLKIT = True` и оба policy files; эти команды ничего не включают.
5. Для отдельной проверки диалога вручную запустить
   `pkexec /run/current-system/sw/bin/true`. Ожидается графический запрос, если
   нет уже действующей авторизации; после подтверждения выполняется только
   `true`. Один успешный exit code не доказывает графический prompt: tty fallback
   тоже возможен. Не включать Bluetooth networking или rfkill ради этой проверки.
   Привычное подключение выбранной периферии проверить отдельно, когда удобно.

## Последующая приёмка Acer

Пользователь показал `hyprpolkitagent.service` active/running и сообщил, что
`pkexec /run/current-system/sw/bin/true` запросил пароль. Это пользовательское
подтверждение запроса авторизации, не независимая агентская проверка отрисовки
диалога, введённого пароля или полного набора PAM-сценариев.

Read-only проверка текущего installed Blueman независимо подтвердила
`POLKIT=True`, четыре ожидаемых action IDs/defaults и наличие штатного wheel
rule с прежним содержимым. Это уже evidence installed результата на Acer,
не только декларации. Логи сборки/installCheck не исследовались; агент их
не запускал. Доступ конкретных пользователей к helper не вызывался/не проверялся.

Обрезанная строка `Failed to register with host portal` уточнена узким чтением
журнала агента: `Connection already associated with an application ID`.
Это ответ desktop portal о существующей app-ID association, не отказ Polkit.
Реальный эффект на прочие функции Qt/portal не проверен; ошибка не помешала
пользовательскому сценарию запроса пароля. Никакие portal/cache/environment
обходы или перезапуски не добавлены. [Отдельные границы portals](portals.md).
Desktop/Lenovo и реальные Bluetooth-подключения этим не приняты.

## Обновление пакета

При обновлении nixpkgs проверить штатный Blueman без override. Когда native
package сам имеет Polkit и проходит этот install verifier, удалить только
overlay/его подключения; агент и проверки нужны независимо. Новый configure
flag без проверенного результата или конфликт сборки не доказывает исправление.
