exports.handler = async function handler(event) {
  const headers = { "content-type": "application/json" };

  if (event.httpMethod === "GET") {
    return {
      statusCode: 200,
      headers,
      body: JSON.stringify({
        ok: true,
        buildHookConfigured: Boolean(process.env.NETLIFY_BUILD_HOOK_URL),
      }),
    };
  }

  if (event.httpMethod !== "POST") {
    return {
      statusCode: 405,
      headers,
      body: JSON.stringify({ error: "Use POST to queue a dashboard refresh." }),
    };
  }

  const buildHookUrl = process.env.NETLIFY_BUILD_HOOK_URL;
  if (!buildHookUrl) {
    return {
      statusCode: 500,
      headers,
      body: JSON.stringify({
        error:
          "Refresh is deployed, but NETLIFY_BUILD_HOOK_URL is not set in Netlify environment variables.",
      }),
    };
  }

  try {
    const response = await fetch(buildHookUrl, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: "{}",
    });
    if (!response.ok) {
      const responseText = await response.text().catch(() => "");
      return {
        statusCode: 502,
        headers,
        body: JSON.stringify({
          error: `Netlify build hook returned ${response.status}.${
            responseText ? ` ${responseText.slice(0, 220)}` : ""
          }`,
        }),
      };
    }

    return {
      statusCode: 202,
      headers,
      body: JSON.stringify({
        message: "Refresh queued. Reload after the Netlify deploy finishes.",
      }),
    };
  } catch (error) {
    return {
      statusCode: 500,
      headers,
      body: JSON.stringify({ error: "Unable to queue Netlify refresh." }),
    };
  }
};
