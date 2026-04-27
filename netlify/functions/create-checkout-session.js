const stripeSecret = process.env.STRIPE_SECRET_KEY;
const appBase = process.env.URL || 'https://training-coach.netlify.app';

exports.handler = async function handler(event) {
  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, body: JSON.stringify({ error: 'Method not allowed' }) };
  }

  if (!stripeSecret) {
    return { statusCode: 500, body: JSON.stringify({ error: 'Missing STRIPE_SECRET_KEY' }) };
  }

  const { identity_id, email } = JSON.parse(event.body || '{}');
  if (!identity_id || !email) {
    return { statusCode: 400, body: JSON.stringify({ error: 'identity_id and email are required' }) };
  }

  try {
    const stripe = require('stripe')(stripeSecret);
    const session = await stripe.checkout.sessions.create({
      mode: 'subscription',
      customer_email: email,
      line_items: [
        {
          price: process.env.STRIPE_PRO_PRICE_ID,
          quantity: 1,
        },
      ],
      success_url: `${appBase}/app?checkout=success`,
      cancel_url: `${appBase}/app?checkout=cancel`,
      metadata: {
        identity_id,
        plan: 'pro',
      },
    });

    return {
      statusCode: 200,
      body: JSON.stringify({ url: session.url }),
    };
  } catch (error) {
    return {
      statusCode: 500,
      body: JSON.stringify({ error: error.message || 'Stripe checkout error' }),
    };
  }
};
