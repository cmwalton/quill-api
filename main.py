from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import jwt
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from anthropic import Anthropic
import stripe
import json

# Load environment variables
load_dotenv()

app = FastAPI(title="Quill API", version="v1")

# Configure CORS origins based on environment
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8080",
    "file://*",  # Allow Electron app
]

# Add production origins if in production
if os.getenv("ENVIRONMENT") == "production":
    # Add your production frontend domains here
    ALLOWED_ORIGINS.extend([
        "https://your-quill-app.com",
        "https://www.your-quill-app.com"
    ])

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Initialize Anthropic client
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
if not anthropic_api_key:
    raise ValueError("ANTHROPIC_API_KEY environment variable is required")

anthropic_client = Anthropic(api_key=anthropic_api_key)

# Initialize Stripe
stripe_secret_key = os.getenv("STRIPE_SECRET_KEY")
stripe_publishable_key = os.getenv("STRIPE_PUBLISHABLE_KEY") 
stripe_webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

if not stripe_secret_key:
    print("Warning: STRIPE_SECRET_KEY not found. Payment features will be disabled.")
else:
    stripe.api_key = stripe_secret_key

# Available Claude models (based on your actual API access)
AVAILABLE_MODELS = {
    "claude-sonnet-4-20250514": {
        "name": "Claude Sonnet 4",
        "description": "Latest Sonnet - excellent for complex writing tasks",
        "max_tokens": 8192,
        "tier": "premium"
    },
    "claude-opus-4-20250514": {
        "name": "Claude Opus 4",
        "description": "Most powerful model for the most complex tasks",
        "max_tokens": 4096,
        "tier": "premium"
    },
    "claude-opus-4-1-20250805": {
        "name": "Claude Opus 4.1",
        "description": "Latest Opus with enhanced capabilities",
        "max_tokens": 4096,
        "tier": "premium"
    },
    "claude-3-7-sonnet-20250219": {
        "name": "Claude 3.7 Sonnet",
        "description": "Hybrid reasoning model with thinking capabilities",
        "max_tokens": 8192,
        "tier": "premium"
    },
    "claude-3-5-haiku-20241022": {
        "name": "Claude 3.5 Haiku", 
        "description": "Fast and efficient for most tasks",
        "max_tokens": 8192,
        "tier": "basic"
    },
    "claude-3-haiku-20240307": {
        "name": "Claude 3 Haiku",
        "description": "Budget-friendly option for simple tasks",
        "max_tokens": 4096,
        "tier": "basic"
    }
}

# Pricing configuration
PRICING_PLANS = {
    # Subscription plans (monthly)
    "subscriptions": {
        "starter": {
            "name": "Starter Writer",
            "price": 9.99,
            "credits_per_month": 1000,
            "features": ["Basic AI assistance", "Project management", "Export to common formats"]
        },
        "pro": {
            "name": "Professional Writer", 
            "price": 19.99,
            "credits_per_month": 5000,
            "features": ["Advanced AI models", "Series planning", "Premium export options", "Priority support"]
        },
        "unlimited": {
            "name": "Unlimited Writer",
            "price": 39.99, 
            "credits_per_month": -1,  # -1 means unlimited
            "features": ["Unlimited AI usage", "All models", "Advanced analytics", "White-glove support"]
        }
    },
    # One-time credit purchases
    "credits": {
        100: {"price": 4.99, "bonus": 0},
        500: {"price": 19.99, "bonus": 50},   # 10% bonus
        1000: {"price": 34.99, "bonus": 150},  # 15% bonus  
        2500: {"price": 79.99, "bonus": 500},  # 20% bonus
    }
}

# Environment and configuration validation
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
SECRET_KEY = os.getenv("SECRET_KEY")

if not SECRET_KEY:
    if ENVIRONMENT == "production":
        raise ValueError("SECRET_KEY environment variable is required in production")
    else:
        SECRET_KEY = "development-secret-key-not-for-production"
        print("Warning: Using development SECRET_KEY. Set SECRET_KEY environment variable for production.")

# Mock data for development
mock_users = {}

# License database - in production, this would be a real database
license_database = {
    # Example license keys (generate these when customers purchase)
    "DEMO-LICENSE-12345": {
        "machineId": None,  # Will be set when first activated
        "credits": 5000,
        "tier": "pro",
        "purchaseDate": "2025-01-01",
        "activated": False
    }
}

