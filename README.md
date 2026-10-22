# Scoop

**[View the website](https://noptus.github.io/Scoop/)** · [Contact](mailto:raphael.caillon.engineer@gmail.com?subject=Scoop%20sample%20request)

Account intelligence for B2B sales teams: public company changes, source context and a suggested next conversation.

This repository contains the responsive marketing website for a product experiment. The application and its data infrastructure are maintained separately. The page's example is fictional; public events are not evidence of buying intent.

## What is here

- A responsive landing page, example brief, pilot pricing and FAQ.
- A sample-request helper that validates three accounts and prepares a message locally.
- Clipboard copy, a selectable-text fallback and an email-draft link. No form data is submitted automatically.
- Static HTML, CSS and JavaScript, with no build step or third-party tracking scripts.

## Preview

```bash
git clone https://github.com/Noptus/Scoop.git
cd Scoop
python3 -m http.server 8080 --bind 127.0.0.1
```

Open http://127.0.0.1:8080. GitHub Pages serves the root of `main`.

## Browser checks

Python 3 and Node.js 22+ are needed for the local test runner. Dependencies are for development only; the website remains build-free.

```bash
npm ci
npx playwright install chromium
npm test
```

The suite covers desktop/mobile layout, navigation, three-account validation, clipboard denial, email-draft contents and stale-draft invalidation. It confirms the helper sends no POST request.

## Review the implementation

| File | Purpose |
| --- | --- |
| [index.html](index.html) | Content, semantic sections, labeled form and FAQ |
| [css/style.css](css/style.css) | Responsive layouts, focus styles and reduced-motion support |
| [js/app.js](js/app.js) | Local validation, message preparation and clipboard fallback |

The proposed pilot is €150 excluding VAT for up to five users and 50 accounts, with four reviewed weekly briefs. Scope is agreed before payment; this website does not take payments or enroll users. Salesforce sync remains planned.

AI tools assisted development. This public repository demonstrates product presentation and browser interactions; it does not expose or establish the behavior of the private application.
