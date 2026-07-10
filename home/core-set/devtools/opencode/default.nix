# ─────────────────────────────────────────────────────────────────────────────
# OpenCode + RLM (Recursive Language Model) — декларативная интеграция.
#
# Что здесь настроено:
#
# 1. RLM-инструменты (идея arXiv «context as a variable in a REPL»):
#    - tool `rlm`      — грузит большой файл/каталог в Python-переменную `ctx`,
#                        код грепает/слайсит и print-ит ТОЛЬКО нужный срез
#                        (в контекст модели попадает лишь он → токены не пухнут).
#    - plugin `rlm_subquery` (toggle rlmRecursive) — отдаёт большой срез дешёвой
#                        суб-модели в изолированной сессии, назад берём лишь ответ.
#    Оба .ts зависят от zod. На NixOS файлы — симлинки в /nix/store, Bun резолвит
#    импорты из реального стор-пути → рядом с .ts вендорим node_modules/zod
#    (см. withZod). Ставим через xdg.configFile (каталог целиком), а НЕ через
#    programs.opencode.tools: тот принял бы derivation за attrs и развалился.
#    @opencode-ai/plugin НЕ импортируем — tool() это passthrough, а tool.schema=zod.
#
# 2. small_model = deepseek-v4-flash-free (НЕ дефолт):
#    дефолт для провайдера opencode захардкожен в gpt-5-nano (issue #8609),
#    а он платный на zen → 401 CreditsError на титулах/суммаризации. Явный
#    small_model перебивает эту ветку (getSmallModel: `if (cfg.small_model)`).
#    ВАЖНО: при смене main-модели на non-opencode провайдер — обязательно задать
#    и small_model на тот же залогиненный провайдер, иначе титулы утекут на zen.
#    NB: -free тиры на zen нестабильны; если titles/subquery начнут 401/молчать —
#    сперва проверь живость id: `opencode models | grep deepseek`.
#
# 3. package override — фикс file-watcher (libstdc++ через LD_LIBRARY_PATH).
#    Подробности — в комменте у самого override ниже.
#
# Смежное (в СИСТЕМНОЙ конфиге, не тут): programs.nix-ld со stdenv.cc.cc.lib —
# чинит ВНЕШНИЕ prebuilt-бинари (Mason-LSP для nvim). opencode-вотчер — не его
# класс (пропатченный бинарь), поэтому у него отдельный LD_LIBRARY_PATH-wrap.
#
# large-модель = big-pickle (осознанно): единственная реально проверенная в
# агентном режиме; flash/mini годятся для суб-вызовов, но не как драйвер агента.
#
# Проверка после правок: opencode run "ping" → без пустоты и без трейса rlm.ts;
# в свежем логе plugin rlm.ts loading + tool.registry rlm/rlm_subquery, титулы
# на deepseek-…-free без 401, file.watcher backend=inotify без ERROR.
# ─────────────────────────────────────────────────────────────────────────────

{ pkgs, lib, ... }:
let
  # ─── ПЕРЕКЛЮЧАТЕЛЬ RLM ──────────────────────────────────────────────────
  # false → только tool `rlm` (depth-0). true → + plugin-tool `rlm_subquery` (рекурсия).
  rlmRecursive = true;

  # zod вендорим РЯДОМ с tool/plugin: на NixOS файлы — симлинки в /nix/store,
  # Bun резолвит импорты из реального стор-пути, где иначе нет node_modules.
  # Обновить hash: nix store prefetch-file https://registry.npmjs.org/zod/-/zod-4.4.3.tgz
  zodTgz = pkgs.fetchurl {
    url = "https://registry.npmjs.org/zod/-/zod-4.4.3.tgz";
    hash = "sha256-7jjxf1M/1QBhBoWkg64vQTwm9OszpRaEMUVjyNYPJ5w=";
  };
  # Плоский каталог: <name>.ts и node_modules/zod — СОСЕДИ (Bun резолвит zod
  # от реального стор-пути вверх → находит ./node_modules/zod). node_modules
  # opencode как плагины/тулы не сканирует, так что .d.ts из zod не подхватятся.
  withZod =
    name: file:
    pkgs.runCommand "opencode-${name}" { } ''
      mkdir -p "$out/node_modules/zod"
      tar xf ${zodTgz} -C "$out/node_modules/zod" --strip-components=1
      cp ${file} "$out/${name}.ts"
    '';
