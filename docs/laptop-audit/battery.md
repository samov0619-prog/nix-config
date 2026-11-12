# Lenovo: предупреждение и защита от разряда

## Согласованная policy

- NixOS: `hosts/laptop/battery.nix` включает штатный UPower, процентную policy и
  `CriticalPowerAction=Hibernate` при `PercentageAction=2`.
- HM: Lenovo Waybar предупреждает при 15%, критически уведомляет при 2%.
  Его события вызывают popup через `notify-send` и один стандартный сигнал
  `dialog-warning.oga` через `pw-play`, не запускают Hibernate. Warning имеет
  normal urgency, critical — critical; громкость/mute пользователя не меняются.
- Внутренний `PercentageCritical=5` UPower — уровень состояния, не порог действия.
  Сам демон не показывает уведомление на 5% и не усыпляет ноутбук на 3–5%.
- Действие UPower не зависит от работающего Waybar. Lid/logind, PPD, swap/resume,
  NVIDIA, аудио, VPN и authentication policy не меняются. Общие HM-тайминги
  уведомлений меняются также на Acer/desktop; power policy других хостов прежняя.
  Нового сборщика, таймера или запросов к GPU нет.

Штатный UPower сам наблюдает батарею; это не обещание полного отсутствия polling.
Отдельный сбор статистики, графики, температур и истории PPD пользователь отложил.

## Что означает порог 2%

Это небольшой резерв, а не гарантия успешного Hibernate при любой нагрузке,
погрешности оценки заряда, состоянии батареи и объёме памяти для записи.
UPower 1.91.5 ставит действие в очередь примерно на **20 секунд** после перехода
в action level. Показания/обновления UPower и Waybar могут различаться; точного
одновременного срабатывания по цифре на панели нет. Выход из action level отменяет
ожидающее действие.

При выборе действия UPower проверяет возможности logind: если Hibernate недоступна,
следующий штатный кандидат — **PowerOff**, а не гарантия сохранения сессии.
`AllowRiskyCriticalPowerAction` остаётся false. Нет своего countdown или обёртки,
обходящей эту политику. Не следует полагаться на приложение с inhibitor как на
способ отменить critical action: native backend запрашивает пропуск inhibitors.

