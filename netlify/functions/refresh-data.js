exports.handler = async function handler(event) {
  const headers = { "content-type": "application/json" };
  const rawBuildHookUrl = process.env.NETLIFY_BUILD_HOOK_URL || "";

  function normalizeBuildHookUrl(value) {
    let normalized = String(value || "").trim();
    if (normalized.startsWith("NETLIFY_BUILD_HOOK_URL=")) {
      normalized = normalized.slice("NETLIFY_BUILD_HOOK_URL=".length).trim();
    }
    const first = normalized[0];
    const last = normalized[normalized.length - 1];
    if (
      normalized.length >= 2 &&
      ((first === '"' && last === '"') ||
        (first === "'" && last === "'") ||
        (first === "`" && last === "`"))
    ) {
      normalized = normalized.slice(1, -1).trim();
    }
    return normalized.replace(/\s+/g, "");
  }

  const buildHookUrl = normalizeBuildHookUrl(rawBuildHookUrl);

  function envSummary() {
    return {
      rawLength: rawBuildHookUrl.length,
      normalizedLength: buildHookUrl.length,
      startsWithHttps: buildHookUrl.startsWith("https://"),
      hasWhitespace: /\s/.test(rawBuildHookUrl),
      wasNormalized: rawBuildHookUrl.trim() !== buildHookUrl,
    };
  }

  function hookSummary() {
    if (!buildHookUrl) return null;
    try {
      const url = new URL(buildHookUrl);
      const hookId = url.pathname.split("/").filter(Boolean).pop() || "";
      return {
        origin: url.origin,
        pathPrefix: url.pathname.replace(hookId, hookId ? "..." : ""),
        hookIdSuffix: hookId.slice(-6),
      };
    } catch (error) {
      return { invalid: true };
    }
  }

  if (event.httpMethod === "GET") {
    return {
      statusCode: 200,
      headers,
      body: JSON.stringify({
        ok: true,
        buildHookConfigured: Boolean(buildHookUrl),
        buildHook: hookSummary(),
        environment: envSummary(),
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

  let parsedBuildHookUrl;
  try {
    parsedBuildHookUrl = new URL(buildHookUrl);
  } catch (error) {
    return {
      statusCode: 500,
      headers,
      body: JSON.stringify({
        error:
          "NETLIFY_BUILD_HOOK_URL is not a valid URL. Paste the full https://api.netlify.com/build_hooks/... value.",
        environment: envSummary(),
      }),
    };
  }

  if (
    parsedBuildHookUrl.origin !== "https://api.netlify.com" ||
    !parsedBuildHookUrl.pathname.startsWith("/build_hooks/")
  ) {
    return {
      statusCode: 500,
      headers,
      body: JSON.stringify({
        error:
          "NETLIFY_BUILD_HOOK_URL must be the full https://api.netlify.com/build_hooks/... URL from Netlify Build hooks.",
        buildHook: hookSummary(),
        environment: envSummary(),
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
          buildHook: hookSummary(),
          environment: envSummary(),
        }),
      };
    }

    return {
      statusCode: 202,
      headers,
      body: JSON.stringify({
        message: "Refresh queued. Reload the page after a couple of minutes",
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
