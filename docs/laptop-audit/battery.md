# Lenovo: предупреждение и защита от разряда

## Согласованная policy

- NixOS: `hosts/laptop/battery.nix` включает штатный UPower, процентную policy и
  `CriticalPowerAction=Hibernate` при `PercentageAction=2`.
- HM: Lenovo Waybar предупреждает при 15%, критически уведомляет при 2%.
  Его события только вызывают `notify-send`, не запускают Hibernate.
- Внутренний `PercentageCritical=5` UPower — уровень состояния, не порог действия.
  Сам демон не показывает уведомление на 5% и не усыпляет ноутбук на 3–5%.
- Действие UPower не зависит от работающего Waybar. Lid/logind, PPD, swap/resume,
  NVIDIA, аудио, VPN и authentication policy не меняются; Acer/desktop сохраняют
  прежние настройки. Нового сборщика, таймера или запросов к GPU нет.

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
3. Если Waybar не перечитал конфигурацию: `pkill -USR2 -x waybar`.
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
