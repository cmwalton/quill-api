// Frontend Payment Integration Example for Quill App
// This shows how to integrate the Stripe payment endpoints

class PaymentService {
    constructor(apiBaseUrl = 'http://localhost:8000', authToken = null) {
        this.apiBaseUrl = apiBaseUrl;
        this.authToken = authToken;
    }

    setAuthToken(token) {
        this.authToken = token;
    }

    async makeAuthenticatedRequest(url, options = {}) {
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        if (this.authToken) {
            headers['Authorization'] = `Bearer ${this.authToken}`;
        }

        const response = await fetch(`${this.apiBaseUrl}${url}`, {
            ...options,
            headers
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return response.json();
    }

    // Get available pricing plans
    async getPricingPlans() {
        return this.makeAuthenticatedRequest('/pricing/plans');
    }

    // Create subscription checkout session
    async createSubscription(plan) {
        return this.makeAuthenticatedRequest('/subscriptions/create', {
            method: 'POST',
            body: JSON.stringify({ plan })
        });
    }

    // Purchase credits (one-time payment)
    async purchaseCredits(amount) {
        return this.makeAuthenticatedRequest('/credits/purchase', {
            method: 'POST',
            body: JSON.stringify({ amount })
        });
    }

    // Get user subscription status
    async getSubscriptionStatus() {
        return this.makeAuthenticatedRequest('/subscriptions/status');
    }

    // Get user analytics
    async getUserAnalytics(days = 30) {
        return this.makeAuthenticatedRequest(`/users/analytics?days=${days}`);
    }
}

// Example usage in your Electron app

const paymentService = new PaymentService();

// After user logs in, set the auth token
// paymentService.setAuthToken(userToken);

// Example: Handle subscription purchase
async function handleSubscriptionPurchase(plan) {
    try {
        const response = await paymentService.createSubscription(plan);
        
        if (response.success) {
            // Redirect to Stripe Checkout
            window.open(response.checkout_url, '_blank');
            
            // Store session ID for verification later
            localStorage.setItem('stripe_session_id', response.session_id);
        }
    } catch (error) {
        console.error('Subscription purchase failed:', error);
        alert('Failed to create subscription checkout. Please try again.');
    }
}

// Example: Handle credit purchase
async function handleCreditPurchase(amount) {
    try {
        const response = await paymentService.purchaseCredits(amount);
        
        if (response.success) {
            // Redirect to Stripe Checkout
            window.open(response.checkout_url, '_blank');
            
            // Show user how many credits they'll get
            alert(`You'll receive ${response.total_credits} credits after payment!`);
            
            // Store session ID for verification later
            localStorage.setItem('stripe_session_id', response.session_id);
        }
    } catch (error) {
        console.error('Credit purchase failed:', error);
        alert('Failed to create credit purchase checkout. Please try again.');
    }
}

// Example: Display pricing plans
async function displayPricingPlans() {
    try {
        const response = await paymentService.getPricingPlans();
        
        if (response.success) {
            const plans = response.plans;
            
            console.log('Subscription Plans:');
            Object.entries(plans.subscriptions).forEach(([key, plan]) => {
                console.log(`${plan.name}: $${plan.price}/month`);
                console.log(`- ${plan.credits_per_month === -1 ? 'Unlimited' : plan.credits_per_month} credits per month`);
                console.log(`- Features: ${plan.features.join(', ')}`);
                console.log('');
            });
            
            console.log('Credit Packages:');
            Object.entries(plans.credits).forEach(([amount, config]) => {
                const totalCredits = parseInt(amount) + config.bonus;
                console.log(`${amount} credits (+${config.bonus} bonus): $${config.price}`);
                console.log(`Total: ${totalCredits} credits`);
                console.log('');
            });
        }
    } catch (error) {
        console.error('Failed to load pricing plans:', error);
    }
}

// Example: Check payment success (call this on your success page)
async function handlePaymentSuccess() {
    const urlParams = new URLSearchParams(window.location.search);
    const sessionId = urlParams.get('session_id');
    
    if (sessionId) {
        // Payment was successful, refresh user data
        try {
            const status = await paymentService.getSubscriptionStatus();
            console.log('Updated user status:', status);
            
            // Update UI with new subscription/credit status
            updateUserInterface(status);
            
            // Clear stored session ID
            localStorage.removeItem('stripe_session_id');
        } catch (error) {
            console.error('Failed to get updated user status:', error);
        }
    }
}

// Example: Update UI based on user status
function updateUserInterface(userStatus) {
    if (userStatus.success) {
        const tier = userStatus.tier;
        const credits = userStatus.credits;
        
        console.log(`User tier: ${tier}`);
        console.log(`Available credits: ${credits === -1 ? 'Unlimited' : credits}`);
        
        // Update your UI elements here
        // document.getElementById('user-tier').textContent = tier;
        // document.getElementById('user-credits').textContent = credits === -1 ? 'Unlimited' : credits;
    }
}

// Export for use in your main application
if (typeof module !== 'undefined' && module.exports) {
    module.exports = PaymentService;
}