# Create default desktop user for development testing
DESKTOP_USER_EMAIL = "desktop@quillapp.local"
mock_users[DESKTOP_USER_EMAIL] = {
    "email": DESKTOP_USER_EMAIL,
    "password": "desktop-user-auto-auth", 
    "credits": 10000,
    "subscription_tier": "unlimited"
}

# Pydantic models
class UserRegister(BaseModel):
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class AIRequest(BaseModel):
    prompt: str
    model: Optional[str] = None
    projectContext: Optional[Dict[str, Any]] = {}

class CheckoutRequest(BaseModel):
    tier: str

class CreditPurchaseRequest(BaseModel):
    amount: int  # Number of credits to purchase
    
class SubscriptionRequest(BaseModel):
    plan: str  # 'starter', 'pro', 'unlimited'

class LicenseAuthRequest(BaseModel):
    machineId: str
    licenseKey: Optional[str] = None

# Helper functions
def create_token(email: str):
    payload = {
        "email": email,
        "exp": datetime.utcnow() + timedelta(days=30)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def generate_license_key():
    """Generate a new license key for purchase"""
    import secrets
    import string
    
    # Generate format: QUILL-XXXXX-XXXXX-XXXXX
    chars = string.ascii_uppercase + string.digits
    part1 = ''.join(secrets.choice(chars) for _ in range(5))
    part2 = ''.join(secrets.choice(chars) for _ in range(5)) 
    part3 = ''.join(secrets.choice(chars) for _ in range(5))
    
    return f"QUILL-{part1}-{part2}-{part3}"

def verify_token(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload["email"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/health")
def health():
    """Health check endpoint for monitoring services"""
    try:
        # Basic service health checks
        health_status = {
            "status": "ok",
            "environment": ENVIRONMENT,
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "anthropic": bool(anthropic_api_key),
                "stripe": bool(stripe_secret_key),
            }
        }

        return health_status
    except Exception as e:
        return {
            "status": "error",
            "error": str(e) if ENVIRONMENT != "production" else "Health check failed",
            "timestamp": datetime.utcnow().isoformat()
        }

# Authentication endpoints
@app.post("/auth/register")
def register(user: UserRegister):
    if user.email in mock_users:
        return {"success": False, "message": "User already exists"}
    
    mock_users[user.email] = {
        "email": user.email,
        "password": user.password,  # In production, hash this!
        "credits": 100,
        "subscription_tier": "credits"
    }
    
    token = create_token(user.email)
    return {
        "success": True,
        "token": token,
        "user": mock_users[user.email]
    }

@app.post("/auth/login")
def login(user: UserLogin):
    if user.email not in mock_users or mock_users[user.email]["password"] != user.password:
        return {"success": False, "message": "Invalid credentials"}
    
    token = create_token(user.email)
    return {
        "success": True,
        "token": token,
        "user": mock_users[user.email]
    }

@app.get("/auth/verify")
def verify(email: str = Depends(verify_token)):
    if email not in mock_users:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "success": True,
        "user": mock_users[email]
    }

@app.post("/auth/desktop")
def desktop_auth():
    """Auto-authenticate desktop app users (development only)"""
    token = create_token(DESKTOP_USER_EMAIL)
    return {
        "success": True,
        "token": token,
        "user": mock_users[DESKTOP_USER_EMAIL]
    }

@app.post("/auth/license")
def license_auth(request: LicenseAuthRequest):
    """Production license-based authentication"""
    machine_id = request.machineId
    license_key = request.licenseKey
    
    # If no license key provided, check if machine already has one registered
    if not license_key:
        # Look for existing license for this machine
        for key, data in license_database.items():
            if data.get("machineId") == machine_id and data.get("activated"):
                license_key = key
                break
        
        if not license_key:
            return {
                "success": False,
                "requiresLicense": True,
                "message": "This device needs to be activated with a license key"
            }
    
    # Validate license key
    if license_key not in license_database:
        return {
            "success": False,
            "message": "Invalid license key"
        }
    
    license_data = license_database[license_key]
    
    # Check if license is already activated on a different machine
    if license_data.get("activated") and license_data.get("machineId") != machine_id:
        return {
            "success": False,
            "message": "License key is already activated on another device"
        }
    
    # Activate license for this machine if not already activated
    if not license_data.get("activated"):
        license_data["machineId"] = machine_id
        license_data["activated"] = True
        license_data["activationDate"] = datetime.utcnow().isoformat()
    
    # Create user account for this license
    user_email = f"license_{license_key}@quillapp.local"
    mock_users[user_email] = {
        "email": user_email,
        "machineId": machine_id,
        "licenseKey": license_key,
        "credits": license_data["credits"],
        "subscription_tier": license_data["tier"],
        "activationDate": license_data.get("activationDate")
    }
    
    token = create_token(user_email)
    return {
        "success": True,
        "token": token,
        "user": mock_users[user_email],
        "licenseActivated": not license_data.get("activated", True)
    }

# AI endpoints
@app.post("/ai/{tool}")
async def ai_request(tool: str, request: AIRequest, email: str = Depends(verify_token)):
    try:
        # Get user and check credits
        user = mock_users[email]
        if user["subscription_tier"] == "credits" and user["credits"] <= 0:
            raise HTTPException(status_code=402, detail="No credits remaining")
        
        # Build the prompt based on tool
        prompt = request.prompt
        if tool == "brainstorm":
            prompt = f"Brainstorm creative ideas for: {request.prompt}"
        elif tool == "edit":
            prompt = f"Provide editing suggestions for: {request.prompt}"
        elif tool == "complete":
            prompt = f"Continue or complete this text: {request.prompt}"
        
        # Add project context if available
        if request.projectContext:
            context_info = f"Project: {request.projectContext.get('projectName', 'Untitled')} ({request.projectContext.get('projectType', 'general')})"
            prompt = f"{context_info}\n\n{prompt}"
        
        # Validate and get model
        model_id = request.model or "claude-sonnet-4-20250514"  # Use Claude Sonnet 4 as default
        if model_id not in AVAILABLE_MODELS:
            # Fall back to Claude Sonnet 4 if requested model not available
            model_id = "claude-sonnet-4-20250514"
        
        model_config = AVAILABLE_MODELS[model_id]
        max_tokens = min(1000, model_config.get("max_tokens", 1000))
        
        # Call Claude API
        message = anthropic_client.messages.create(
            model=model_id,
            max_tokens=max_tokens,
            messages=[{
                "role": "user", 
                "content": prompt
            }]
        )
        
        response_text = message.content[0].text if message.content else "No response generated"
        
        # Deduct credits
        if user["subscription_tier"] == "credits":
            user["credits"] -= 1
        
        return {
            "success": True,
            "response": response_text,
            "remainingCredits": user["credits"]
        }
        
    except Exception as e:
        error_msg = f"AI request error: {str(e)}"
        print(error_msg)

        # Don't expose internal errors in production
        if ENVIRONMENT == "production":
            raise HTTPException(status_code=500, detail="Internal server error occurred")
        else:
            raise HTTPException(status_code=500, detail=f"AI request failed: {str(e)}")

@app.get("/ai/models")
def get_models(email: str = Depends(verify_token)):
    models = []
    for model_id, config in AVAILABLE_MODELS.items():
        models.append({
            "id": model_id,
            "name": config["name"],
            "description": config["description"],
            "tier": config["tier"],
            "max_tokens": config["max_tokens"]
        })
    
    return {
        "success": True,
        "models": models
    }

# Subscription endpoints
@app.get("/subscriptions/status")
def subscription_status(email: str = Depends(verify_token)):
    user = mock_users[email]
    return {
        "success": True,
        "tier": user["subscription_tier"],
        "credits": user.get("credits", 0)
    }

@app.post("/subscriptions/create")
def create_subscription(request: SubscriptionRequest, email: str = Depends(verify_token)):
    if not stripe_secret_key:
        raise HTTPException(status_code=503, detail="Stripe not configured")
    
    plan = request.plan
    if plan not in PRICING_PLANS["subscriptions"]:
        raise HTTPException(status_code=400, detail="Invalid subscription plan")
    
    plan_config = PRICING_PLANS["subscriptions"][plan]
    
    try:
        # Create Stripe checkout session for subscription
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            mode='subscription',
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': plan_config["name"],
                        'description': ', '.join(plan_config["features"]),
                    },
                    'unit_amount': int(plan_config["price"] * 100),  # Convert to cents
                    'recurring': {
                        'interval': 'month',
                    },
                },
                'quantity': 1,
            }],
            metadata={
                'user_email': email,
                'plan': plan,
                'credits_per_month': plan_config["credits_per_month"]
            },
            success_url=f'http://localhost:3000/payment/success?session_id={{CHECKOUT_SESSION_ID}}',
            cancel_url='http://localhost:3000/payment/cancel',
        )
        
        return {
            "success": True,
            "checkout_url": session.url,
            "session_id": session.id
        }
        
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/credits/purchase")
def purchase_credits(request: CreditPurchaseRequest, email: str = Depends(verify_token)):
    if not stripe_secret_key:
        raise HTTPException(status_code=503, detail="Stripe not configured")
    
    amount = request.amount
    if amount not in PRICING_PLANS["credits"]:
        raise HTTPException(status_code=400, detail="Invalid credit amount")
    
    credit_config = PRICING_PLANS["credits"][amount]
    total_credits = amount + credit_config["bonus"]
    
    try:
        # Create Stripe checkout session for one-time payment
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            mode='payment',
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f'{amount} Quill Credits',
                        'description': f'{amount} credits + {credit_config["bonus"]} bonus credits = {total_credits} total credits',
                    },
                    'unit_amount': int(credit_config["price"] * 100),  # Convert to cents
                },
                'quantity': 1,
            }],
            metadata={
                'user_email': email,
                'credits_purchased': amount,
                'bonus_credits': credit_config["bonus"],
                'total_credits': total_credits
            },
            success_url=f'http://localhost:3000/payment/success?session_id={{CHECKOUT_SESSION_ID}}',
            cancel_url='http://localhost:3000/payment/cancel',
        )
        
        return {
            "success": True,
            "checkout_url": session.url,
            "session_id": session.id,
            "total_credits": total_credits
        }
        
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))

