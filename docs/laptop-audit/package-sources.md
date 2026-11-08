# Источники пакетов: исключения из stable

Срез **09.11.2026**, read-only исследование для подготовки Lenovo. Пакеты, inputs,
`flake.lock` и существующие профили не изменены. Это не проверка сборки или runtime.

## Сопоставленные снимки

Root input `nixpkgs` в lock ссылается на узел **`nixpkgs_2`**, не `nixpkgs`.
Последний является транзитивным input; нельзя считать его stable текущих профилей.
Root mapping и версии locked packages сверены коротким offline `nix eval` без IFD
и реализации derivations. Свежий stable проверен по HTTP-исходникам на фиксированном
commit ветки `nixos-26.05`, без обновления lock и Git network operations.

| Снимок               | Revision                                   | Yazi   | Swayimg | compress |
| -------------------- | ------------------------------------------ | ------ | ------- | -------- |
| Root locked stable   | `0ad6f47ea4fe188f4bc8f0380f93ae8523337c6c` | 26.5.6 | 4.7     | 0.6      |
| Root locked unstable | `f3a77a0c9b182bf55b71c8f22f99725f38b69a3e` | 26.9.1 | 5.6     | 0.6      |
| Свежий `nixos-26.05` | `c56a87d8e41ce69bd2af57eb35dcc117a9dfca33` | 26.5.6 | 4.7     | 0.6      |

Версия Yazi берётся из `yazi-unwrapped`, а не из wrapper `yazi`. Исходники свежего
stable: [Yazi](https://github.com/NixOS/nixpkgs/blob/c56a87d8e41ce69bd2af57eb35dcc117a9dfca33/pkgs/by-name/ya/yazi-unwrapped/package.nix),
[Swayimg](https://github.com/NixOS/nixpkgs/blob/c56a87d8e41ce69bd2af57eb35dcc117a9dfca33/pkgs/by-name/sw/swayimg/package.nix),
[compress](https://github.com/NixOS/nixpkgs/blob/c56a87d8e41ce69bd2af57eb35dcc117a9dfca33/pkgs/by-name/ya/yazi/plugins/compress/default.nix).
Это версии определений пакетов, не inventory установленных приложений.

## Yazi и compress: происхождение и граница совместимости

- [Выбор unstable](../../home/core-set/shell.nix) присутствует уже в первом коммите
  `6399ae7`; отдельной причины в доступной истории нет. Это не доказательство
  необходимости unstable и не основание считать выбор ошибочным.
- `d01d460` (`fix compress yazi (workaround)`) добавил три точечные замены API;
  сам выбор unstable появился раньше и этим коммитом не объясняется.
- В обоих каналах plugin остаётся на одном upstream tag `0.6` с одинаковым source
  hash. Употребление `pkgsUnstable.yaziPlugins.compress` само по себе не означает
  более новую версию plugin.
- [Upstream compress 0.6](https://github.com/KKV9/compress.yazi/blob/0.6/main.lua)
  использует `u.parent` при обходе выделенных файлов и `fs.unique_name()`.
- [Yazi changelog](https://github.com/sxyazi/yazi/blob/v26.9.1/CHANGELOG.md):
  в **26.8.15** `tab::Selected.__pairs()` начал возвращать `File` вместо `Url`.
  Поэтому локальная замена `u.parent` на `u.url.parent` соответствует новому API,
  а не является универсальной правкой для старого stable **26.5.6**.
- `fs.unique()` появился уже в **26.5.6**; `fs.unique_name()` тогда deprecated
  из-за TOCTOU race. Эти две замены нельзя объединять с первой под предположением,
  что весь workaround нужен только unstable или полностью не нужен stable.

**Рекомендация, не новый пользовательский выбор:** пока сохранить рабочую связку
Yazi/patch. Если решим перейти на stable только на Lenovo, отдельно адаптировать
plugin к его API и проверить выделение одного/нескольких файлов, создание обычного
и password-архива, извлечение и отсутствие перезаписи существующего результата.
Ни downgrade, ни эти функциональные проверки в данном шаге не выполнялись.

## Swayimg: конкретная зависимость от нового формата конфигурации

Модуль появился в `e31a9b0` (`linux/core-set: add swayimg image viewer for yazi`)
сразу с unstable и [Lua-конфигурацией](../../home/linux/modules/swayimg/swayimg.lua).
Commit объясняет добавление просмотрщика, но отдельно выбор канала не обосновывает.

Здесь есть проверяемая причина не переключать пакет вслепую:
[release 5.0](https://github.com/artemsen/swayimg/releases/tag/v5.0) впервые добавил
Lua scripting и явно изменил формат конфигурации на Lua. Stable **4.7** не подходит
для текущего `swayimg/init.lua`; его Nix-определение также не содержит LuaJIT.
Locked unstable **5.6** содержит LuaJIT и выбран текущим модулем.

**Рекомендация:** сохранить unstable для существующего Lua workflow. Переход на
4.7 потребует отдельного переноса конфигурации, а не простой замены `pkgsUnstable`
на `pkgs`. Реальный запуск, directory navigation, zoom и drag здесь не проверялись.

## Что не является активной установкой из unstable

Ограниченный поиск активных `.nix` в `home/` и `hosts/`, сверенный с композициями,
выявил две группы прямых package consumers выше. Не смешивать с ними:

- Amnezia: ссылки `pkgsUnstable.amnezia-vpn.version` в hosts служат warning об
  обновлении. Сам пакет — локальный override, не установка upstream unstable.
- Chrome: отдельный input `browser-previews`, не `pkgsUnstable`.
- Freesm: собственный overlay/input.
- OpenCode: отдельный pinned input; старый unstable consumer в `archive/v1`
  не импортируется активной конфигурацией.
- Blender: обычный `pkgs.blender`.

Это не полный аудит транзитивных зависимостей или всех внешних source pins.
Сравнение fresh Node LTS и дальнейшие аппаратные/storage/security решения остаются
отдельными шагами; здесь не делается вывод об их готовности.

## Проверки и применение

Проверены локальная Git-история, root mapping lock, locked package attributes,
фиксированные HTTP-исходники свежего stable и upstream changelog/release notes.
Совместимость установленных приложений, UI и архивирование не испытывались.
Builds, activation, update, облачные/VPN операции не запускались.

Изменена только документация: **NixOS/Home Manager activation не нужна**.
Следующий шаг — уточнение платформы Lenovo и поддержки thermald; решения о замене
пакетов требуют отдельного согласования и не должны менять Acer автоматически.
