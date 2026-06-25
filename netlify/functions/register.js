// FitOut Post — registration intake function (Netlify Functions)
//
// Receives the register.html form POST, appends the new member to
// newsletter_members.json via the GitHub Contents API, and sends an
// instant welcome email via Resend. Replaces the old localStorage-only
// handler, which made no network call and never reached the mailing list.
//
// Required environment variables (set in Netlify → Site settings →
// Environment variables — never commit these):
//   GITHUB_TOKEN      Fine-grained PAT scoped ONLY to expo2030/fitoutpost,
//                      permission "Contents: Read and write". Do not reuse
//                      the broad classic PAT used elsewhere for this repo.
//   GITHUB_REPO        "expo2030/fitoutpost"
//   RESEND_API_KEY     Same Resend key used by send_newsletter.py.
//   MAIL_FROM          "FitOut Post <hello@fitoutpost.com>"
//   ALLOWED_ORIGIN     "https://fitoutpost.com" (CORS allow-list)

const GITHUB_API = "https://api.github.com";
const MEMBERS_PATH = "newsletter_members.json";
const RESEND_URL = "https://api.resend.com/emails";

function corsHeaders() {
  const origin = process.env.ALLOWED_ORIGIN || "https://fitoutpost.com";
  return {
    "Access-Control-Allow-Origin": origin,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Content-Type": "application/json",
  };
}

function json(statusCode, body) {
  return { statusCode, headers: corsHeaders(), body: JSON.stringify(body) };
}

function isValidEmail(email) {
  return typeof email === "string" && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

async function githubGetMembers(repo, token) {
  const resp = await fetch(`${GITHUB_API}/repos/${repo}/contents/${MEMBERS_PATH}`, {
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
    },
  });
  if (!resp.ok) {
    throw new Error(`GitHub GET ${MEMBERS_PATH} failed: ${resp.status} ${await resp.text()}`);
  }
  const data = await resp.json();
  const decoded = Buffer.from(data.content, "base64").toString("utf-8");
  return { json: JSON.parse(decoded), sha: data.sha };
}

async function githubPutMembers(repo, token, newJson, sha, commitMessage) {
  const content = Buffer.from(JSON.stringify(newJson, null, 2) + "\n", "utf-8").toString("base64");
  const resp = await fetch(`${GITHUB_API}/repos/${repo}/contents/${MEMBERS_PATH}`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      message: commitMessage,
      content,
      sha,
      committer: { name: "FitOut Post Bot", email: "bot@fitoutpost.com" },
    }),
  });
  if (!resp.ok) {
    throw new Error(`GitHub PUT ${MEMBERS_PATH} failed: ${resp.status} ${await resp.text()}`);
  }
}

async function sendWelcomeEmail({ apiKey, from, toEmail, toName }) {
  const greetingName = toName ? toName.split(" ")[0] : "";
  const html = `
    <div style="font-family:Georgia,'Times New Roman',serif;max-width:560px;margin:0 auto;color:#1a1a1a;">
      <div style="background:#1a1a1a;padding:20px 28px;">
        <span style="display:inline-block;background:#990033;padding:6px 10px;font-size:16px;
                     font-weight:700;color:#fff;letter-spacing:1px;">FOP</span>
        <span style="font-size:18px;font-weight:700;color:#fff;margin-left:10px;">FitOut Post</span>
      </div>
      <div style="padding:32px 28px;background:#fff;border:1px solid #DDD0C4;border-top:none;">
        <h1 style="font-size:22px;margin:0 0 16px;">Welcome${greetingName ? ", " + greetingName : ""}.</h1>
        <p style="font-size:15px;line-height:1.6;margin:0 0 14px;">
          You're registered as a FitOut Post member. Your first weekly roundup —
          news, pipeline, tenders and contract awards from every continent — arrives
          by email <strong>Monday at 12:00 (Spain time)</strong>.
        </p>
        <p style="font-size:15px;line-height:1.6;margin:0 0 22px;">
          In the meantime you have full access to the platform, including the
          members-only roundup archive.
        </p>
        <a href="https://fitoutpost.com/weekly.html"
           style="display:inline-block;background:#1a1a1a;color:#fff;padding:11px 26px;
                  font-size:13px;font-weight:600;text-decoration:none;">View the roundup →</a>
        <p style="font-size:12px;color:#66605A;margin-top:28px;">
          You can unsubscribe at any time by replying to this email.
        </p>
      </div>
    </div>`;
  const resp = await fetch(RESEND_URL, {
    method: "POST",
    headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      from,
      to: [toEmail],
      reply_to: "hello@fitoutpost.com",
      subject: "Welcome to FitOut Post",
      html,
    }),
  });
  if (!resp.ok) {
    // Don't fail the whole registration if only the welcome email fails —
    // the member is already persisted and will still get Monday's roundup.
    console.error(`Resend welcome email failed: ${resp.status} ${await resp.text()}`);
  }
}

exports.handler = async function (event) {
  if (event.httpMethod === "OPTIONS") {
    return { statusCode: 204, headers: corsHeaders(), body: "" };
  }
  if (event.httpMethod !== "POST") {
    return json(405, { ok: false, error: "Method not allowed" });
  }

  let payload;
  try {
    payload = JSON.parse(event.body || "{}");
  } catch (e) {
    return json(400, { ok: false, error: "Invalid JSON body" });
  }

  const firstName = (payload.firstName || "").trim();
  const lastName = (payload.lastName || "").trim();
  const email = (payload.email || "").trim().toLowerCase();
  const company = (payload.company || "").trim();
  const role = (payload.role || "").trim();
  const region = (payload.region || "").trim();

  if (!firstName || !lastName) {
    return json(400, { ok: false, error: "First and last name are required." });
  }
  if (!isValidEmail(email)) {
    return json(400, { ok: false, error: "A valid email address is required." });
  }

  const repo = process.env.GITHUB_REPO;
  const githubToken = process.env.GITHUB_TOKEN;
  const resendKey = process.env.RESEND_API_KEY;
  const mailFrom = process.env.MAIL_FROM || "FitOut Post <hello@fitoutpost.com>";

  if (!repo || !githubToken) {
    console.error("Missing GITHUB_REPO or GITHUB_TOKEN env var");
    return json(500, { ok: false, error: "Server misconfigured. Please try again later." });
  }

  const name = `${firstName} ${lastName}`.trim();

  try {
    const { json: membersFile, sha } = await githubGetMembers(repo, githubToken);
    const members = membersFile.members || [];
    const existing = members.find((m) => (m.email || "").toLowerCase() === email);

    if (existing) {
      // Already a member — idempotent success, no duplicate welcome email.
      return json(200, { ok: true, alreadyMember: true });
    }

    members.push({
      email,
      name,
      company,
      role,
      region,
      subscribedAt: new Date().toISOString(),
    });
    membersFile.members = members;

    await githubPutMembers(repo, githubToken, membersFile, sha, `chore(members): add ${email} via registration`);

    if (resendKey) {
      await sendWelcomeEmail({ apiKey: resendKey, from: mailFrom, toEmail: email, toName: name });
    } else {
      console.error("RESEND_API_KEY not set — member saved but no welcome email sent");
    }

    return json(201, { ok: true });
  } catch (err) {
    console.error("Registration failed:", err);
    return json(502, { ok: false, error: "Could not complete registration. Please try again shortly." });
  }
};
