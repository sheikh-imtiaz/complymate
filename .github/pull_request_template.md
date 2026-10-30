## Summary

<!-- What does this change and why? Link the Kiro spec / issue. -->

## Type of change

- [ ] Feature
- [ ] Fix
- [ ] Refactor / chore
- [ ] Infrastructure
- [ ] Rule / content change (risk rules, templates, rule library)

## Checklist

- [ ] Tests added or updated (unit / integration / e2e)
- [ ] New tables have `tenant_id` and an RLS policy (migration 0013 pattern)
- [ ] New routes declare a permission with `require(...)`; sensitive actions are in `STEP_UP_PERMISSIONS`
- [ ] Business changes write an audit event; no PII added to system logs
- [ ] Domain code imports no cloud SDK (ports and adapters)
- [ ] OpenAPI types regenerated (`make openapi`) if the API changed
- [ ] Rule/template changes reviewed by a compliance professional

## Screenshots / notes
