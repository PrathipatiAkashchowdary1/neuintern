from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "NeuIntern API"
    environment: str = "development"
    port: int = 8000

    jwt_secret: str = "dev_secret_change_me"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60 * 24 * 7  # 7 days

    cors_origin: str = "*"  # comma-separated list, or "*"

    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""

    database_url: str = "sqlite:///./neuintern.db"

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "NeuIntern <contact@neuintern.in>"
    contact_notify_email: str = "contact@neuintern.in"  # where contact form submissions are sent

    otp_expiry_minutes: int = 10
    otp_verification_valid_minutes: int = 30

    @property
    def cors_origins(self) -> list[str]:
        if self.cors_origin.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origin.split(",") if o.strip()]

    @property
    def razorpay_configured(self) -> bool:
        return bool(
            self.razorpay_key_id
            and self.razorpay_key_secret
            and "YOUR_" not in self.razorpay_key_id
            and "YOUR_" not in self.razorpay_key_secret
        )
    @property
    def smtp_configured(self) -> bool:
        return bool(self.smtp_host and self.smtp_user and self.smtp_password)


settings = Settings()
