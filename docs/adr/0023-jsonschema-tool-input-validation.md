# ADR-0023: jsonschema restores mcp tool input validation

## Status

Accepted

## Context

mcp 1.x validated `call_tool` arguments against each tool's
`inputSchema` with jsonschema on the request layer. mcp 2.x routes
`CallToolRequest` straight to `on_call_tool` unvalidated, so
schema-invalid arguments reach the handlers as late failures instead of
a boundary error.

The SDK 1.62.0 sweep forced `mcp>=2` (the `fastmcp-slim[client]` extra
pins it), so the repo migrated `mcp_server.py` to the 2.x API. The
request-layer validation is part of the contract the tests and sisters
rely on (`Input validation error` results naming the offending key).

## Decision

Add `jsonschema>=4` as a runtime dependency. `call_tool` validates
`arguments` against the tool's `input_schema` with
`Draft202012Validator` before dispatch; on failure it returns a
`CallToolResult` carrying `Input validation error: '<key>': <message>`
(`is_error=True`).

## Consequences

- Schema-invalid arguments fail closed at the boundary.
- Direct `call_tool` test invocations must pass schema-valid
  arguments, same as the wire path always required.
