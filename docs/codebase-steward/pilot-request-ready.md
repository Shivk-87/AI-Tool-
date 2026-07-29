# Pilot Request — Ready

This file contains the finalized pilot outreach email, service-account onboarding steps, and a checklist for add/remove access so your security team can manage pilot repository provisioning.

Pilot service account instructions
- Create a read-only service account (machine user) in your GitHub org.
- Grant it "Read" permission to the repositories intended for pilot indexing.
- Note the account username and the list of repos; paste them into the pilot onboarding issue when ready.

Onboarding checklist for your admin
- [ ] Create service account: username: <pilot-bot-user>
- [ ] Grant read-only access to pilot repos: repo1, repo2
- [ ] Confirm OAuth app or PAT creation for the service account and store credentials in HashiCorp Vault.
- [ ] Notify me here with the username and repo names.

Pilot outreach email (final)

Subject: Request to participate in Codebase Steward pilot

Hi <Team/Owner>,

We’re piloting a codebase AI assistant to help improve developer productivity and code quality. We’d like to include <repo-name> in the pilot. We require read-only access for a test account or a sanitized repo bundle.

What we need:
- Read-only access to the repository for the pilot service account: <pilot-bot-user>.
- Alternatively, a sanitized git bundle uploaded to the secure share: <upload-link>.

We will only index source code and non-sensitive commit metadata; no secrets will be stored. We will provide a pilot report and remove the indexed data on request.

Thanks,
<Your Name>

