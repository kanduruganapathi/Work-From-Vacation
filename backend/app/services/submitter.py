"""Application submission engine.

Automates *submitting* job applications — not just preparing materials — via the
strategy that fits each posting:

- **Greenhouse / Lever**: fill and submit the public application form with a
  headless browser (Playwright), attaching the tailored resume. Supports a
  ``dry_run`` mode that fills everything and screenshots it **without** clicking
  submit, so you can verify before going live.
- **Email**: send the application (resume + cover letter) to a configured
  address via SMTP.
- **Everything else** (Workday, LinkedIn, Naukri, …): marked ``manual_needed``
  with a ready-to-use packet — these cannot be submitted programmatically within
  their terms of service.

Ethics/safety: real submission is **opt-in and off by default**. Autopilot only
submits when ``autopilot_auto_submit`` is explicitly enabled.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone

from app.config import settings
from app.models import Application, Profile, SubmissionStatus

logger = logging.getLogger(__name__)

os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers")

SCREENSHOT_DIR = os.path.join(os.getcwd(), "submission_screenshots")


@dataclass
class SubmissionResult:
    status: SubmissionStatus
    method: str
    note: str
    screenshot_path: str | None = None


def detect_ats(url: str | None) -> str:
    """Classify a posting URL into a submission method."""
    if not url:
        return "unknown"
    u = url.lower()
    if "greenhouse.io" in u or "grnh.se" in u:
        return "greenhouse"
    if "lever.co" in u:
        return "lever"
    if "myworkdayjobs" in u or "workday" in u:
        return "workday"
    if "linkedin.com" in u:
        return "linkedin"
    if "naukri.com" in u:
        return "naukri"
    return "external"


def can_auto_submit(url: str | None) -> bool:
    return detect_ats(url) in {"greenhouse", "lever"}


def _resume_bytes_and_name(profile: Profile, application: Application) -> tuple[bytes, str]:
    """Best resume text available, as a .txt upload payload."""
    text = application.tailored_resume or profile.resume_text or ""
    name = f"resume_{(profile.full_name or 'candidate').replace(' ', '_')}.txt"
    return text.encode("utf-8"), name


def _find_browser() -> str | None:
    """Resolve a Chromium executable in this environment (paths vary)."""
    base = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers")
    candidates = []
    if os.path.isdir(base):
        for entry in sorted(os.listdir(base)):
            if entry.startswith("chromium") and "headless" not in entry:
                candidates.append(os.path.join(base, entry, "chrome-linux", "chrome"))
        candidates.append(os.path.join(base, "chromium", "chrome-linux", "chrome"))
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


async def submit(
    profile: Profile,
    application,
    job,
    *,
    dry_run: bool = False,
) -> SubmissionResult:
    """Submit ``application`` to ``job``'s posting using the best strategy."""
    method = detect_ats(job.url)

    if method in {"greenhouse", "lever"}:
        return await _submit_ats(profile, application, job, method, dry_run=dry_run)
    if method == "external" and settings.application_email_to:
        return _submit_email(profile, application, job)
    return SubmissionResult(
        status=SubmissionStatus.manual_needed,
        method=method,
        note=(
            f"{method.title()} postings can't be auto-submitted within their "
            "terms. Your tailored resume and cover letter are ready — apply "
            f"manually at: {job.url or 'the posting'}"
        ),
    )


async def _submit_ats(
    profile: Profile, application, job, method: str, *, dry_run: bool
) -> SubmissionResult:
    from playwright.async_api import async_playwright

    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    exec_path = _find_browser()
    resume_bytes, resume_name = _resume_bytes_and_name(profile, application)
    full_name = profile.full_name or ""
    first, _, last = full_name.partition(" ")

    # Field name → value, matched case-insensitively against input name/id.
    values = {
        "first_name": first or full_name,
        "last_name": last,
        "name": full_name,
        "email": _guess_email(profile),
        "phone": profile.phone or "",
        "location": profile.current_location or "",
        "linkedin": profile.linkedin_url or "",
        "github": profile.github_url or "",
        "website": profile.portfolio_url or "",
    }

    screenshot_path = os.path.join(
        SCREENSHOT_DIR, f"application_{application.id}.png"
    )

    try:
        async with async_playwright() as p:
            launch_kwargs = {"headless": True}
            if exec_path:
                launch_kwargs["executable_path"] = exec_path
            browser = await p.chromium.launch(**launch_kwargs)
            page = await browser.new_page()
            await page.goto(job.url, wait_until="domcontentloaded", timeout=45000)

            filled = await _fill_fields(page, values)
            await _attach_resume(page, resume_bytes, resume_name)
            await _fill_cover_letter(page, application.cover_letter or "")

            await page.screenshot(path=screenshot_path, full_page=True)

            if dry_run:
                await browser.close()
                return SubmissionResult(
                    status=SubmissionStatus.not_submitted,
                    method=method,
                    note=(
                        f"Dry run: filled {filled} fields on the {method} form "
                        "and captured a screenshot. Nothing was submitted."
                    ),
                    screenshot_path=screenshot_path,
                )

            submitted = await _click_submit(page)
            await page.screenshot(path=screenshot_path, full_page=True)
            await browser.close()

            if submitted:
                return SubmissionResult(
                    status=SubmissionStatus.submitted,
                    method=method,
                    note=f"Submitted via {method}. Screenshot captured as proof.",
                    screenshot_path=screenshot_path,
                )
            return SubmissionResult(
                status=SubmissionStatus.manual_needed,
                method=method,
                note=(
                    "Filled the form but couldn't confirm the submit button "
                    "(the form may need extra required fields). Review the "
                    "screenshot and finish manually."
                ),
                screenshot_path=screenshot_path,
            )
    except Exception as exc:  # never crash the caller
        logger.warning("Submission failed for application %s: %s", application.id, exc)
        return SubmissionResult(
            status=SubmissionStatus.failed,
            method=method,
            note=f"Automated submission error: {exc}",
        )


