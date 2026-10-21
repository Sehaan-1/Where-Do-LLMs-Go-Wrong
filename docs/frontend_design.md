# Static project frontend

## Scope and boundary

The frontend is a static information site for the annotation project, not a new annotation application. It explains the protocol, seed, and limitations and links to the repository’s existing documentation. The actual labels are still collected separately in Label Studio.

The site sends no annotations or contact-form data. Its small controls only update the visible sample line or workflow stage in the current page. There is no API, account system, analytics, advertising, cookie, browser storage, third-party embed, remote font, or externally hosted image. A strict Content Security Policy blocks connection requests and form submissions. External links are ordinary navigations to GitHub.

## Art direction and idea

The page run used the `sentence-as-layout` direction from [Taste Skill](https://github.com/leonxlnx/taste-skill), dealt with seed `20261021`. The subject’s own material—the response line—becomes the visual insert in the headline and the task preview. The task UI fragment uses the `framed-sheet` app-screen style for its own controls; it is clearly labeled as an unannotated preview, not a functioning submission form.

The direction sheet proposed a remote General Sans font and image/photograph slots. Those were not used: loading a remote font or image would add a third-party request, and no project-owned photography exists. The page uses a local system sans-serif stack and original in-page interface fragments derived from the actual task schema and seed. No third-party image is embedded or copied, so no invented image credits are needed. The interface preview contains an actual source excerpt and leaves all label choices unselected.

## Claims and evidence

| Public-facing statement | Evidence / constraint |
|---|---|
| 150 paired problems, 300 historical responses, 1,355 line units | `data/manifest.json` and validated seed batch |
| The sample uses GSM8K `6b_finetuning` and `175b_finetuning` traces | `data/manifest.json`, `docs/datasheet.md`, and third-party notices |
| No human step labels or agreement findings exist yet | Current project state; keep this visible until real independent annotations are imported |
| The website does not submit annotation decisions | Static HTML/JavaScript only; sample controls change in-memory page text and make no network request |
| No purchases or paid service are offered | Project is research/tooling, not a shop; refund policy is not applicable |

Do not add testimonials, ratings, performance claims, a kappa score, or a first-error distribution unless supported by real, reviewed data. Upstream `answer_correct` is never presented as a human step label.

## Accessibility, privacy, and legal checklist

- **Contrast:** the active text/background pairs were checked above 4.5:1. The lowest checked pair is muted ink on the raised surface at 5.69:1; normal ink/page is 17.14:1 and white/cobalt is 8.15:1. Recheck any new color pair.
- **Images and alt text:** no third-party raster images are used. The site’s visual evidence is semantic HTML; any future non-decorative image or SVG must receive an accurate accessible name/description, and decorative art must be hidden from assistive technology.
- **Accessibility:** semantic landmarks and heading order, skip link, keyboard-operable native range/details controls, labeled controls, visible focus, 44px action targets, responsive layouts, and reduced-motion behavior are implemented. These are implementation checks, not a certification of legal compliance.
- **Privacy and cookies:** `privacy.html` explains the current static behavior, host request logs, the separate Label Studio workflow, and GitHub links. The site sets no cookies and runs no analytics or tracking pixels.
- **Forms and consent:** no personal-data form is present. If one is added later, stop and add data minimization, clear purpose and retention, consent where required, secure handling, and a revised privacy notice before launch.
- **Third-party content:** no remote fonts, scripts, images, widgets, or embeds. GitHub is linked but not loaded inside the page.
- **Copyright:** the task preview uses material already attributed in `THIRD_PARTY_NOTICES.md`; no third-party image assets are included. Preserve source notices when redistributing the seed.
- **Reviews and supported claims:** there are no testimonials or fake reviews. Historical-data and unlabeled-seed limitations are explicit.
- **Refunds and business details:** refunds are explicitly not applicable because no product or paid service is offered. The repository is the real project contact; no business address, email, or legal entity has been invented.
- **Local law:** the policy pages describe current implementation only and do not claim universal compliance. The person deploying or collecting data remains responsible for reviewing applicable rules.

## Files and verification

- `site/index.html`: project landing page and read-only task/workflow previews.
- `site/privacy.html`, `site/terms.html`: project-specific privacy and terms/refund notices.
- `site/assets/site.css`, `site/assets/site-responsive.css`, `site/assets/site.js`: local-only visual system and interactions; styles are split to keep each source file under 1,000 lines.

Run a local preview from the repository root with `python3 -m http.server 4173 --bind 0.0.0.0 --directory site`. Static-site tests and the taste-skill linter should be run after frontend changes. Source tests and Taste Skill lint pass, but no browser executable is installed in the sandbox, so no screenshot-based browser or assistive-technology audit is claimed. Do not claim a browser audit or legal review unless one was performed.