in
{
  programs.opencode = {
    enable = true;
    # file-watcher opencode — нативный аддон (.node), слинкованный с libstdc++.
    # На NixOS его нет в стандартном пути → аддон падает на dlopen, вотчер
    # молча отключается (ERROR service=file.watcher ... libstdc++.so.6 ...),
    # и opencode не видит ВНЕШНИХ правок файлов (из nvim/git/форматтера).
    #
    # nix-ld тут НЕ помогает: он перехватывает dlopen только у непатченных
    # бинарей (интерпретатор /lib64/ld-linux…), а opencode из nixpkgs уже
    # пропатчен (nix-store ld.so) → идёт мимо nix-ld. Поэтому чиним через
    # LD_LIBRARY_PATH — его ld.so читает при dlopen у ЛЮБОГО процесса.
    #
    # Оборачиваем ВНУТРЕННИЙ .opencode-wrapped__ (external opencode — это уже
    # обёртка nixpkgs). Проверка держит ли фикс — только из чистого окружения:
    #   env -i HOME=$HOME PATH=/run/current-system/sw/bin (which opencode) run "ping"
    #   grep -iE "watcher|libstdc" <свежий лог>   # backend=inotify без ERROR
    # (если запускать из грязного шелла, libstdc++ может подтянуться транзитивом
    #  и замаскировать поломку — тестируй только через env -i.)
    package = pkgs.opencode.overrideAttrs (old: {
      nativeBuildInputs = (old.nativeBuildInputs or [ ]) ++ [ pkgs.makeWrapper ];
      postFixup = (old.postFixup or "") + ''
        for b in $out/bin/.opencode-wrapped__ $out/bin/opencode; do
          [ -e "$b" ] && wrapProgram "$b" \
            --prefix LD_LIBRARY_PATH : ${lib.makeLibraryPath [ pkgs.stdenv.cc.cc.lib ]}
        done
      '';
    });

    settings = {
      autoupdate = false; # пакет иммутабелен (Nix) — не качать апдейты
      autoshare = false;
      permission = {
        edit = "ask";
        bash = "ask";
      };

      # ─── МОДЕЛИ ───────────────────────────────────────────────────────────
      # Не заданы → дефолт opencode zen (big-pickle и пр.). Переключить декларативно:
      # раскомментируй строку и заведи креды `opencode auth login` (ключ ляжет вне store).
      # НЕ клади ключ в settings/sessionVariables — уйдёт в world-readable /nix/store.
      #   model = "anthropic/claude-sonnet-4-5";   # ANTHROPIC_API_KEY
      #   model = "deepseek/deepseek-chat";        # DEEPSEEK_API_KEY  ("deepseek-reasoner" — reasoning)
      #   model = "openai/gpt-5.5";                 # OPENAI_API_KEY
      # small_model — заголовки/суммаризация (и sub-модель RLM, если пинишь её в плагине):
      #   small_model = "anthropic/claude-haiku-4-5";
      small_model = "opencode/deepseek-v4-flash-free";
    };

    extraPackages = with pkgs; [
      python3
      ripgrep
      fd
    ];

    # Скилл — просто markdown, node_modules не нужен → оставляем через модуль.
    skills.rlm = ./rlm-skill.md; # → ~/.config/opencode/skills/rlm/SKILL.md
  };

  # tools/plugin ставим НАПРЯМУЮ (каталог с node_modules/zod), а не через
  # programs.opencode.tools: тот принимает либо path-литерал, либо attrs, а derivation
  # он ошибочно примет за attrs и развалится.
  xdg.configFile."opencode/tools".source = withZod "rlm" ./rlm-tool.ts;
  xdg.configFile."opencode/plugin" = lib.mkIf rlmRecursive {
    source = withZod "rlm" ./rlm-plugin.ts;
  };
}
