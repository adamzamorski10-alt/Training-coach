const stripeSecret = process.env.STRIPE_SECRET_KEY;
const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET;
const apiBase = process.env.FITAI_API_BASE || 'http://127.0.0.1:8000';

exports.handler = async function handler(event) {
  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, body: JSON.stringify({ error: 'Method not allowed' }) };
  }

  if (!stripeSecret || !webhookSecret) {
    return { statusCode: 500, body: JSON.stringify({ error: 'Missing Stripe secrets' }) };
  }

  try {
    const stripe = require('stripe')(stripeSecret);
    const sig = event.headers['stripe-signature'] || event.headers['Stripe-Signature'];
    const stripeEvent = stripe.webhooks.constructEvent(event.body, sig, webhookSecret);

    if (stripeEvent.type === 'checkout.session.completed') {
      const session = stripeEvent.data.object;
      const identityId = session.metadata && session.metadata.identity_id;
      const plan = (session.metadata && session.metadata.plan) || 'pro';

      if (identityId) {
        await fetch(`${apiBase}/billing/plan/${identityId}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ plan }),
        });
      }
    }

    return { statusCode: 200, body: JSON.stringify({ received: true }) };
  } catch (error) {
    return {
      statusCode: 400,
      body: JSON.stringify({ error: error.message || 'Webhook verification failed' }),
    };
  }
};
