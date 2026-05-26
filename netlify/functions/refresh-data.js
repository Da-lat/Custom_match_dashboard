exports.handler = async function handler(event) {
  if (event.httpMethod !== "POST") {
    return {
      statusCode: 405,
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ error: "Use POST to queue a dashboard refresh." }),
    };
  }

  const buildHookUrl = process.env.NETLIFY_BUILD_HOOK_URL;
  if (!buildHookUrl) {
    return {
      statusCode: 500,
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        error: "NETLIFY_BUILD_HOOK_URL is not configured.",
      }),
    };
  }

  try {
    const response = await fetch(buildHookUrl, { method: "POST" });
    if (!response.ok) {
      return {
        statusCode: 502,
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          error: `Netlify build hook returned ${response.status}.`,
        }),
      };
    }

    return {
      statusCode: 202,
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        message: "Refresh queued. Reload after the Netlify deploy finishes.",
      }),
    };
  } catch (error) {
    return {
      statusCode: 500,
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ error: "Unable to queue Netlify refresh." }),
    };
  }
};
