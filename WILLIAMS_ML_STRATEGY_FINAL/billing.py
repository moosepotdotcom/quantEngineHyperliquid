import stripe
import os

# --- CONFIG ---
# User needs to provide this!
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "sk_test_PLACEHOLDER")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_PLACEHOLDER")
YOUR_DOMAIN = "http://localhost:5173"

stripe.api_key = STRIPE_SECRET_KEY

def create_checkout_session(user_id: str, email: str = None):
    """
    Creates a Stripe Checkout Session for a $49/mo subscription.
    """
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': 'Quant Engine Pro Access',
                        'description': 'Copy-Trading + Premium Dashboard',
                    },
                    'unit_amount': 4900, # $49.00
                    'recurring': {
                        'interval': 'month',
                    },
                },
                'quantity': 1,
            }],
            mode='subscription',
            success_url=YOUR_DOMAIN + '/dashboard?payment=success',
            cancel_url=YOUR_DOMAIN + '/dashboard?payment=cancelled',
            client_reference_id=user_id, # Link payment to our internal user
            metadata={
                "user_id": user_id
            },
            # If email is provided, pre-fill it
            customer_email=email 
        )
        return {"checkout_url": session.url}
    except Exception as e:
        print(f"Stripe Error: {e}")
        return {"error": str(e)}

def verify_webhook(payload, sig_header):
    """
    Verifies that the webhook came from Stripe.
    """
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
        return event
    except ValueError as e:
        # Invalid payload
        return None
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return None
