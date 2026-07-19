# Security Policy

## Supported Versions

| Version | Supported |
| ------- | --------- |
| 0.1.x   | ✅        |

## Reporting a Vulnerability

Do **not** open a public issue for security vulnerabilities. Report them
privately to the maintainer; expect acknowledgement within 72 hours.

## Data-safety notes

- API keys come from the environment (`OPENAI_API_KEY`, `OPENAI_BASE_URL`).
  Never commit credentials.
- The default `MockProvider` makes no network calls and sends no data off-device.
- When using `OpenAIProvider`, your spec and synthesized text are sent to the
  configured endpoint. Review what leaves your trust boundary.
- The quality filter flags obvious PII patterns, but it is **not** a substitute
  for manual review before using synthesized data in production tests.
