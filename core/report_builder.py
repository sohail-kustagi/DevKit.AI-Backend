"""
core/report_builder.py

Assembles the comprehensive 7-section Markdown report from all phase data
and Specialist Swarm outputs. This is the 'devkit-report.md' downloadable.
"""


def build_report_md(session: dict, outputs: dict) -> str:
    """
    Compile the full project report from session phase data and agent outputs.

    Output sections:
        1. Project Summary          (Phase 1 & 2 data)
        2. Tech Stack & Architecture (outputs['architecture'])
        3. Security & Auth          (Phase 4 data)
        4. Testing Strategy         (Phase 5 data)
        5. Cost & Deployment Plan   (Phase 6 data + RAG pricing)
        6. Milestones & Timeline    (outputs['milestones'])
        7. Integration Warnings     (outputs['architecture']['integration_warnings'])

    Args:
        session: The full MongoDB session document.
        outputs: Dict containing 'architecture', 'milestones', 'instruction_md'.

    Returns:
        A formatted Markdown string ready for file download.
    """
    # TODO: Implement in Phase 6
    raise NotImplementedError("build_report_md not yet implemented — Phase 6")
