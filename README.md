# VPN Telegram bot (3x-ui)

Бот на aiogram 3: пробный период, оплата Stars / картой / криптой, выдача и продление клиентов в 3x-ui через API, ссылка-подписка, статистика для админов.

## Запуск

```bash
cp .env.example .env      # заполнить значения
docker compose up -d --build
docker compose logs -f bot
```

## Что нужно в 3x-ui
1. Создать inbound (например VLESS + Reality) и записать его ID в `XUI_INBOUND_ID`.
2. Включить подписку: Настройки панели → Подписка. `SUB_BASE_URL` = адрес подписки без subId.
3. `XUI_URL` — адрес панели вместе с webBasePath.

## Способы оплаты
Тарифы и цены — в `bot/config.py` (`TARIFFS`). Способ показывается, только если задан его токен в `.env`:
- **Telegram Stars** — работает всегда, токены не нужны.
- **Картой** — `PAYMENT_PROVIDER_TOKEN` из @BotFather (Payments), валюта в `CARD_CURRENCY`.
- **Криптой (USDT)** — `CRYPTO_PAY_TOKEN` из @CryptoBot. Счета опрашиваются раз в 15 секунд, домен и webhook не нужны.

## Команды админа
- `/stats` — статистика
- `/give <tg_id> <дней>` — выдать/продлить подписку вручную

## Структура
- `bot/xui.py` — клиент API 3x-ui
- `bot/services.py` — выдача/продление подписки
- `bot/db.py` — SQLite (пользователи, платежи)
- `bot/handlers/` — пользователь, оплата, админка
