// Known AI Domains Catalog
const AI_DOMAINS = {
  "chatgpt.com": { name: "ChatGPT", category: "llm", risk: 0.8 },
  "chat.openai.com": { name: "ChatGPT (Legacy)", category: "llm", risk: 0.8 },
  "claude.ai": { name: "Claude AI", category: "llm", risk: 0.8 },
  "gemini.google.com": { name: "Google Gemini", category: "llm", risk: 0.7 },
  "perplexity.ai": { name: "Perplexity AI", category: "search", risk: 0.6 },
  "deepseek.com": { name: "DeepSeek", category: "llm", risk: 0.9 },
  "chat.deepseek.com": { name: "DeepSeek Chat", category: "llm", risk: 0.9 },
  "copilot.microsoft.com": { name: "Microsoft Copilot", category: "llm", risk: 0.6 },
  "midjourney.com": { name: "Midjourney", category: "image", risk: 0.6 },
  "huggingface.co": { name: "Hugging Face", category: "mlops", risk: 0.4 },
  "v0.dev": { name: "v0 by Vercel", category: "code", risk: 0.6 },
  "cursor.com": { name: "Cursor AI", category: "code", risk: 0.6 },
  "poe.com": { name: "Poe by Quora", category: "llm", risk: 0.7 },
  "mistral.ai": { name: "Mistral AI", category: "llm", risk: 0.6 },
  "chat.mistral.ai": { name: "Le Chat Mistral", category: "llm", risk: 0.7 }
};

// lookupDomain matches an exact host or any subdomain of a known AI
// domain (e.g. "foo.claude.ai" matches "claude.ai").
function lookupDomain(hostname) {
  const host = (hostname || "").toLowerCase();
  for (const [domain, meta] of Object.entries(AI_DOMAINS)) {
    if (host === domain || host.endsWith("." + domain)) {
      return { domain, ...meta };
    }
  }
  return null;
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { AI_DOMAINS, lookupDomain };
}
