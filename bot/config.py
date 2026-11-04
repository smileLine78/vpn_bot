from dataclasses import dataclass

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    bot_token: str
    admin_ids: str = ""

    xui_url: str
    xui_username: str
    xui_password: str
    xui_inbound_id: int = 1
    xui_flow: str = ""
    xui_verify_ssl: bool = True

    sub_base_url: str

    trial_days: int = 3
    trial_gb: int = 5

    # Оплата картой через Telegram Payments (токен провайдера из @BotFather)
    payment_provider_token: str = ""
    card_currency: str = "RUB"

    # Оплата криптой через CryptoBot (Crypto Pay API)
    crypto_pay_token: str = ""
    crypto_pay_api: str = "https://pay.crypt.bot/api"

    db_path: str = "data/bot.db"

    @property
    def admins(self) -> set[int]:
        return {int(x) for x in self.admin_ids.split(",") if x.strip()}


settings = Settings()


@dataclass(frozen=True)
class Tariff:
    key: str
    title: str
    days: int
    stars: int  # цена в Telegram Stars
    card: int  # цена картой в основных единицах CARD_CURRENCY (например, рубли)
    usdt: float  # цена в USDT через CryptoBot


# Цены — примерные, поменяйте под себя
TARIFFS: dict[str, Tariff] = {
    t.key: t
    for t in [
        Tariff("m1", "1 месяц", 30, 150, 199, 2.5),
        Tariff("m3", "3 месяца", 90, 400, 499, 6.5),
        Tariff("m12", "12 месяцев", 365, 1400, 1790, 22.0),
    ]
}