async def _fill_fields(page, values: dict[str, str]) -> int:
    """Fill visible text inputs whose name/id matches a known field."""
    filled = 0
    inputs = await page.query_selector_all(
        "input[type=text], input[type=email], input[type=tel], input:not([type])"
    )
    for el in inputs:
        try:
            ident = (
                (await el.get_attribute("name") or "")
                + " "
                + (await el.get_attribute("id") or "")
                + " "
                + (await el.get_attribute("aria-label") or "")
            ).lower()
            for key, val in values.items():
                if not val:
                    continue
                if key in ident or key.replace("_", "") in ident.replace("_", ""):
                    await el.fill(val)
                    filled += 1
                    break
        except Exception:
            continue
    return filled


async def _attach_resume(page, resume_bytes: bytes, resume_name: str) -> None:
    file_inputs = await page.query_selector_all("input[type=file]")
    for el in file_inputs:
        try:
            ident = (
                (await el.get_attribute("name") or "")
                + (await el.get_attribute("id") or "")
            ).lower()
            if "cover" in ident:
                continue
            await el.set_input_files(
                files=[{"name": resume_name, "mimeType": "text/plain", "buffer": resume_bytes}]
            )
            return
        except Exception:
            continue


async def _fill_cover_letter(page, cover: str) -> None:
    if not cover:
        return
    areas = await page.query_selector_all("textarea")
    for el in areas:
        try:
            ident = (
                (await el.get_attribute("name") or "")
                + (await el.get_attribute("id") or "")
                + (await el.get_attribute("aria-label") or "")
            ).lower()
            if "cover" in ident or "message" in ident or "additional" in ident:
                await el.fill(cover[:5000])
                return
        except Exception:
            continue


async def _click_submit(page) -> bool:
    for selector in (
        "button[type=submit]",
        "input[type=submit]",
        "button:has-text('Submit application')",
        "button:has-text('Submit')",
        "button:has-text('Apply')",
    ):
        try:
            btn = await page.query_selector(selector)
            if btn:
                await btn.click(timeout=8000)
                await page.wait_for_timeout(3000)
                return True
        except Exception:
            continue
    return False


def _submit_email(profile: Profile, application, job) -> SubmissionResult:
    import smtplib
    from email.message import EmailMessage

    if not settings.smtp_host:
        return SubmissionResult(
            status=SubmissionStatus.manual_needed,
            method="email",
            note="Email submission needs SMTP configured (SMTP_HOST, ...).",
        )
    try:
        msg = EmailMessage()
        msg["Subject"] = f"Application: {job.title}"
        msg["From"] = settings.smtp_from or settings.smtp_user or ""
        msg["To"] = settings.application_email_to
        msg.set_content(application.cover_letter or f"Please find my application for {job.title}.")
        resume_bytes, resume_name = _resume_bytes_and_name(profile, application)
        msg.add_attachment(
            resume_bytes, maintype="text", subtype="plain", filename=resume_name
        )
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            if settings.smtp_user and settings.smtp_password:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
        return SubmissionResult(
            status=SubmissionStatus.submitted,
            method="email",
            note=f"Emailed application to {settings.application_email_to}.",
        )
    except Exception as exc:
        return SubmissionResult(
            status=SubmissionStatus.failed, method="email", note=str(exc)
        )


_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def _guess_email(profile: Profile) -> str:
    """Pull an email from the resume text if we don't store one separately."""
    text = profile.resume_text or ""
    m = _EMAIL_RE.search(text)
    return m.group(0) if m else ""


def now_utc() -> datetime:
    return datetime.now(timezone.utc)
