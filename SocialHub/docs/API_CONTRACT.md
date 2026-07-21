# API Contract

- OpenAPI: /openapi.json
- Docs: /docs
- Health: /api/health
- API errors should move toward:

`json
{"success": false, "error": {"code": "ERROR_CODE", "message": "Human-readable message", "fields": {}}}
`

A regression test now fails if any HTTP method/path pair is registered more than once.