# Payment webhook handlers
@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    
    if not stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="Webhook secret not configured")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, stripe_webhook_secret
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        
        # Get user email from metadata
        user_email = session.get('metadata', {}).get('user_email')
        if not user_email or user_email not in mock_users:
            print(f"Webhook error: User {user_email} not found")
            return {"status": "error", "message": "User not found"}
        
        user = mock_users[user_email]
        
        if session.get('mode') == 'subscription':
            # Handle subscription completion
            plan = session.get('metadata', {}).get('plan')
            credits_per_month = int(session.get('metadata', {}).get('credits_per_month', 0))
            
            user['subscription_tier'] = plan
            if credits_per_month > 0:
                user['credits'] = credits_per_month
            elif credits_per_month == -1:
                user['credits'] = -1  # Unlimited
            
            print(f"Subscription activated for {user_email}: {plan}")
            
        elif session.get('mode') == 'payment':
            # Handle one-time credit purchase
            total_credits = int(session.get('metadata', {}).get('total_credits', 0))
            user['credits'] = user.get('credits', 0) + total_credits
            
            print(f"Credits purchased for {user_email}: +{total_credits} (total: {user['credits']})")
    
    elif event['type'] == 'customer.subscription.deleted':
        # Handle subscription cancellation
        subscription = event['data']['object']
        # You would need to match this to a user in production
        print(f"Subscription cancelled: {subscription.get('id')}")
    
    return {"status": "success"}

