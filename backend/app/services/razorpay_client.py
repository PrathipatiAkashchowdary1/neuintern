import razorpay

from app.core.config import settings


def get_client() -> razorpay.Client:
    return razorpay.Client(
        auth=(
            settings.razorpay_key_id or "rzp_test_placeholder",
            settings.razorpay_key_secret or "placeholder",
        )
    )