Основание — source review версии 1.91.5:
[таймер и уровни](https://sources.debian.org/data/main/u/upower/1.91.5-1/src/up-daemon.c),
[выбор и выполнение действия](https://sources.debian.org/data/main/u/upower/1.91.5-1/src/linux/up-backend.c).
Это не live-тест низкого заряда.

## Всплывающее уведомление и звук

Пользователь сообщил, что видел красный мигающий значок на 15%, но не заметил popup
и звука. Звук ранее действительно не был задан: события вызывали один `notify-send`.
Mako работает в режиме `default`; пользователь увидел отдельный прямой тестовый popup.
Команда проигрывания стандартного сигнала также завершилась успешно, но это ещё
не подтверждение слышимого звука пользователем. Причина пропуска прежнего popup
не установлена; прошлое уведомление не объявляется ни доставленным, ни потерянным.

Общий helper `home/linux/modules/waybar/scripts/battery-notify.sh` подготовлен
для Lenovo и Acer; пороги сохранены: 15/2 и 30/15 соответственно.
Nix wrapper закрепляет пути notify-send, pw-play, notification-close и обычного
freedesktop sound; от Mako sound hints он не зависит. `suppress-sound` исключает
второй сигнал от поддерживающего hints daemon. Если popup не удаётся отправить,
попытка звука всё равно выполняется, а ошибка не скрывается. Нет daemon, battery
polling, таймера или новых power actions; события и повторные входы в уровни остаются
штатными Waybar. Multi-output deduplication не добавлена и не проверена.

Warning/critical имеют timeout 0: до ручного закрытия или события зарядки Waybar.
Они заменяют друг друга одним native tag, а не копятся. Зарядка закрывает только
категорию `device.power.low` приложения `Battery`, не чужие уведомления. Штатный
Waybar считает все статусы, кроме Discharging, charging events; добавленные состояния
normal/full покрывают 0–100%. Это не отдельное доказательство наличия зарядного
тока: Unknown/Not charging тоже идут по native charging-ветке. Закрытие происходит
при очередном наблюдении Waybar (интервал 30 секунд), не строго в момент подключения.
Battery Full показывается 3 секунды без звука. Без override от приложения общий
Mako timeout теперь 15 секунд на трёх Linux GUI-хостах; Mac/server не включаются.
Остальные правила и проверка диктовки — `home/linux/modules/notifications/README.md`.

Красное мигание задаёт CSS для `critical`. Раньше этот порог был 15%, сейчас 2%:
наблюдение на 15% совместимо со старым загруженным конфигом, но само по себе этого
не доказывает. На проверенной установке процесс называется `.waybar-wrapped`;
`pkill -USR2 -x waybar` его не выбирает. Нужен reload с обоими вариантами имени.

Безопасный ручной тест после применения HM:

```fish
~/.config/waybar/scripts/battery-notify test
```

Ожидаются popup «Battery notification test» и один обычный короткий сигнал.
Команда не читает и не подменяет заряд, не запускает Hibernate. Она проверяет
доставку/звук, но не реальное пересечение порога Waybar. Слышимость при mute/DND
и низкая батарея не гарантируются; настройки звука/режимы не обходятся.

Локальная проверка без вывода уведомлений или звука:

```fish
python3 -B home/linux/modules/waybar/tests/test_battery_notify.py
python3 -B home/linux/modules/notifications/tests/test_close.py
nix eval --impure --offline --json --option allow-import-from-derivation false --file home/linux/modules/waybar/tests/test-battery.nix
```

## Проверки и применение

Выбранные merged declarations проходят без сборки/IFD:

```fish
nix eval --impure --offline --json --option allow-import-from-derivation false --file hosts/laptop/tests/test-battery.nix
```

Проверены enable, пороги, generated UPower INI, Waybar thresholds и отсутствие
Hibernate в его events; сравнение с отключённым UPower сохраняет logind/PPD,
resume device, swap policy и NVIDIA module parameters. Это не native daemon,
реальная запись образа памяти или аппаратная low-battery acceptance.

На подготовительном read-only шаге logind ответил `CanHibernate=yes`. Один обычный
Hibernate/offload/idle цикл ранее принят пользователем; он не проверяет новый
автоматический триггер и достаточность резерва.

Пользователь применяет на Lenovo при достаточном заряде или подключённом питании:

1. NixOS: `sudo nixos-rebuild switch --flake .#laptop`.
2. Отдельно HM: `home-manager switch --flake .#samov-laptop`.
3. Перечитать Waybar: `pkill -USR2 -x 'waybar|\.waybar-wrapped'`.
4. Проверить без запуска действия:

   ```fish
   systemctl is-active upower.service
   busctl call org.freedesktop.login1 /org/freedesktop/login1 org.freedesktop.login1.Manager CanHibernate
   busctl call org.freedesktop.UPower /org/freedesktop/UPower org.freedesktop.UPower GetCriticalAction
   cat /etc/UPower/UPower.conf
   ```

   Ожидаются `active`, `s "yes"`, `s "Hibernate"` и пороги 15/5/2 с процентной policy.
   Если действие другое, сначала разобрать причину; не считать защиту принятой.
5. Уведомления и Hibernate наблюдать при обычной эксплуатации, сохраняя работу
   заранее. Не разряжать батарею специально и не подменять live-показания для теста.

Пользователь затем подтвердил применение и успешные проверки. Read-only проверка
12.11.2026 подтверждает active UPower, `GetCriticalAction` → `Hibernate` и installed
INI с процентной policy 15/5/2, без risky actions. Это приёмка установленной
конфигурации, не фактического low-battery trigger или достаточности 2%.
Агент не выполнял сборку, activation или намеренный разряд.
Документация сама activation не требует.

Для нового popup/sound helper нужен **только**
`home-manager switch --flake .#samov-laptop` и reload Waybar указанной командой;
уже принятую NixOS/UPower policy повторно применять не нужно. Mako перечитать через
`makoctl reload`. Десять mock-проверок реального helper покрывают уровни, charging
clear, full, один вызов player, безопасный test, неверный ввод и ошибки команд;
это не live Waybar threshold/audio acceptance. Агент не собирал и не применял
эту HM-правку. Затем 12.11.2026 пользователь отдельно подтвердил, что новые
уведомления его устраивают. Это пользовательская приёмка поведения на Lenovo,
не независимое UI/audio-наблюдение агента или проверка каждого battery threshold,
charging transition и фактического Hibernate на низком заряде.
