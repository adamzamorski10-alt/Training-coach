const { schedule } = require('@netlify/functions');

const apiBase = (process.env.FITAI_API_BASE || 'http://127.0.0.1:8000').replace(/\/$/, '');
const publicBase = (process.env.URL || 'https://training-coach.netlify.app').replace(/\/$/, '');
const resendApiKey = process.env.RESEND_API_KEY;
const reminderFrom = process.env.REMINDER_FROM_EMAIL || 'FitAI <noreply@training-coach.netlify.app>';

async function sendReminderEmail(to, streakDays) {
  if (!resendApiKey || !to) return { skipped: true };

  const subject = 'FitAI: czas na dzienny check-in';
  const html = `
    <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #111;">
      <h2 style="margin-bottom: 8px;">Hej! Czas na check-in w FitAI</h2>
      <p>Twoj aktualny streak to <strong>${streakDays} dni</strong>. Nie przerywaj serii.</p>
      <p>Wypelnij szybki check-in i wygeneruj plan na jutro:</p>
      <p><a href="${publicBase}/app" style="display: inline-block; background: #00bcd4; color: #001217; text-decoration: none; padding: 10px 14px; border-radius: 8px; font-weight: 700;">Przejdz do panelu FitAI</a></p>
      <p style="font-size: 12px; color: #666;">Jesli nie chcesz otrzymywac maili, wylacz je w ustawieniach przypomnien w panelu.</p>
    </div>
  `;

  const response = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${resendApiKey}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      from: reminderFrom,
      to: [to],
      subject,
      html,
    }),
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Resend error (${response.status}): ${body}`);
  }

  return { skipped: false };
}

exports.handler = schedule('0 20 * * *', async function processReminders() {
  try {
    const dueResponse = await fetch(`${apiBase}/app/reminders-due`);
    if (!dueResponse.ok) {
      const body = await dueResponse.text();
      throw new Error(`Unable to fetch due reminders (${dueResponse.status}): ${body}`);
    }

    const duePayload = await dueResponse.json();
    const due = Array.isArray(duePayload.due) ? duePayload.due : [];

    let attemptedEmails = 0;
    let sentEmails = 0;
    const failures = [];

    for (const user of due) {
      const reminders = user.reminders || {};
      if (!reminders.email_enabled) continue;
      if (!user.email) continue;

      attemptedEmails += 1;
      try {
        const emailResult = await sendReminderEmail(user.email, Number(user.streak_days || 0));
        if (!emailResult.skipped) {
          sentEmails += 1;
        }
      } catch (err) {
        failures.push({ user_id: user.user_id, error: err.message });
      }
    }

    return {
      statusCode: 200,
      body: JSON.stringify({
        total_due: due.length,
        attempted_emails: attemptedEmails,
        sent_emails: sentEmails,
        failed: failures,
      }),
    };
  } catch (error) {
    return {
      statusCode: 500,
      body: JSON.stringify({ error: error.message || 'Reminder processing failed' }),
    };
  }
});
