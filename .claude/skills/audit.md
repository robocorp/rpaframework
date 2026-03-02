# Security Audit Skill

Comprehensive security audit for Python projects with GitHub integration.

## Instructions

Perform a security audit covering:

### 1. GitHub Security Status

Check the repository's security configuration:
```bash
gh api repos/:owner/:repo --jq '{
  visibility: .visibility,
  security: .security_and_analysis
}'
```

### 2. Dependabot Alerts

**Important:** Use `--paginate` and `per_page=100` to get all alerts (API defaults to 30).

Count open alerts by severity:
```bash
gh api "repos/:owner/:repo/dependabot/alerts?state=open&per_page=100" --paginate --jq '.[].security_vulnerability.severity' | sort | uniq -c | sort -rn
```

List critical and high severity alerts:
```bash
gh api "repos/:owner/:repo/dependabot/alerts?state=open&severity=critical&per_page=100" --paginate --jq '.[] | {package: .security_vulnerability.package.name, summary: .security_advisory.summary, cve: .security_advisory.cve_id}'

gh api "repos/:owner/:repo/dependabot/alerts?state=open&severity=high&per_page=100" --paginate --jq '.[] | {package: .security_vulnerability.package.name, summary: .security_advisory.summary}' | head -50
```

Show which packages are affected (deduplicated):
```bash
gh api "repos/:owner/:repo/dependabot/alerts?state=open&per_page=100" --paginate --jq '.[].security_vulnerability.package.name' | sort | uniq -c | sort -rn
```

### 3. Secret Scanning Alerts

Check for any exposed secrets:
```bash
gh api repos/:owner/:repo/secret-scanning/alerts --jq 'length' 2>/dev/null || echo "Secret scanning not available or no alerts"
```

### 4. Code Scanning Alerts

Check for code scanning (CodeQL) alerts:
```bash
gh api repos/:owner/:repo/code-scanning/alerts --jq 'length' 2>/dev/null || echo "Code scanning not enabled or no alerts"
```

### 5. Local Dependency Audit (pip-audit)

If in a package directory with a virtual environment:
```bash
# Run pip-audit in the package's venv
uv run pip-audit 2>/dev/null || pip-audit
```

### 6. Summary and Recommendations

After gathering all data:
1. Summarize findings by category and severity
2. Prioritize critical and high severity issues
3. For Dependabot alerts: suggest running `uv lock --upgrade-package <pkg>` for affected packages
4. For any secrets found: flag as URGENT
5. Recommend enabling any disabled security features (especially dependabot_security_updates)

### 7. Optional: Fix Vulnerabilities

If user wants to fix issues:
1. Update vulnerable packages: `uv lock --upgrade-package <package-name> && uv sync`
2. Run tests: `invoke code.test`
3. If tests pass, commit the lock file changes

## Output Format

Present findings as:
- Security features status table
- Vulnerability summary (count by severity)
- Detailed list of critical/high issues
- Recommended actions
