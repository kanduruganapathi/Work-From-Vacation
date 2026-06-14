"""Multi-agent AI layer powered by Claude.

The agents cooperate to automate the job hunt:

- ``orchestrator``    — plans the search and invokes specialists via tools.
- ``matching_agent``  — scores a job against a candidate profile.
- ``resume_agent``    — tailors a resume to a specific role.
- ``cover_letter_agent`` — drafts a cover letter.
- ``strategy_agent``  — recommends titles / keywords / sources.
"""
