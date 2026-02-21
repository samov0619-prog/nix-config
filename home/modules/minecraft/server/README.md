# Управление сервером

## Запуск

```bash
systemctl --user start minecraft.target
```

## Перезапуск

```bash
systemctl --user restart minecraft.target
```

## Логи

```bash
journalctl --user -u minecraft-server -f
```

---

# Автостарт при логине (опционально)

Если хочешь автозапуск:

```bash
systemctl --user enable minecraft.target
```

Или добавь в модуль:

```nix
Install.WantedBy = [ "default.target" ];
```