@app.get("/pricing/plans")
def get_pricing_plans():
    return {
        "success": True,
        "plans": PRICING_PLANS
    }

@app.post("/admin/generate-license")
def generate_new_license(tier: str = "pro", credits: int = 5000):
    """Generate a new license key (admin use only)"""
    license_key = generate_license_key()
    
    license_database[license_key] = {
        "machineId": None,
        "credits": credits,
        "tier": tier,
        "purchaseDate": datetime.utcnow().isoformat(),
        "activated": False
    }
    
    return {
        "success": True,
        "licenseKey": license_key,
        "tier": tier,
        "credits": credits
    }

@app.get("/admin/licenses")
def list_licenses():
    """List all licenses and their status (admin use only)"""
    return {
        "success": True,
        "licenses": {
            key: {
                "tier": data["tier"],
                "credits": data["credits"],
                "activated": data.get("activated", False),
                "activationDate": data.get("activationDate"),
                "machineId": data.get("machineId", "Not activated")[:8] + "..." if data.get("machineId") else "Not activated"
            } for key, data in license_database.items()
        }
    }

# Analytics endpoints
@app.get("/users/analytics")
def user_analytics(days: int = 30, email: str = Depends(verify_token)):
    # Mock analytics data
    return {
        "success": True,
        "analytics": {
            "totalRequests": 42,
            "creditsUsed": 37,
            "topTools": ["complete", "brainstorm", "edit"]
        }
    }
