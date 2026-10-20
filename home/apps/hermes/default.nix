# Hermes Agent / Home Manager — минимальные отклонения от upstream (18.10.2026).
# Источник значений по умолчанию: NousResearch/hermes-agent,
# hermes_cli/config_defaults.py и website/docs/getting-started/nix-setup.md.
# Upstream Home Manager module подключается отдельно в flake.nix.
# Здесь НЕТ пользовательских системных промптов, RLM, governor, MCP или принудительного workflow.
# Комментарии рядом с активными параметрами: ДЕФОЛТ → ИЗМЕНЕНИЕ → ПРИЧИНА.
# Поскольку flake следует за main, после обновления lock значения по умолчанию стоит сверять заново.
{ hermes-agent, ... }:
{
  imports = [
    hermes-agent.homeManagerModules.default
  ];

  # остальное без изменений
  programs.hermes-agent.enable = true; # HM default false → true: установить hermes CLI и HERMES_HOME; без этого программы нет в PATH.

  services.hermes-agent = {
    enable = true; # HM default false → true: декларативно управлять конфигом/состоянием Hermes.
    # Не включает фоновые процессы сам по себе: gateway.enable=false,
    # backend.mode="none" — уже дефолты HM. Поэтому их намеренно НЕ задаём.

    settings = {
      model = {
        provider = "openai-codex"; # Дефолт: нет выбранного провайдера → ChatGPT/Codex OAuth, БЕЗ OpenAI API key.
        default = "gpt-6.1-sol"; # Дефолт: модель не выбрана → Sol 6.1 High через ChatGPT OAuth; без ключа OpenAI API.

        # Автоповышение reasoning high → max намеренно не включаем:
        # - Нет штатного надёжного механизма определения сложности задачи в Hermes.
        # - Сложность часто выявляется только в процессе работы, а не из запроса.
        # - По имеющимся тестам Max стоит ~2.25x дороже при небольшом
        #   и пока статистически не подтверждённом приросте качества (50 → 52).
        # - Собственный LLM-классификатор добавит расходы, ошибки и техдолг.
        #
        # Пересмотрим, когда появится штатная адаптивная маршрутизация,
        # основанная на объективных сигналах (неудачные тесты, повторные
        # безуспешные попытки, обнаруженные противоречия), с ограничением
        # стоимости и доказанным улучшением качества на coding-бенчмарках.
        # До этого High — постоянный режим, без ручных переключений.
      };

      auth.adopt_external_logins = false; # Дефолт true → false: Hermes не трогает refresh-токены OpenCode/Codex CLI;
      # потребуется отдельный `hermes auth add openai-codex` (один раз).

      agent.reasoning_effort = "high"; # Дефолт medium → high: для ВСЕХ обычных задач; без ручного Max или дополнительного классификатора сложности.
      # Max нельзя автоматически выбирать по сложности штатной настройкой; не добавляем свой роутер.

      compression = {
        threshold_tokens = 225000;
        # Дефолт null → максимум 225K перед сжатием; стартуем в выбранном диапазоне 200–250K.
        # Реальный триггер = MIN(процентный порог модели, 225K): при окне 272K
        # встроенный минимум 75% даст ~204K; при окне 500K получится 225K.
        # Это НЕ жёсткий предел API, возможен overshoot на крупном результате инструмента.
        # Компактизатор Sol через тот же OAuth должен выдерживать источник + инструкции
        # + вывод: при фактическом окне 272K запас до потолка лишь ~47–68K.
        # Сначала проверить /context и фактический каталог модели.

        abort_on_summary_failure = true;
        # Дефолт false → true: при провале модели-компактизатора НЕ заменять
        # старую историю заглушкой «summary unavailable»; вместо этого остановить
        # автосжатие до ручной /compress, восстановления модели или новой сессии.
        # Это защита контекста, а НЕ гарантия отсутствия платного fallback.

        # ДЕФОЛТЫ HERMES, намеренно НЕ переопределяем (важно для cache/стоимости):
        # enabled = true;                  # штатная автокомпактизация ВКЛЮЧЕНА.
        # threshold = 0.50;               # базовый порог 50%; Hermes применяет >=75% для окон <512K.
        # codex_gpt55_autoraise = true;    # штатный Codex autoreset для перечисленных семейств; для Sol 6.1
        #                                 # не полагаемся на это правило: корректный порог берётся из окна модели.
        # tail_mode = "lean";             # штатная компактная сводка + короткий хвост + session_search.
        # target_ratio = 0.20;            # штатный бюджет свежей истории после сжатия.
        # proactive_prune_tokens = 0;     # ранняя без-LLM очистка tool history ВЫКЛЮЧЕНА по дефолту.
        #                                 # ВАЖНО: это не отключает compression.enabled и обычное сжатие на ~204–225K.
        #                                 # Включать дополнительно только при измеренной выгоде: ранняя очистка
        #                                 # переписывает префикс и может ухудшать prompt cache; есть issue о
        #                                 # потере/усечении деталей старых tool-calls в отдельных реализациях.
        # proactive_prune_min_reclaim_tokens = 4096; # штатный минимальный выигрыш, чтобы не ломать кэш по мелочи.
        # idle_compact_after_seconds = 0; # штатно не сжимать только из-за паузы; idle-сжатие тоже тратит токены.
        # micro_compact = false;          # штатно не переписывать историю после каждого хода (дорого для кэша).
        # checkpoint_required = false;    # НЕ включать без настроенного checkpoint-capable memory provider:
        #                                 # иначе любое lossy-сжатие может блокироваться.
        #
        # ВОЗМОЖНЫЙ ПОЗДНЕЙШИЙ ЭКСПЕРИМЕНТ (НЕ активен):
        # proactive_prune_tokens = 48000;             # проверять старый tool output при 48K.
        # proactive_prune_min_reclaim_tokens = 8192;  # записывать prune только при >=8K выигрыша.
        # Цена компромисса: cache miss и потенциальная потеря точных деталей истории.
      };

      auxiliary = {
        compression = {
          provider = "openai-codex"; # Дефолт "auto" → тот же ChatGPT OAuth; не подключать сторонний аккаунт.
          model = "gpt-6.1-sol";
          # Дефолт авто/основная модель → явная Sol 6.1; приоритет точности
          # и сохранения архитектурных ограничений, а не минимальной цены компрессии.
          reasoning_effort = "high"; # Дефолт effort провайдера → high для ответственной суммаризации.
          # Качество длинных сводок не гарантируется одним размером контекстного окна.
        };
        title_generation.enabled = false;
        # Дефолт true → false: не делать отдельный LLM-вызов за красивым названием;
        # одновременно отключаются автоматически улучшенные названия сессий.
        # Если нужны бесплатные простые заголовки, вместо этой строки поставить
        # title_generation.model_upgrade_enabled = false; (дефолт true).
        background_review.enabled = false;
        # Дефолт true → false: не запускать фоновый self-review с вызовами LLM
        # после пользовательского ответа; ручные функции обзора сохраняются.
      };

      # Делегирование не переопределяем: upstream наследует от основного агента
      # openai-codex / gpt-6.1-sol / high. Это не форсирует появление субагентов;
      # каждый запущенный субагент расходует отдельные токены. Нет дополнительного
      # Luna-роутера, который мог бы ошибаться на сложном поданализе.
      # delegation.fallback_providers = [ ]; # НЕ задаём; при отсутствии глобальной
      # fallback-цепочки нечего наследовать. Если её добавим — пересмотреть явно.

      # Не меняем toolsets, skills, memory, checkpoints, агентные промпты, разрешения,
      # кеширующие настройки провайдера и поведение CLI. Все они остаются upstream.
      # Провайдер сам кэширует совпадающий префикс; Hermes не управляет TTL OpenAI Codex OAuth.
      #
      # === ПОДКЛЮЧЕНИЕ НА БУДУЩЕЕ: комментарии, не активные маршруты ===
      # Аккаунты/ключи ниже сейчас НЕ нужны. Никогда не класть их в Nix/store/Git.
      #
      # 1) Недорогой официальный DeepSeek API, если Sol окажется слишком дорогой для вспомогательных задач:
      #    в ~/.hermes/.env (chmod 600): DEEPSEEK_API_KEY=...
      #    auxiliary.compression.provider = "deepseek";
      #    auxiliary.compression.model = "deepseek-flash";
      #    delegation.provider = "deepseek";
      #    delegation.model = "deepseek-flash";
      #    Перед включением перепроверить доступную модель, окно и реальные тарифы.
      #
      # 2) OpenRouter, если доступна действительно FREE-модель с окном >=225K + запас:
      #    в ~/.hermes/.env (chmod 600): OPENROUTER_API_KEY=...
      #    auxiliary.compression.provider = "openrouter";
      #    auxiliary.compression.model = "<актуальный-id>:free";
      #    delegation.provider = "openrouter";
      #    delegation.model = "<актуальный-id>:free";
      #    auxiliary.free_only = true; # Только страховка от ПЛАТНЫХ OpenRouter fallback,
      #                                # НЕ запрещает auxiliary переключиться на основную Sol.
      #
      # 3) Qwen OAuth: через `hermes model` выбрать авторизацию; затем проверить квоты,
      #    модель и доступный контекст ДО переключения auxiliary/delegation.
      #
      # 4) OpenCode Zen: требует отдельного OPENCODE_ZEN_API_KEY; бесплатный anonymous
      #    opencode-free не следует считать доступным стороннему Hermes-клиенту.
    };
  };
  # штатный Hermes CLI устанавливает programs.hermes-agent.enable.
}
