# Scoop

Account intelligence for B2B sales teams. Scoop turns sourced changes at target accounts into relevant sales briefs and suggested next conversations.

**[Visit the Scoop marketing page](https://noptus.github.io/Scoop/)**

## Team pilot

- €30 per salesperson per month, excluding VAT, with a five-seat minimum.
- Proposed 30-day pilot: €150 for up to five users and 50 pooled accounts.
- Four reviewed weekly briefs, source context, suggested questions and manual onboarding.
- Initial delivery uses email and CSV. Salesforce account sync is planned for the team product.

The example on the page uses a fictional company to demonstrate the format. No customer outcome or buying intent is implied.

This public repository contains the marketing website only. Application code and product infrastructure are maintained separately in a private repository.

The sample-request helper prepares a message locally for invited prospects to paste into their reply. It does not submit data or enroll anyone. A public business email or booking destination can be added once selected.

## Website maintenance

Static HTML, CSS and JavaScript, deployed from the root of `main` with GitHub Pages. Serve the repository locally with `python3 -m http.server 8080` to preview it.
