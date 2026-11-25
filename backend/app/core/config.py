from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "NeuIntern API"
    environment: str = "development"
    port: int = 8000

    jwt_secret: str = "dev_secret_change_me"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60 * 24 * 7  # 7 days

    cors_origin: str = "*"  # comma-separated list, or "*" (development only)

    # Browser sessions: the JWT lives in an httpOnly cookie so page scripts (XSS)
    # can never read it. Secure defaults to on in production.
    session_cookie_name: str = "neuintern_session"
    cookie_secure: bool | None = None  # None = on when ENVIRONMENT=production
    cookie_samesite: str = "lax"  # "none" only if the site and API are on different domains
    cookie_domain: str = ""  # e.g. .neuintern.in to share across subdomains; empty = API host only

    # Password for the seeded admin account. Required in production (the built-in
    # default is public in the README and would be refused).
    admin_password: str = ""

    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    # Set in Razorpay Dashboard > Webhooks (separate from the API key secret).
    razorpay_webhook_secret: str = ""

    database_url: str = ""

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "NeuIntern <contact@neuintern.in>"
    contact_notify_email: str = "contact@neuintern.in"  # where contact form submissions are sent

    # Reminder emails to students who enrolled but have not paid. Off by
    # default so deploying never emails existing students unexpectedly; use the
    # admin dry run first, then set REMINDERS_ENABLED=true.
    reminders_enabled: bool = False
    frontend_url: str = "https://neuintern.in"  # base for links in emails (www redirects here)
    # Public URL of THIS API (e.g. https://api.neuintern.in). Only used for the
    # one-click List-Unsubscribe email header; omitted when empty.
    api_public_url: str = ""

    # Program images uploaded from the admin portal. Relative paths are
    # relative to backend/. On hosts with ephemeral disks, point this at a
    # persistent volume or the images disappear on redeploy.
    upload_dir: str = "uploads"
    max_upload_mb: int = 3

    otp_expiry_minutes: int = 10
    otp_verification_valid_minutes: int = 30

    @property
    def is_production(self) -> bool:
        return self.environment.strip().lower() == "production"

    @property
    def session_cookie_secure(self) -> bool:
        return self.is_production if self.cookie_secure is None else self.cookie_secure

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
