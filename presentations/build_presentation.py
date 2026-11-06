"""
PATCHPROOF Professional Hackathon Presentation Generator
Generates a polished 17-slide widescreen (16:9) PowerPoint presentation
with a premium cybersecurity visual identity (Dark Navy, Electric Cyan, Vibrant Violet).
"""

import os
import sys
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

# Widescreen 16:9 Dimensions
SLIDE_WIDTH = Inches(13.333)
SLIDE_HEIGHT = Inches(7.5)

# Color Palette: Premium Cybersecurity Visual Identity
COLOR_BG_DARK = RGBColor(10, 14, 26)       # #0A0E1A - Deep Navy/Near-Black
COLOR_CARD_BG = RGBColor(19, 27, 46)       # #131B2E - Dark Slate Blue Card
COLOR_CARD_BG_ALT = RGBColor(15, 23, 42)   # #0F172A - Secondary Container
COLOR_BORDER = RGBColor(38, 53, 84)        # #263554 - Subtle Accent Border
COLOR_CYAN = RGBColor(0, 240, 255)         # #00F0FF - Electric Cyan
COLOR_SKY = RGBColor(56, 189, 248)         # #38BDF8 - Sky Blue
COLOR_VIOLET = RGBColor(168, 85, 247)      # #A855F7 - Vibrant Violet
COLOR_PURPLE = RGBColor(139, 92, 246)      # #8B5CF6 - Accent Purple
COLOR_WHITE = RGBColor(248, 250, 252)      # #F8FAFC - Bright Text
COLOR_MUTED = RGBColor(148, 163, 184)      # #94A3B8 - Slate Muted Text
COLOR_EMERALD = RGBColor(16, 185, 129)     # #10B981 - Safe / Verified Emerald
COLOR_ROSE = RGBColor(244, 63, 94)         # #F43F5E - Critical / Vulnerability Rose
COLOR_AMBER = RGBColor(245, 158, 11)       # #F59E0B - Warning Amber

FONT_HEADING = "Segoe UI"
FONT_BODY = "Segoe UI"
FONT_CODE = "Consolas"


class PresentationBuilder:
    def __init__(self):
        self.prs = Presentation()
        self.prs.slide_width = SLIDE_WIDTH
        self.prs.slide_height = SLIDE_HEIGHT
        self.blank_layout = self.prs.slide_layouts[6]  # Blank layout
        self.total_slides = 17

    def _set_dark_background(self, slide):
        """Fill slide background with deep navy."""
        bg = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_WIDTH, SLIDE_HEIGHT
        )
        bg.fill.solid()
        bg.fill.fore_color.rgb = COLOR_BG_DARK
        bg.line.fill.background()  # No border
        return bg

    def _add_header(self, slide, category: str, title: str, subtitle: str):
        """Add standardized top header with category pill, title and subtitle."""
        # Category Pill
        pill = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(0.4), Inches(2.8), Inches(0.32)
        )
        pill.fill.solid()
        pill.fill.fore_color.rgb = RGBColor(30, 27, 75)  # Dark violet container
        pill.line.color.rgb = COLOR_VIOLET
        pill.line.width = Pt(1)
        tf_pill = pill.text_frame
        tf_pill.word_wrap = False
        p_pill = tf_pill.paragraphs[0]
        p_pill.text = category.upper()
        p_pill.font.name = FONT_HEADING
        p_pill.font.size = Pt(9.5)
        p_pill.font.bold = True
        p_pill.font.color.rgb = COLOR_CYAN
        p_pill.alignment = PP_ALIGN.CENTER

        # Title Box
        title_box = slide.shapes.add_textbox(
            Inches(0.8), Inches(0.75), Inches(11.7), Inches(0.65)
        )
        tf_title = title_box.text_frame
        tf_title.word_wrap = True
        p_title = tf_title.paragraphs[0]
        p_title.text = title
        p_title.font.name = FONT_HEADING
        p_title.font.size = Pt(22)
        p_title.font.bold = True
        p_title.font.color.rgb = COLOR_WHITE

        # Subtitle Box
        sub_box = slide.shapes.add_textbox(
            Inches(0.8), Inches(1.35), Inches(11.7), Inches(0.4)
        )
        tf_sub = sub_box.text_frame
        tf_sub.word_wrap = True
        p_sub = tf_sub.paragraphs[0]
        p_sub.text = subtitle
        p_sub.font.name = FONT_BODY
        p_sub.font.size = Pt(11)
        p_sub.font.color.rgb = COLOR_MUTED

    def _add_footer(self, slide, slide_num: int):
        """Add bottom branding and safety guard bar."""
        # Top dividing line for footer
        line = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(6.9), Inches(11.733), Pt(1)
        )
        line.fill.solid()
        line.fill.fore_color.rgb = COLOR_BORDER
        line.line.fill.background()

        # Left branding text
        left_box = slide.shapes.add_textbox(
            Inches(0.8), Inches(6.95), Inches(4.5), Inches(0.4)
        )
        tf_l = left_box.text_frame
        p_l = tf_l.paragraphs[0]
        p_l.text = "PATCHPROOF  |  Intelligent Software Supply-Chain Security & ML Code Debugger"
        p_l.font.name = FONT_BODY
        p_l.font.size = Pt(8.5)
        p_l.font.color.rgb = COLOR_MUTED

        # Center safety guard pill
        guard_pill = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, Inches(5.3), Inches(6.95), Inches(3.2), Inches(0.28)
        )
        guard_pill.fill.solid()
        guard_pill.fill.fore_color.rgb = RGBColor(6, 44, 30)
        guard_pill.line.color.rgb = COLOR_EMERALD
        guard_pill.line.width = Pt(1)
        tf_g = guard_pill.text_frame
        p_g = tf_g.paragraphs[0]
        p_g.text = "SAFETY INVARIANT: NEVER_MERGE_ACTIVE"
        p_g.font.name = FONT_CODE
        p_g.font.size = Pt(8.5)
        p_g.font.bold = True
        p_g.font.color.rgb = COLOR_EMERALD
        p_g.alignment = PP_ALIGN.CENTER

        # Right slide number
        right_box = slide.shapes.add_textbox(
            Inches(10.5), Inches(6.95), Inches(2.0), Inches(0.4)
        )
        tf_r = right_box.text_frame
        p_r = tf_r.paragraphs[0]
        p_r.text = f"Slide {slide_num:02d} / {self.total_slides:02d}"
        p_r.font.name = FONT_BODY
        p_r.font.size = Pt(8.5)
        p_r.font.color.rgb = COLOR_MUTED
        p_r.alignment = PP_ALIGN.RIGHT

    def add_card(self, slide, left, top, width, height, title=None, subtitle=None, border_color=COLOR_BORDER):
        """Create a styled dark card container."""
        card = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height
        )
        card.fill.solid()
        card.fill.fore_color.rgb = COLOR_CARD_BG
        card.line.color.rgb = border_color
        card.line.width = Pt(1)

        # Optional Title/Subtitle inside card header
        if title:
            tb = slide.shapes.add_textbox(left + Inches(0.2), top + Inches(0.15), width - Inches(0.4), Inches(0.45))
            tf = tb.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.text = title
            p.font.name = FONT_HEADING
            p.font.size = Pt(13)
            p.font.bold = True
            p.font.color.rgb = COLOR_CYAN

            if subtitle:
                p2 = tf.add_paragraph()
                p2.text = subtitle
                p2.font.name = FONT_BODY
                p2.font.size = Pt(9.5)
                p2.font.color.rgb = COLOR_MUTED

        return card

    # ==================== SLIDE IMPLEMENTATIONS ====================

    def build_slide_01_title(self):
        """Slide 1: Title & Hero Vision."""
        slide = self.prs.slides.add_slide(self.blank_layout)
        self._set_dark_background(slide)

        # Hero Banner Glow Card
        hero = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(0.8), Inches(11.733), Inches(5.9)
        )
        hero.fill.solid()
        hero.fill.fore_color.rgb = COLOR_CARD_BG
        hero.line.color.rgb = COLOR_CYAN
        hero.line.width = Pt(1.5)

        # Top Badge
        badge = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.3), Inches(1.2), Inches(4.2), Inches(0.4)
        )
        badge.fill.solid()
        badge.fill.fore_color.rgb = RGBColor(24, 20, 60)
        badge.line.color.rgb = COLOR_VIOLET
        badge.line.width = Pt(1)
        tb_b = badge.text_frame
        p_b = tb_b.paragraphs[0]
        p_b.text = "AUTONOMOUS CYBERSECURITY & ML PLATFORM"
        p_b.font.name = FONT_HEADING
        p_b.font.size = Pt(10)
        p_b.font.bold = True
        p_b.font.color.rgb = COLOR_CYAN
        p_b.alignment = PP_ALIGN.CENTER

        # Title
        t_box = slide.shapes.add_textbox(Inches(1.3), Inches(1.8), Inches(10.7), Inches(1.1))
        tf_t = t_box.text_frame
        p_t = tf_t.paragraphs[0]
        p_t.text = "PATCHPROOF"
        p_t.font.name = FONT_HEADING
        p_t.font.size = Pt(46)
        p_t.font.bold = True
        p_t.font.color.rgb = COLOR_WHITE

        # Subtitle
        s_box = slide.shapes.add_textbox(Inches(1.3), Inches(2.95), Inches(10.7), Inches(0.6))
        tf_s = s_box.text_frame
        p_s = tf_s.paragraphs[0]
        p_s.text = "Intelligent Software Supply-Chain Security & AI Code Debugging"
        p_s.font.name = FONT_HEADING
        p_s.font.size = Pt(20)
        p_s.font.color.rgb = COLOR_SKY

        # Tagline
        tag_box = slide.shapes.add_textbox(Inches(1.3), Inches(3.55), Inches(10.7), Inches(0.4))
        tf_tag = tag_box.text_frame
        p_tag = tf_tag.paragraphs[0]
        p_tag.text = '“Find the risk. Prove the fix. Guard the merge.”'
        p_tag.font.name = FONT_BODY
        p_tag.font.size = Pt(14)
        p_tag.font.italic = True
        p_tag.font.color.rgb = COLOR_VIOLET

        # 4 Core Value Pillars Cards at bottom of Hero
        pillars = [
            ("Multi-Format SBOM", "CycloneDX & SPDX with live OSV, CISA KEV & EPSS intelligence", COLOR_CYAN),
            ("High-Entropy Secret Scan", "Full Git history scanning with automated patch redaction", COLOR_ROSE),
            ("Explainable Risk Engine", "Multi-factor formula evaluating exploitability & depth", COLOR_AMBER),
            ("Safe Human-Gated PRs", "Minimal SemVer bumps + strict NEVER_MERGE enforcement", COLOR_EMERALD)
        ]
        w = Inches(2.5)
        h = Inches(1.8)
        gap = Inches(0.24)
        for i, (p_title, p_desc, p_col) in enumerate(pillars):
            l = Inches(1.3) + i * (w + gap)
            p_card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, l, Inches(4.3), w, h)
            p_card.fill.solid()
            p_card.fill.fore_color.rgb = COLOR_CARD_BG_ALT
            p_card.line.color.rgb = p_col
            p_card.line.width = Pt(1)

            tb_c = slide.shapes.add_textbox(l + Inches(0.15), Inches(4.45), w - Inches(0.3), h - Inches(0.3))
            tf_c = tb_c.text_frame
            tf_c.word_wrap = True

            pt = tf_c.paragraphs[0]
            pt.text = p_title
            pt.font.name = FONT_HEADING
            pt.font.size = Pt(12)
            pt.font.bold = True
            pt.font.color.rgb = p_col

            pd = tf_c.add_paragraph()
            pd.text = p_desc
            pd.font.name = FONT_BODY
            pd.font.size = Pt(9.5)
            pd.font.color.rgb = COLOR_MUTED

    def build_slide_02_problem(self):
        """Slide 2: Problem Statement."""
        slide = self.prs.slides.add_slide(self.blank_layout)
        self._set_dark_background(slide)
        self._add_header(
            slide,
            "PROBLEM STATEMENT",
            "The Fragility of Modern Software Supply Chains",
            "Critical vulnerabilities, credential exposures, and flawed automation threaten modern developer workflows"
        )
        self._add_footer(slide, 2)

        cards = [
            (
                "1. Hidden Dependency Risks",
                COLOR_ROSE,
                [
                    ("80–90% Open Source Codebase", "Modern applications are predominantly composed of third-party packages with deep transitive trees."),
                    ("742% Surge in Supply-Chain Attacks", "Adversaries target unmonitored dependencies (e.g. Log4Shell, requests credential leaks)."),
                    ("Opaque Transitive Depths", "Developers cannot manually trace multi-level sub-dependencies or detect compromised nested manifests.")
                ]
            ),
            (
                "2. Secrets & Alert Fatigue",
                COLOR_AMBER,
                [
                    ("Credentials in Git History", "API tokens, private keys, and cloud credentials accidentally committed into source repositories."),
                    ("Noisy Security Scanners", "Traditional SAST/SCA tools output thousands of unprioritized CVE warnings, driving engineer fatigue."),
                    ("Lack of Exploit Context", "A CVSS 9.8 vulnerability with 0.01% exploit probability blinds teams to real CISA KEV active threats.")
                ]
            ),
            (
                "3. Flawed Remediation Bots",
                COLOR_VIOLET,
                [
                    ("Breaking Version Bumps", "Automated bots blind-jump major versions, introducing breaking API changes and CI failures."),
                    ("Dangerous Autonomous Merging", "Auto-merging bots create attack vectors where untrusted dependency patches bypass human review."),
                    ("Semantic Bug Blindness", "Static scanners ignore runtime code defects (memory safety, race conditions, null dereferences).")
                ]
            )
        ]

        w = Inches(3.64)
        h = Inches(4.7)
        gap = Inches(0.4)
        top = Inches(1.9)

        for i, (title, color, items) in enumerate(cards):
            left = Inches(0.8) + i * (w + gap)
            self.add_card(slide, left, top, w, h, title, border_color=color)

            tb = slide.shapes.add_textbox(left + Inches(0.2), top + Inches(0.7), w - Inches(0.4), h - Inches(0.8))
            tf = tb.text_frame
            tf.word_wrap = True

            for j, (h_text, b_text) in enumerate(items):
                p_head = tf.paragraphs[0] if j == 0 else tf.add_paragraph()
                p_head.text = f"▸ {h_text}"
                p_head.font.name = FONT_HEADING
                p_head.font.size = Pt(11)
                p_head.font.bold = True
                p_head.font.color.rgb = COLOR_WHITE
                p_head.space_after = Pt(2)

                p_body = tf.add_paragraph()
                p_body.text = b_text
                p_body.font.name = FONT_BODY
                p_body.font.size = Pt(9.5)
                p_body.font.color.rgb = COLOR_MUTED
                p_body.space_after = Pt(10)

    def build_slide_03_solution(self):
        """Slide 3: Our Solution."""
        slide = self.prs.slides.add_slide(self.blank_layout)
        self._set_dark_background(slide)
        self._add_header(
            slide,
            "OUR SOLUTION",
            "PATCHPROOF: Unified Supply-Chain Security & Code Debugging",
            "A deterministic, developer-first platform pairing automated threat intelligence with human-controlled remediation"
        )
        self._add_footer(slide, 3)

        # 3 Pillars Layout
        pillars = [
            (
                "Full-Spectrum Visibility",
                "Complete Software Bill of Materials (SBOM)",
                COLOR_CYAN,
                [
                    "Multi-Ecosystem Ingestion: Python (pip, pyproject.toml), Node.js (package.json, lockfiles), Go (go.mod).",
                    "Dual Standard Export: Generates official CycloneDX v1.5 and SPDX v2.3 compliant SBOM JSON files.",
                    "Deep Git History Secret Scanning: Regex-entropy detection for 7 credential families with immediate rotation playbooks."
                ]
            ),
            (
                "Actionable Threat Intelligence",
                "Explainable Multi-Factor Prioritization",
                COLOR_VIOLET,
                [
                    "Multi-Source Enrichment: Live integration with OSV.dev, NVD CVE records, and official EPSS probability feeds.",
                    "CISA KEV Prioritization: Automatically flags vulnerabilities actively exploited by threat actors in the wild.",
                    "Transparent Risk Formula: Composite 0–100 scoring based on CVSS, exploit probability, depth, and secret exposure."
                ]
            ),
            (
                "Human-Gated Safe Remediations",
                "Verified Minimal Bumps + NEVER_MERGE",
                COLOR_EMERALD,
                [
                    "Minimal SemVer Bumps: Calculates exact non-breaking patch targets (e.g. requests 2.19.1 → 2.20.0).",
                    "Unified Diff Synthesis: Pre-generates ready-to-apply diffs with automatic secret masking and validation guidance.",
                    "NEVER_MERGE Invariant: Absolute architectural enforcement — PATCHPROOF creates Draft PRs; developers own merge rights."
                ]
            )
        ]

        w = Inches(3.64)
        h = Inches(4.7)
        gap = Inches(0.4)
        top = Inches(1.9)

        for i, (title, subtitle, color, bullets) in enumerate(pillars):
            left = Inches(0.8) + i * (w + gap)
            self.add_card(slide, left, top, w, h, title, subtitle, border_color=color)

            tb = slide.shapes.add_textbox(left + Inches(0.2), top + Inches(0.95), w - Inches(0.4), h - Inches(1.1))
            tf = tb.text_frame
            tf.word_wrap = True

            for j, b_text in enumerate(bullets):
                p = tf.paragraphs[0] if j == 0 else tf.add_paragraph()
                p.text = f"✓ {b_text}"
                p.font.name = FONT_BODY
                p.font.size = Pt(10)
                p.font.color.rgb = COLOR_WHITE
                p.space_after = Pt(12)

    def build_slide_04_features(self):
        """Slide 4: Core Platform Capabilities."""
        slide = self.prs.slides.add_slide(self.blank_layout)
        self._set_dark_background(slide)
        self._add_header(
            slide,
            "CORE CAPABILITIES",
            "Full-Spectrum Security & Remediation Engine",
            "Four integrated pillars safeguarding the modern software supply chain from ingest to deploy"
        )
        self._add_footer(slide, 4)

        features = [
            (
                "1. Multi-Format SBOM Engine",
                "Automated Component & Dependency Inventory",
                COLOR_CYAN,
                [
                    "Direct & Transitive Dependency Graph: Full hierarchy parsing for pip, npm, and go modules.",
                    "CycloneDX v1.5 JSON: Package URLs (purls), versions, direct flags, and schema-compliant structure.",
                    "SPDX v2.3 JSON: Machine-readable licensing, relationship mapping, and SHA-256 asset hashes."
                ]
            ),
            (
                "2. Live Threat Intelligence & Fallbacks",
                "Multi-Source Advisory Enrichment",
                COLOR_ROSE,
                [
                    "OSV.dev Batch Queries: Real-time API lookups across global open-source vulnerability registries.",
                    "CISA KEV Integration: High-priority tagging for Known Exploited Vulnerabilities actively tracked by US-CERT.",
                    "EPSS Probability Scoring: 30-day exploit likelihood predictions (e.g. 0.35 = 35% probability).",
                    "Curated Offline Fallback DB: Instant, reliable scanning resilience during network dropouts."
                ]
            ),
            (
                "3. High-Entropy Git Secret Scanner",
                "Deep History Inspection & Leak Neutralization",
                COLOR_AMBER,
                [
                    "7 Credential Families: AWS Access Keys, GitHub PATs, Slack Webhooks, Stripe Keys, Private Keys, JWTs.",
                    "Full Graph Scanning: Traverses all commits, branches, and diff trees rather than just head files.",
                    "Vendor-Specific Runbooks: Actionable revocation guidance and git history purge commands (filter-repo).",
                    "Patch Masking: Guarantees secrets are redacted in diffs to prevent secondary leak propagation."
                ]
            ),
            (
                "4. 13-Class ML Defect Classifier",
                "AST-Aware Semantic Code Debugger",
                COLOR_VIOLET,
                [
                    "13 Defect Classes: Null dereference, memory safety, resource leak, race condition, loop error, etc.",
                    "Hybrid Model: Scikit-learn tabular classifier backed by Python AST structural analysis and regex localization.",
                    "Line-Level Localization: Pinpoints defective lines and generates corrected code remediations.",
                    "Zero-Overclaim Safety: Strict confidence thresholds distinguishing clean code from genuine defects."
                ]
            )
        ]

        w = Inches(5.65)
        h = Inches(2.25)
        gap_x = Inches(0.43)
        gap_y = Inches(0.2)

        for i, (title, subtitle, color, bullets) in enumerate(features):
            col = i % 2
            row = i // 2
            left = Inches(0.8) + col * (w + gap_x)
            top = Inches(1.9) + row * (h + gap_y)

            self.add_card(slide, left, top, w, h, title, subtitle, border_color=color)
            tb = slide.shapes.add_textbox(left + Inches(0.2), top + Inches(0.8), w - Inches(0.4), h - Inches(0.9))
            tf = tb.text_frame
            tf.word_wrap = True

            for j, b in enumerate(bullets):
                p = tf.paragraphs[0] if j == 0 else tf.add_paragraph()
                p.text = f"• {b}"
                p.font.name = FONT_BODY
                p.font.size = Pt(9.5)
                p.font.color.rgb = COLOR_WHITE
                p.space_after = Pt(3)

    def build_slide_05_architecture(self):
        """Slide 5: System Architecture."""
        slide = self.prs.slides.add_slide(self.blank_layout)
        self._set_dark_background(slide)
        self._add_header(
            slide,
            "SYSTEM ARCHITECTURE",
            "Modular, Scalable, Human-Centric Platform Design",
            "High-throughput FastAPI backend powering an interactive React dashboard with strict safety boundaries"
        )
        self._add_footer(slide, 5)

        # 3 Architectural Tiers Layout
        tiers = [
            (
                "TIER 1: FRONTEND DASHBOARD",
                "React 18 + TypeScript + Tailwind CSS",
                COLOR_CYAN,
                Inches(0.8),
                [
                    "Interactive Risk Overview Meter (0-100 severity gauge)",
                    "Component & SBOM Explorer (CycloneDX/SPDX downloads)",
                    "Vulnerability Table with CISA KEV & EPSS badges",
                    "Secret Leak Viewer with vendor remediation playbooks",
                    "Unified Diff Viewer with inline patch inspections",
                    "AI Code Debugger console with syntax-highlighted fixes"
                ]
            ),
            (
                "TIER 2: BACKEND ORCHESTRATION",
                "FastAPI Asynchronous Security Microservices",
                COLOR_VIOLET,
                Inches(4.8),
                [
                    "RepositoryService: Git ingestion, branch tree traversal",
                    "DependencyParser: pip, npm, and go manifest extraction",
                    "SBOMService: Standardized CycloneDX & SPDX synthesis",
                    "VulnerabilityService: Multi-source threat enrichment",
                    "SecretScanner: High-entropy regex pattern matching",
                    "RiskEngine: Multi-factor composite scoring engine",
                    "RemediationService: SemVer bumps & unified diff generator"
                ]
            ),
            (
                "TIER 3: INTELLIGENCE & SAFETY",
                "Threat Feeds, ML Debugger & Security Gates",
                COLOR_EMERALD,
                Inches(8.8),
                [
                    "Live Threat Feeds: OSV.dev batch API & EPSS probabilities",
                    "Curated Offline DB: High-fidelity fallback knowledge base",
                    "ML Debugger: 13-class defect detector (bug_detector.joblib)",
                    "AST Analysis Engine: Python AST inspection & patch generator",
                    "NEVER_MERGE Invariant: Hardcoded safety gate on all PR APIs",
                    "Audit Logger: Per-event SHA-256 in-memory tamper evidence"
                ]
            )
        ]

        w = Inches(3.733)
        h = Inches(4.7)
        top = Inches(1.9)

        for title, subtitle, color, left, items in tiers:
            self.add_card(slide, left, top, w, h, title, subtitle, border_color=color)
            tb = slide.shapes.add_textbox(left + Inches(0.2), top + Inches(0.95), w - Inches(0.4), h - Inches(1.1))
            tf = tb.text_frame
            tf.word_wrap = True

            for j, item in enumerate(items):
                p = tf.paragraphs[0] if j == 0 else tf.add_paragraph()
                p.text = f"▸ {item}"
                p.font.name = FONT_BODY
                p.font.size = Pt(9.5)
                p.font.color.rgb = COLOR_WHITE
                p.space_after = Pt(8)

    def build_slide_06_workflow(self):
        """Slide 6: Repository Analysis Workflow."""
        slide = self.prs.slides.add_slide(self.blank_layout)
        self._set_dark_background(slide)
        self._add_header(
            slide,
            "ANALYSIS PIPELINE",
            "End-to-End Repository Security Analysis Workflow",
            "Deterministic 5-stage pipeline processing repositories from ingest to human-gated remediation"
        )
        self._add_footer(slide, 6)

        steps = [
            ("1. Ingestion", "Target Selection", COLOR_SKY, "Developer submits GitHub URL or loads fixture (vulnerable-python, vulnerable-node, secret-leak, secure-go)."),
            ("2. Parsing", "Manifests & Secrets", COLOR_CYAN, "Parses requirements.txt, package.json, go.mod. Executes regex-entropy scan across full git commit history."),
            ("3. Threat Intel", "Multi-Source Query", COLOR_VIOLET, "Queries OSV.dev in batch; fetches EPSS probabilities; cross-references CISA KEV; falls back to curated cache if offline."),
            ("4. Risk & Diffs", "Scoring & Patches", COLOR_AMBER, "Computes composite 0–100 risk score; calculates minimal non-breaking version jumps; synthesizes unified diffs with secret redaction."),
            ("5. Remediation", "Human Authorization", COLOR_EMERALD, "Presents interactive dashboard; generates CycloneDX/SPDX SBOMs; outputs Draft PR proposal for developer review (NEVER_MERGE).")
        ]

        w = Inches(2.2)
        h = Inches(4.7)
        gap = Inches(0.18)
        top = Inches(1.9)

        for i, (num, stage, color, desc) in enumerate(steps):
            left = Inches(0.8) + i * (w + gap)

            card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, w, h)
            card.fill.solid()
            card.fill.fore_color.rgb = COLOR_CARD_BG
            card.line.color.rgb = color
            card.line.width = Pt(1.5)

            # Step number badge
            badge = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left + Inches(0.15), top + Inches(0.2), w - Inches(0.3), Inches(0.45))
            badge.fill.solid()
            badge.fill.fore_color.rgb = RGBColor(20, 24, 45)
            badge.line.color.rgb = color
            badge.line.width = Pt(1)
            tf_b = badge.text_frame
            p_b = tf_b.paragraphs[0]
            p_b.text = num.upper()
            p_b.font.name = FONT_HEADING
            p_b.font.size = Pt(11)
            p_b.font.bold = True
            p_b.font.color.rgb = color
            p_b.alignment = PP_ALIGN.CENTER

            # Stage Name
            tb_s = slide.shapes.add_textbox(left + Inches(0.15), top + Inches(0.8), w - Inches(0.3), Inches(0.4))
            tf_s = tb_s.text_frame
            p_s = tf_s.paragraphs[0]
            p_s.text = stage
            p_s.font.name = FONT_HEADING
            p_s.font.size = Pt(13)
            p_s.font.bold = True
            p_s.font.color.rgb = COLOR_WHITE
            p_s.alignment = PP_ALIGN.CENTER

            # Description
            tb_d = slide.shapes.add_textbox(left + Inches(0.15), top + Inches(1.3), w - Inches(0.3), Inches(3.1))
            tf_d = tb_d.text_frame
            tf_d.word_wrap = True
            p_d = tf_d.paragraphs[0]
            p_d.text = desc
            p_d.font.name = FONT_BODY
            p_d.font.size = Pt(10)
            p_d.font.color.rgb = COLOR_MUTED

    def build_slide_07_sbom(self):
        """Slide 7: SBOM & Threat Intelligence."""
        slide = self.prs.slides.add_slide(self.blank_layout)
        self._set_dark_background(slide)
        self._add_header(
            slide,
            "STANDARDS & THREAT INTEL",
            "Enterprise SBOM Generation & Threat Intelligence",
            "Dual-standard compliance with CycloneDX and SPDX enriched by multi-dimensional exploit telemetry"
        )
        self._add_footer(slide, 7)

        # Left Card: Dual Standards
        left_card = self.add_card(
            slide, Inches(0.8), Inches(1.9), Inches(5.65), Inches(4.7),
            "Dual-Standard SBOM Engine", "Standards-compliant machine-readable transparency",
            COLOR_CYAN
        )
        tb_l = slide.shapes.add_textbox(Inches(1.0), Inches(2.7), Inches(5.25), Inches(3.7))
        tf_l = tb_l.text_frame
        tf_l.word_wrap = True

        sbom_points = [
            ("CycloneDX v1.5 JSON", "Industry standard for application security; includes full component metadata, purl definitions, direct vs. transitive flags, and vulnerability linkages."),
            ("SPDX v2.3 JSON", "Linux Foundation standard for supply chain compliance; provides licensing attributes, supplier relationships, and cryptographic verification hashes."),
            ("Schema Validation Tested", "Verified against official specification JSON schemas; zero structural truncation, malformed syntax, or missing required attributes."),
            ("Complete Dependency Tree", "Recursively maps nested dependency relationships across Python (PyPI), Node.js (npm), and Go modules.")
        ]
        for j, (h_text, b_text) in enumerate(sbom_points):
            p = tf_l.paragraphs[0] if j == 0 else tf_l.add_paragraph()
            p.text = f"▸ {h_text}: "
            p.font.name = FONT_HEADING
            p.font.size = Pt(10.5)
            p.font.bold = True
            p.font.color.rgb = COLOR_CYAN

            run = p.add_run()
            run.text = b_text
            run.font.name = FONT_BODY
            run.font.size = Pt(9.5)
            run.font.bold = False
            run.font.color.rgb = COLOR_WHITE
            p.space_after = Pt(8)

        # Right Card: 4 Threat Intelligence Dimensions
        right_card = self.add_card(
            slide, Inches(6.88), Inches(1.9), Inches(5.65), Inches(4.7),
            "4-Dimensional Threat Enrichment", "From raw CVE IDs to actionable risk context",
            COLOR_VIOLET
        )
        tb_r = slide.shapes.add_textbox(Inches(7.08), Inches(2.7), Inches(5.25), Inches(3.7))
        tf_r = tb_r.text_frame
        tf_r.word_wrap = True

        intel_points = [
            ("OSV.dev API (Live Batch)", "Retrieves authoritative open-source vulnerability records across ecosystems with precise commit ranges and fixed versions."),
            ("CISA KEV Catalog Tagging", "Elevates vulnerabilities verified to be actively weaponized and exploited in the wild (e.g. CVE-2018-18074 in requests)."),
            ("EPSS Exploit Prediction", "Provides empirical 30-day exploit probability scores (0.0 to 1.0) to separate theoretical bugs from imminent threats."),
            ("Curated Offline Knowledge Base", "Guarantees zero-failure scanning resilience during air-gapped operations or remote API dropouts with offline attribution.")
        ]
        for j, (h_text, b_text) in enumerate(intel_points):
            p = tf_r.paragraphs[0] if j == 0 else tf_r.add_paragraph()
            p.text = f"★ {h_text}: "
            p.font.name = FONT_HEADING
            p.font.size = Pt(10.5)
            p.font.bold = True
            p.font.color.rgb = COLOR_VIOLET

            run = p.add_run()
            run.text = b_text
            run.font.name = FONT_BODY
            run.font.size = Pt(9.5)
            run.font.bold = False
            run.font.color.rgb = COLOR_WHITE
            p.space_after = Pt(8)

    def build_slide_08_secrets(self):
        """Slide 8: Secret Detection & Remediation."""
        slide = self.prs.slides.add_slide(self.blank_layout)
        self._set_dark_background(slide)
        self._add_header(
            slide,
            "SECRET INTELLIGENCE",
            "High-Entropy Git History Secret Detection",
            "Deep commit-level credential scanning coupled with vendor-specific neutralization playbooks"
        )
        self._add_footer(slide, 8)

        # Left Card: Detection Patterns
        self.add_card(
            slide, Inches(0.8), Inches(1.9), Inches(5.65), Inches(4.7),
            "7 Credential Detection Families", "Full commit tree regex-entropy scanning",
            COLOR_ROSE
        )
        tb_l = slide.shapes.add_textbox(Inches(1.0), Inches(2.7), Inches(5.25), Inches(3.7))
        tf_l = tb_l.text_frame
        tf_l.word_wrap = True

        secrets = [
            ("AWS Access Key IDs", "AKIA[0-9A-Z]{16} — Immediate cloud account compromise risk."),
            ("GitHub Personal Access Tokens", "ghp_ / github_pat_ — Repository read/write hijacking risk."),
            ("Slack Incoming Webhooks", "hooks.slack.com/services/... — Channel spam and phishing threat."),
            ("Stripe Secret API Keys", "sk_live_[0-9a-zA-Z]{24} — Financial transaction unauthorized access."),
            ("Private Keys (RSA/OpenSSH)", "-----BEGIN (RSA|EC|OPENSSH) PRIVATE KEY-----"),
            ("High-Entropy API Tokens", "Generic Base64/Hex high-entropy secrets and bearer tokens."),
            ("JSON Web Tokens (JWT)", "eyJ... bearer tokens containing claims and sensitive scopes.")
        ]
        for j, (name, pattern) in enumerate(secrets):
            p = tf_l.paragraphs[0] if j == 0 else tf_l.add_paragraph()
            p.text = f"⚠ {name}: "
            p.font.name = FONT_HEADING
            p.font.size = Pt(9.5)
            p.font.bold = True
            p.font.color.rgb = COLOR_ROSE

            run = p.add_run()
            run.text = pattern
            run.font.name = FONT_CODE
            run.font.size = Pt(8.5)
            run.font.color.rgb = COLOR_MUTED
            p.space_after = Pt(4)

        # Right Card: Remediation Playbooks
        self.add_card(
            slide, Inches(6.88), Inches(1.9), Inches(5.65), Inches(4.7),
            "Vendor Remediation Playbooks & Patch Redaction", "Safe neutralization without propagation",
            COLOR_EMERALD
        )
        tb_r = slide.shapes.add_textbox(Inches(7.08), Inches(2.7), Inches(5.25), Inches(3.7))
        tf_r = tb_r.text_frame
        tf_r.word_wrap = True

        playbook_points = [
            ("Automated Diff Masking", "When PATCHPROOF proposes code diffs, all detected credentials are automatically redacted (e.g. AKIA****************) so remediation patches never leak secrets."),
            ("Vendor Rotation Guidance", "Provides tailored step-by-step revocation procedures for AWS IAM, GitHub Token Management, Stripe Dashboard, and Slack App console."),
            ("Git History Purge Playbook", "Generates safe commands utilizing git-filter-repo and BFG Repo-Cleaner to completely scrub leaked blobs from historical commits."),
            ("Zero Deceptive Silence", "Clearly flags whether an exposed secret remains active in the current HEAD or was buried in previous commit revisions.")
        ]
        for j, (h_text, b_text) in enumerate(playbook_points):
            p = tf_r.paragraphs[0] if j == 0 else tf_r.add_paragraph()
            p.text = f"✓ {h_text}: "
            p.font.name = FONT_HEADING
            p.font.size = Pt(10.5)
            p.font.bold = True
            p.font.color.rgb = COLOR_EMERALD

            run = p.add_run()
            run.text = b_text
            run.font.name = FONT_BODY
            run.font.size = Pt(9.5)
            run.font.bold = False
            run.font.color.rgb = COLOR_WHITE
            p.space_after = Pt(8)

    def build_slide_09_risk_engine(self):
        """Slide 9: Explainable Risk Engine."""
        slide = self.prs.slides.add_slide(self.blank_layout)
        self._set_dark_background(slide)
        self._add_header(
            slide,
            "RISK ENGINE",
            "Explainable, Multi-Factor Risk Prioritization",
            "A deterministic scoring formula eliminating black-box guesswork and CVE alert fatigue"
        )
        self._add_footer(slide, 9)

        # Top Banner: Mathematical Formula
        form_card = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.9), Inches(11.733), Inches(1.2)
        )
        form_card.fill.solid()
        form_card.fill.fore_color.rgb = COLOR_CARD_BG
        form_card.line.color.rgb = COLOR_CYAN
        form_card.line.width = Pt(1)

        tb_f = slide.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(11.3), Inches(1.0))
        tf_f = tb_f.text_frame
        p_ft = tf_f.paragraphs[0]
        p_ft.text = "THE PATCHPROOF COMPOSITE RISK FORMULA (0–100 SCALE)"
        p_ft.font.name = FONT_HEADING
        p_ft.font.size = Pt(11)
        p_ft.font.bold = True
        p_ft.font.color.rgb = COLOR_CYAN

        p_fe = tf_f.add_paragraph()
        p_fe.text = "Vuln Risk = (CVSS × 0.40) + (EPSS × 10 × 0.25) + (CISA KEV Bonus: 25) + (Direct: +10 | Transitive: +5)"
        p_fe.font.name = FONT_CODE
        p_fe.font.size = Pt(11)
        p_fe.font.bold = True
        p_fe.font.color.rgb = COLOR_WHITE

        p_fe2 = tf_f.add_paragraph()
        p_fe2.text = "Repo Risk = min(100, max(Max Vuln Risk, Secret Penalty) + Total Exposure Density Factor)"
        p_fe2.font.name = FONT_CODE
        p_fe2.font.size = Pt(9.5)
        p_fe2.font.color.rgb = COLOR_MUTED

        # Bottom 4 Severity Tiers Cards
        tiers = [
            ("CRITICAL (80–100)", COLOR_ROSE, [
                "CISA KEV active exploits (e.g. requests 2.19.1 CVE-2018-18074)",
                "Exposed active AWS/GitHub secret tokens in repository",
                "High CVSS (>8.5) with EPSS exploit probability >25%",
                "Immediate developer intervention required"
            ]),
            ("HIGH (60–79)", COLOR_AMBER, [
                "Critical CVSS vulnerabilities (>9.0) lacking public exploits",
                "Direct dependency vulnerabilities with known fixes",
                "Exposed private keys in historical inactive branches",
                "Priority remediation in next scheduled release"
            ]),
            ("MEDIUM (40–59)", COLOR_SKY, [
                "Transitive sub-dependencies with moderate CVSS (4.0–6.9)",
                "Low exploit probability (EPSS < 5%)",
                "Generic high-entropy strings requiring manual verification",
                "Remediate during standard maintenance cycle"
            ]),
            ("LOW / SAFE (0–39)", COLOR_EMERALD, [
                "Informational advisories with zero known exploit path",
                "Transitive packages isolated in development fixtures",
                "Secure control baseline (e.g. secure-go repository)",
                "Documented in SBOM without urgent patch action"
            ])
        ]

        w = Inches(2.7)
        h = Inches(3.3)
        gap = Inches(0.3)
        top = Inches(3.3)

        for i, (name, color, bullets) in enumerate(tiers):
            left = Inches(0.8) + i * (w + gap)
            self.add_card(slide, left, top, w, h, name, border_color=color)

            tb = slide.shapes.add_textbox(left + Inches(0.15), top + Inches(0.65), w - Inches(0.3), h - Inches(0.75))
            tf = tb.text_frame
            tf.word_wrap = True

            for j, b in enumerate(bullets):
                p = tf.paragraphs[0] if j == 0 else tf.add_paragraph()
                p.text = f"• {b}"
                p.font.name = FONT_BODY
                p.font.size = Pt(9)
                p.font.color.rgb = COLOR_WHITE
                p.space_after = Pt(4)

    def build_slide_10_remediation(self):
        """Slide 10: Safe Dependency Remediation."""
        slide = self.prs.slides.add_slide(self.blank_layout)
        self._set_dark_background(slide)
        self._add_header(
            slide,
            "SAFE REMEDIATION",
            "Safe Dependency Remediation & Unified Diff Synthesis",
            "Calculates non-breaking minimal version jumps and compiles production-ready patch proposals"
        )
        self._add_footer(slide, 10)

        # 3 Pillar Columns
        pillars = [
            (
                "1. Minimal SemVer Bumping",
                "Avoiding Breaking API Jumps",
                COLOR_CYAN,
                [
                    ("Conventional Bots Problem", "Standard bots bump to the latest major version (e.g. 2.19.1 → 3.0.0), breaking production API contracts."),
                    ("The PATCHPROOF Algorithm", "Parses ecosystem advisory fixed ranges to identify the smallest valid non-breaking version bump (e.g. requests 2.19.1 → 2.20.0)."),
                    ("Zero Breaking Changes", "Maintains existing method signatures, configuration keys, and runtime behavior while eliminating the target CVE.")
                ]
            ),
            (
                "2. Unified Diff Generation",
                "Ready-to-Apply Standard Patches",
                COLOR_VIOLET,
                [
                    ("Standard diff -u Format", "Produces compliant unified diffs compatible with git apply, patch, and GitHub pull request views."),
                    ("Multi-Manifest Support", "Synthesizes precise patch hunks across requirements.txt, pyproject.toml, package.json, and go.mod."),
                    ("Secret Redaction In Diffs", "Built-in redaction filter ensures sensitive secrets are replaced with masking symbols (AKIA****) so patches never propagate leaks.")
                ]
            ),
            (
                "3. Human-Authorized Draft PRs",
                "Actionable Developer Pull Requests",
                COLOR_EMERALD,
                [
                    ("Structured PR Proposal", "Includes descriptive commit message, CVE references, CVSS/EPSS threat context, and test verification commands."),
                    ("Dry-Run Simulation Ready", "Allows engineers to preview, review, or copy the exact patch hunk before touching remote branches."),
                    ("Full Human Control", "Adheres strictly to NEVER_MERGE — PRs are created as drafts for human review and authorization.")
                ]
            )
        ]

        w = Inches(3.64)
        h = Inches(4.7)
        gap = Inches(0.4)
        top = Inches(1.9)

        for i, (title, subtitle, color, items) in enumerate(pillars):
            left = Inches(0.8) + i * (w + gap)
            self.add_card(slide, left, top, w, h, title, subtitle, border_color=color)

            tb = slide.shapes.add_textbox(left + Inches(0.2), top + Inches(0.95), w - Inches(0.4), h - Inches(1.1))
            tf = tb.text_frame
            tf.word_wrap = True

            for j, (h_text, b_text) in enumerate(items):
                p = tf.paragraphs[0] if j == 0 else tf.add_paragraph()
                p.text = f"▸ {h_text}: "
                p.font.name = FONT_HEADING
                p.font.size = Pt(10)
                p.font.bold = True
                p.font.color.rgb = color

                run = p.add_run()
                run.text = b_text
                run.font.name = FONT_BODY
                run.font.size = Pt(9)
                run.font.bold = False
                run.font.color.rgb = COLOR_WHITE
                p.space_after = Pt(8)

    def build_slide_11_never_merge(self):
        """Slide 11: NEVER_MERGE Invariant."""
        slide = self.prs.slides.add_slide(self.blank_layout)
        self._set_dark_background(slide)
        self._add_header(
            slide,
            "SAFETY INVARIANT",
            "The NEVER_MERGE Architecture: Safety by Design",
            "Why PATCHPROOF architecturally prohibits automated merges into production repositories"
        )
        self._add_footer(slide, 11)

        # Left Card: The Threat of Autonomous Merging
        self.add_card(
            slide, Inches(0.8), Inches(1.9), Inches(5.65), Inches(4.7),
            "The Peril of Autonomous Merge Bots", "Automated merges create critical supply-chain vectors",
            COLOR_ROSE
        )
        tb_l = slide.shapes.add_textbox(Inches(1.0), Inches(2.7), Inches(5.25), Inches(3.7))
        tf_l = tb_l.text_frame
        tf_l.word_wrap = True

        perils = [
            ("Weaponized Auto-Merge Pipelines", "Adversaries publish malicious dependency updates specifically timed to exploit auto-merging bots in unmonitored repositories."),
            ("Silent CI Regression Introduction", "Autonomous commits bypass human design reviews, introduce architectural regressions, and break downstream dependencies."),
            ("Unaccountable Compliance Violations", "Automated merging of new packages can introduce copyleft (GPL) licenses or unapproved cryptographic libraries without legal clearance."),
            ("Loss of Engineering Accountability", "Security cannot be abdicated to a bot. Every line of code deployed to production requires human ownership.")
        ]
        for j, (h_text, b_text) in enumerate(perils):
            p = tf_l.paragraphs[0] if j == 0 else tf_l.add_paragraph()
            p.text = f"✗ {h_text}: "
            p.font.name = FONT_HEADING
            p.font.size = Pt(10)
            p.font.bold = True
            p.font.color.rgb = COLOR_ROSE

            run = p.add_run()
            run.text = b_text
            run.font.name = FONT_BODY
            run.font.size = Pt(9.5)
            run.font.bold = False
            run.font.color.rgb = COLOR_WHITE
            p.space_after = Pt(8)

        # Right Card: The PATCHPROOF Enforcement Mechanism
        self.add_card(
            slide, Inches(6.88), Inches(1.9), Inches(5.65), Inches(4.7),
            "PATCHPROOF Architectural Enforcement", "Hardcoded safety invariant: NEVER_MERGE_ACTIVE",
            COLOR_EMERALD
        )
        tb_r = slide.shapes.add_textbox(Inches(7.08), Inches(2.7), Inches(5.25), Inches(3.7))
        tf_r = tb_r.text_frame
        tf_r.word_wrap = True

        enforcements = [
            ("Zero Auto-Merge Code Paths", "The platform codebase contains zero merge endpoints, zero auto-merge token scopes, and zero background merge daemons."),
            ("Hardcoded Safety Invariant", "NEVER_MERGE_ACTIVE is returned by the /health endpoint and validated in all service tests to prevent accidental degradation."),
            ("Draft Pull Requests Exclusively", "All generated PR proposals are created in Draft mode, mandating explicit peer review and manual merge authorization."),
            ("Per-Event SHA-256 Audit Trail", "Every analysis, diff generation, and proposal event is logged in memory with an individual SHA-256 cryptographic signature.")
        ]
        for j, (h_text, b_text) in enumerate(enforcements):
            p = tf_r.paragraphs[0] if j == 0 else tf_r.add_paragraph()
            p.text = f"✓ {h_text}: "
            p.font.name = FONT_HEADING
            p.font.size = Pt(10)
            p.font.bold = True
            p.font.color.rgb = COLOR_EMERALD

            run = p.add_run()
            run.text = b_text
            run.font.name = FONT_BODY
            run.font.size = Pt(9.5)
            run.font.bold = False
            run.font.color.rgb = COLOR_WHITE
            p.space_after = Pt(8)

    def build_slide_12_debugger(self):
        """Slide 12: AI Code Debugger."""
        slide = self.prs.slides.add_slide(self.blank_layout)
        self._set_dark_background(slide)
        self._add_header(
            slide,
            "AI DEBUGGER",
            "AI Code Debugger: 13-Class Semantic Defect Detection",
            "Hybrid tabular machine learning combined with AST structural analysis and regex-based localization"
        )
        self._add_footer(slide, 12)

        # Left Card: 13 Defect Taxonomy
        self.add_card(
            slide, Inches(0.8), Inches(1.9), Inches(5.65), Inches(4.7),
            "Canonical 13-Class Defect Taxonomy", "Trained model: models/bug_detector.joblib (SHA-256 verified)",
            COLOR_VIOLET
        )
        tb_l = slide.shapes.add_textbox(Inches(1.0), Inches(2.7), Inches(5.25), Inches(3.7))
        tf_l = tb_l.text_frame
        tf_l.word_wrap = True

        classes = [
            ("null_pointer", "Null / NoneType dereference risk without null-check guard"),
            ("resource_leak", "Unclosed file handles, database streams, or network sockets"),
            ("memory_safety", "Buffer overflow, pointer misuse, out-of-bounds access"),
            ("undefined_behavior", "Uninitialized variables, dangling references, invalid shifts"),
            ("state_management", "Unsynchronized concurrency, data races, global state mutations"),
            ("async_error", "Missing await, unhandled promise rejections, callback deadlocks"),
            ("loop_error / off_by_one", "Infinite loops, loop variable capture, boundary index faults"),
            ("condition / type_error", "Comparison operator errors, invalid type coercions"),
            ("none_correct_code", "High-confidence clean code with zero defect patterns")
        ]
        for j, (c_name, c_desc) in enumerate(classes):
            p = tf_l.paragraphs[0] if j == 0 else tf_l.add_paragraph()
            p.text = f"• {c_name}: "
            p.font.name = FONT_CODE
            p.font.size = Pt(9.5)
            p.font.bold = True
            p.font.color.rgb = COLOR_CYAN

            run = p.add_run()
            run.text = c_desc
            run.font.name = FONT_BODY
            run.font.size = Pt(8.5)
            run.font.color.rgb = COLOR_WHITE
            p.space_after = Pt(3)

        # Right Card: Hybrid Debugging Engine
        self.add_card(
            slide, Inches(6.88), Inches(1.9), Inches(5.65), Inches(4.7),
            "Hybrid Analysis & Patch Synthesis", "Multi-language semantic analysis across 7 languages",
            COLOR_CYAN
        )
        tb_r = slide.shapes.add_textbox(Inches(7.08), Inches(2.7), Inches(5.25), Inches(3.7))
        tf_r = tb_r.text_frame
        tf_r.word_wrap = True

        tech_points = [
            ("Multi-Language Support", "Analyzes Python, JavaScript, TypeScript, C, C++, Java, and Go snippets through tailored language parsers."),
            ("Python AST Structural Inspection", "Parses code into an Abstract Syntax Tree to verify node relationships, control flows, and unhandled exception blocks."),
            ("Line-Level Defect Localization", "Pinpoints the exact source line and column triggering the defect rather than outputting vague file-level warnings."),
            ("Synthesized Code Fixes", "Generates concrete, runnable code remediation replacements (e.g. adding if obj is not None guards or with context managers)."),
            ("Strict Confidence Filtering", "Outputs predictions only when model confidence exceeds calibrated thresholds, suppressing false-positive noise.")
        ]
        for j, (h_text, b_text) in enumerate(tech_points):
            p = tf_r.paragraphs[0] if j == 0 else tf_r.add_paragraph()
            p.text = f"▸ {h_text}: "
            p.font.name = FONT_HEADING
            p.font.size = Pt(10)
            p.font.bold = True
            p.font.color.rgb = COLOR_CYAN

            run = p.add_run()
            run.text = b_text
            run.font.name = FONT_BODY
            run.font.size = Pt(9)
            run.font.bold = False
            run.font.color.rgb = COLOR_WHITE
            p.space_after = Pt(7)

    def build_slide_13_research_journey(self):
        """Slide 13: ML Research Journey."""
        slide = self.prs.slides.add_slide(self.blank_layout)
        self._set_dark_background(slide)
        self._add_header(
            slide,
            "ML RESEARCH",
            "The ML Research Journey: From Baseline to Rigor",
            "Empirical progression from initial heuristic models to discovering dataset limitations and designing leakage-safe splits"
        )
        self._add_footer(slide, 13)

        phases = [
            (
                "PHASE 1: BASELINE",
                "Experiments A–E",
                COLOR_SKY,
                [
                    "Established 13-class defect taxonomy.",
                    "Implemented TF-IDF + n-gram tabular classifiers.",
                    "Evaluated heuristic keyword baselines.",
                    "Initial model deployment to production."
                ]
            ),
            (
                "PHASE 2: RIGOR",
                "Experiments F–L",
                COLOR_CYAN,
                [
                    "Exp F: Multi-language generalization.",
                    "Exp G: Perturbation robustness testing.",
                    "Exp H: Confidence threshold calibration.",
                    "Exp I–L: Tokenizer & AST ablation studies."
                ]
            ),
            (
                "PHASE 3: DISCOVERY",
                "Experiments M & M2",
                COLOR_AMBER,
                [
                    "Audited 96,763 primary corpus vs 105,537 split total.",
                    "CRITICAL DISCOVERY: Test set had 0 samples for 6 defect classes!",
                    "Test set had 0 Go & JS samples.",
                    "Disproved standard random splitting validity."
                ]
            ),
            (
                "PHASE 4: SPLITTER",
                "Experiments N1 & N1.1",
                COLOR_VIOLET,
                [
                    "Designed multi-objective stratified group splitter.",
                    "Enforced strict group isolation constraints.",
                    "Mathematical Proof: Single-group minority classes cannot be split cleanly.",
                    "Proved external dataset acquisition is mandatory."
                ]
            )
        ]

        w = Inches(2.7)
        h = Inches(4.7)
        gap = Inches(0.3)
        top = Inches(1.9)

        for i, (p_num, p_name, color, bullets) in enumerate(phases):
            left = Inches(0.8) + i * (w + gap)
            self.add_card(slide, left, top, w, h, p_num, p_name, border_color=color)

            tb = slide.shapes.add_textbox(left + Inches(0.15), top + Inches(0.95), w - Inches(0.3), h - Inches(1.1))
            tf = tb.text_frame
            tf.word_wrap = True

            for j, b in enumerate(bullets):
                p = tf.paragraphs[0] if j == 0 else tf.add_paragraph()
                p.text = f"• {b}"
                p.font.name = FONT_BODY
                p.font.size = Pt(9.5)
                p.font.color.rgb = COLOR_WHITE
                p.space_after = Pt(10)

    def build_slide_14_dataset_expansion(self):
        """Slide 14: Dataset Expansion (N2A–N2F)."""
        slide = self.prs.slides.add_slide(self.blank_layout)
        self._set_dark_background(slide)
        self._add_header(
            slide,
            "DATASET EXPANSION",
            "Benchmark Acquisition & Zero-Leakage Screening (N2A–N2F)",
            "Acquiring 1,958 genuine bugs across 50 projects to resolve minority class poverty and language bias"
        )
        self._add_footer(slide, 14)

        # Left Card: Big-Vul Lessons
        self.add_card(
            slide, Inches(0.8), Inches(1.9), Inches(5.65), Inches(4.7),
            "The Big-Vul Investigation (N2C–N2E)", "Empirical proof of dataset saturation & leakage risk",
            COLOR_ROSE
        )
        tb_l = slide.shapes.add_textbox(Inches(1.0), Inches(2.7), Inches(5.25), Inches(3.7))
        tf_l = tb_l.text_frame
        tf_l.word_wrap = True

        bigvul_points = [
            ("Extracted 180 C/C++ Candidates", "Targeted null_pointer (CWE-476), resource_leak (CWE-401), and undefined_behavior (CWE-190)."),
            ("High Semantic Quality Confirmed", "N2D quality audit confirmed 69 Confirmed, 111 Plausible, and 0 Mislabeled samples."),
            ("CRITICAL LEAKAGE SCREEN (N2E)", "179 out of 180 candidates (99.4%) overlapped existing train/val/test splits!"),
            ("Only 1 Candidate Eligible", "Exactly 1 sample (pp-bvl-f41e0864540c, QEMU) was eligible without leaking. Proved Big-Vul cannot solve class poverty."),
            ("Scientific Imperative", "Established the mathematical necessity of acquiring genuinely independent external benchmarks.")
        ]
        for j, (h_text, b_text) in enumerate(bigvul_points):
            p = tf_l.paragraphs[0] if j == 0 else tf_l.add_paragraph()
            p.text = f"▸ {h_text}: "
            p.font.name = FONT_HEADING
            p.font.size = Pt(10)
            p.font.bold = True
            p.font.color.rgb = COLOR_ROSE

            run = p.add_run()
            run.text = b_text
            run.font.name = FONT_BODY
            run.font.size = Pt(9)
            run.font.bold = False
            run.font.color.rgb = COLOR_WHITE
            p.space_after = Pt(6)

        # Right Card: N2F Independent Acquisitions
        self.add_card(
            slide, Inches(6.88), Inches(1.9), Inches(5.65), Inches(4.7),
            "External Benchmark Acquisitions (N2F)", "1,958 real bugs across 50 premier repositories (0% commit overlap)",
            COLOR_EMERALD
        )
        tb_r = slide.shapes.add_textbox(Inches(7.08), Inches(2.7), Inches(5.25), Inches(3.7))
        tf_r = tb_r.text_frame
        tf_r.word_wrap = True

        acq_datasets = [
            ("Go Concurrency Bugs (GoBench)", "169 Go bugs across 6 projects (Docker, Kubernetes, etcd, CockroachDB). Pinned commit f265506. Targets state_management & async_error."),
            ("BugsInPy (Python)", "501 Python bugs across 17 projects (FastAPI, Pandas, Requests, SpaCy). Pinned commit 11c5f1e. Targets condition_error & null_pointer."),
            ("BugsJS (JavaScript)", "453 JS bugs across 10 projects (Express, ESLint, Mongoose, Karma). Pinned commit 7abbad3. Dedicated MIT license."),
            ("Defects4J v2.0 (Java)", "835 Java bugs across 17 projects (Apache Commons, Jackson, Jsoup, Mockito). Pinned commit 01f13c6. Dedicated MIT license."),
            ("LEAKAGE AUDIT RESULT", "0 confirmed commit overlaps (0.00%) against all production splits! (Truth Invariant: Production model remains active; N2G–N2L planned).")
        ]
        for j, (h_text, b_text) in enumerate(acq_datasets):
            p = tf_r.paragraphs[0] if j == 0 else tf_r.add_paragraph()
            p.text = f"★ {h_text}: "
            p.font.name = FONT_HEADING
            p.font.size = Pt(10)
            p.font.bold = True
            p.font.color.rgb = COLOR_EMERALD

            run = p.add_run()
            run.text = b_text
            run.font.name = FONT_BODY
            run.font.size = Pt(9)
            run.font.bold = False
            run.font.color.rgb = COLOR_WHITE
            p.space_after = Pt(6)

    def build_slide_15_testing(self):
        """Slide 15: Testing & Verification Architecture."""
        slide = self.prs.slides.add_slide(self.blank_layout)
        self._set_dark_background(slide)
        self._add_header(
            slide,
            "VERIFICATION",
            "Multi-Tiered Automated Testing & Safety Verification",
            "Comprehensive automated test suites spanning application security, API contracts, and ML data integrity"
        )
        self._add_footer(slide, 15)

        # 4 Metric / Category Cards
        suites = [
            (
                "41 Backend & API Tests",
                COLOR_CYAN,
                "Application & API Safety",
                [
                    "9 Safety Guarantee Tests: Enforces NEVER_MERGE, path traversal blocks, secret redactions.",
                    "5 Remediation Diff Tests: Validates unified diff formatting and SemVer minimal bump logic.",
                    "8 Dependency & Secret Tests: Verifies manifest parsing, typosquatting checks, regex entropy.",
                    "19 API & Debug Tests: End-to-end HTTP pipeline and 13-class debugging endpoint tests."
                ]
            ),
            (
                "48 ML Adapter & Splitter Tests",
                COLOR_VIOLET,
                "Data Science & Integrity",
                [
                    "14 Experimental Splitter Tests: Group isolation, deterministic seeding, minority distribution.",
                    "18 Big-Vul Adapter Tests: Pydantic schema validation, syntax sanity, CVE provenance.",
                    "10 Quality & Curation Tests: Confirm vs Plausible audits, test overlap exclusion logic.",
                    "6 Acquisition Audit Tests: Git commit pinning, license auditing, split overlap detection."
                ]
            ),
            (
                "20 HTTP E2E & 14 Readiness Checks",
                COLOR_AMBER,
                "Integration & Release Health",
                [
                    "20 HTTP E2E Checks: Live API integration smoke tests on mock fixtures and health endpoints.",
                    "14 Release Readiness Checks: CycloneDX/SPDX schema validation, SBOM compliance.",
                    "Deterministic SBOM Export: Validated with official CycloneDX & SPDX JSON schemas.",
                    "Tamper-Evident Logging: Per-event SHA-256 cryptographic verification of audit entries."
                ]
            ),
            (
                "Production Frontend Build",
                COLOR_EMERALD,
                "UI Performance & Types",
                [
                    "Clean Vite / TypeScript Build: 100% strict type-checking with zero TypeScript errors.",
                    "Tailwind CSS Dark Theme: Zero CSS layout conflicts, full responsive widescreen design.",
                    "Component Isolation: Standalone SBOM viewer, risk meter, and diff preview components.",
                    "Test Overlap Note: Backend tests focus on API logic; ML tests focus on dataset integrity."
                ]
            )
        ]

        w = Inches(5.65)
        h = Inches(2.25)
        gap_x = Inches(0.43)
        gap_y = Inches(0.2)

        for i, (title, color, category, bullets) in enumerate(suites):
            col = i % 2
            row = i // 2
            left = Inches(0.8) + col * (w + gap_x)
            top = Inches(1.9) + row * (h + gap_y)

            self.add_card(slide, left, top, w, h, title, category, border_color=color)
            tb = slide.shapes.add_textbox(left + Inches(0.2), top + Inches(0.8), w - Inches(0.4), h - Inches(0.9))
            tf = tb.text_frame
            tf.word_wrap = True

            for j, b in enumerate(bullets):
                p = tf.paragraphs[0] if j == 0 else tf.add_paragraph()
                p.text = f"• {b}"
                p.font.name = FONT_BODY
                p.font.size = Pt(9.5)
                p.font.color.rgb = COLOR_WHITE
                p.space_after = Pt(3)

    def build_slide_16_demo(self):
        """Slide 16: Live Demonstration Suite."""
        slide = self.prs.slides.add_slide(self.blank_layout)
        self._set_dark_background(slide)
        self._add_header(
            slide,
            "LIVE DEMO SUITE",
            "Real-World Evaluation Fixtures & Demo Workflows",
            "Four curated test fixtures illustrating diverse threat scenarios and deterministic platform remediation"
        )
        self._add_footer(slide, 16)

        demos = [
            (
                "1. vulnerable-python-repo",
                "Python / PyPI Ecosystem",
                COLOR_ROSE,
                [
                    "Manifest: Outdated requests 2.19.1, urllib3 1.24.1, PyYAML 5.2.",
                    "Active Weaponization: CVE-2018-18074 verified in CISA KEV catalog.",
                    "Platform Action: Risk score elevated to 85.0 (Critical); generates minimal patch to 2.20.0 with unified diff."
                ]
            ),
            (
                "2. vulnerable-node-repo",
                "Node.js / npm Ecosystem",
                COLOR_AMBER,
                [
                    "Manifest: package.json with lodash 4.17.15 and axios 0.21.1.",
                    "Vulnerabilities: Prototype Pollution (CVE-2020-8203) and SSRF (CVE-2020-28168).",
                    "Platform Action: Generates safe version bump to 4.17.19 without breaking lodash API method contracts."
                ]
            ),
            (
                "3. secret-leak-repo",
                "Git History Credential Leaks",
                COLOR_VIOLET,
                [
                    "Exposure: Hardcoded AWS Access Keys and GitHub PATs buried across multiple git commit revisions.",
                    "Platform Action: Scans commit graph; detects high entropy; redacts keys in proposed remediation diffs.",
                    "Output: Vendor-specific revocation playbooks for AWS IAM and GitHub token consoles."
                ]
            ),
            (
                "4. secure-go-repo",
                "Clean Baseline Control",
                COLOR_EMERALD,
                [
                    "Manifest: Clean go.mod utilizing latest secure dependency versions.",
                    "Platform Action: Computes 0 Risk Score; confirms zero known CVEs and zero secret exposures.",
                    "Output: Generates clean CycloneDX and SPDX SBOM proving negative control validity."
                ]
            )
        ]

        w = Inches(5.65)
        h = Inches(2.25)
        gap_x = Inches(0.43)
        gap_y = Inches(0.2)

        for i, (title, ecosystem, color, bullets) in enumerate(demos):
            col = i % 2
            row = i // 2
            left = Inches(0.8) + col * (w + gap_x)
            top = Inches(1.9) + row * (h + gap_y)

            self.add_card(slide, left, top, w, h, title, ecosystem, border_color=color)
            tb = slide.shapes.add_textbox(left + Inches(0.2), top + Inches(0.8), w - Inches(0.4), h - Inches(0.9))
            tf = tb.text_frame
            tf.word_wrap = True

            for j, b in enumerate(bullets):
                p = tf.paragraphs[0] if j == 0 else tf.add_paragraph()
                p.text = f"▸ {b}"
                p.font.name = FONT_BODY
                p.font.size = Pt(9.5)
                p.font.color.rgb = COLOR_WHITE
                p.space_after = Pt(3)

    def build_slide_17_conclusion(self):
        """Slide 17: Conclusion & Strategic Roadmap."""
        slide = self.prs.slides.add_slide(self.blank_layout)
        self._set_dark_background(slide)
        self._add_header(
            slide,
            "ROADMAP & VISION",
            "Current Achievements & Strategic Evolution",
            "From hackathon MVP to enterprise-grade automated software supply-chain security standard"
        )
        self._add_footer(slide, 17)

        # Left Card: Current Achievements
        self.add_card(
            slide, Inches(0.8), Inches(1.9), Inches(5.65), Inches(4.7),
            "Hackathon MVP Achievements", "Production-grade platform ready for deployment",
            COLOR_CYAN
        )
        tb_l = slide.shapes.add_textbox(Inches(1.0), Inches(2.7), Inches(5.25), Inches(3.7))
        tf_l = tb_l.text_frame
        tf_l.word_wrap = True

        achievements = [
            ("Unified Full-Stack Platform", "Operational React dashboard + FastAPI backend with zero external database dependencies."),
            ("Multi-Standard SBOM Ingestion & Export", "CycloneDX v1.5 & SPDX v2.3 JSON compliant exports for Python, Node, and Go."),
            ("Live Threat Intel + CISA KEV Priority", "Multi-source enrichment with EPSS probabilities and offline resilience fallbacks."),
            ("High-Entropy Secret Neutralization", "Full git history scanner with automated diff redaction and vendor runbooks."),
            ("Architectural Safety Invariant", "NEVER_MERGE_ACTIVE strictly enforced; tamper-evident SHA-256 audit trails."),
            ("Scientific ML Rigor", "13-class defect debugger + 1,958 verified independent bugs acquired under N2F.")
        ]
        for j, (h_text, b_text) in enumerate(achievements):
            p = tf_l.paragraphs[0] if j == 0 else tf_l.add_paragraph()
            p.text = f"✓ {h_text}: "
            p.font.name = FONT_HEADING
            p.font.size = Pt(10)
            p.font.bold = True
            p.font.color.rgb = COLOR_CYAN

            run = p.add_run()
            run.text = b_text
            run.font.name = FONT_BODY
            run.font.size = Pt(9)
            run.font.bold = False
            run.font.color.rgb = COLOR_WHITE
            p.space_after = Pt(6)

        # Right Card: Planned Strategic Roadmap
        self.add_card(
            slide, Inches(6.88), Inches(1.9), Inches(5.65), Inches(4.7),
            "Planned Strategic Roadmap (N2G–N2L & Beyond)", "Advancing the frontier of agentic developer security",
            COLOR_VIOLET
        )
        tb_r = slide.shapes.add_textbox(Inches(7.08), Inches(2.7), Inches(5.25), Inches(3.7))
        tf_r = tb_r.text_frame
        tf_r.word_wrap = True

        roadmap = [
            ("Milestones N2G–N2L: Multi-Language Adapters", "Implement dedicated normalization adapters for GoBench, BugsInPy, BugsJS, and Defects4J; train candidate model under group isolation."),
            ("Ephemeral Sandboxed Diff Validation", "Spin up isolated Docker containers to automatically execute test suites against proposed patches before presenting to engineers."),
            ("Native CI/CD Pipeline Integrations", "GitHub Actions, GitLab CI, and Bitbucket Pipelines for automated pull-request risk gatekeeping."),
            ("Cryptographic Sigstore & SLSA Provenance", "Signing generated SBOMs and remediation patches with in-toto and Cosign attestations for verifiable build provenance.")
        ]
        for j, (h_text, b_text) in enumerate(roadmap):
            p = tf_r.paragraphs[0] if j == 0 else tf_r.add_paragraph()
            p.text = f"➔ {h_text}: "
            p.font.name = FONT_HEADING
            p.font.size = Pt(10)
            p.font.bold = True
            p.font.color.rgb = COLOR_VIOLET

            run = p.add_run()
            run.text = b_text
            run.font.name = FONT_BODY
            run.font.size = Pt(9)
            run.font.bold = False
            run.font.color.rgb = COLOR_WHITE
            p.space_after = Pt(8)

    def generate_all(self, output_path: str):
        """Generate all 17 slides and save to disk."""
        print(f"Building slide 1 / {self.total_slides}: Title...")
        self.build_slide_01_title()
        print(f"Building slide 2 / {self.total_slides}: Problem Statement...")
        self.build_slide_02_problem()
        print(f"Building slide 3 / {self.total_slides}: Our Solution...")
        self.build_slide_03_solution()
        print(f"Building slide 4 / {self.total_slides}: Core Capabilities...")
        self.build_slide_04_features()
        print(f"Building slide 5 / {self.total_slides}: System Architecture...")
        self.build_slide_05_architecture()
        print(f"Building slide 6 / {self.total_slides}: Repository Analysis Workflow...")
        self.build_slide_06_workflow()
        print(f"Building slide 7 / {self.total_slides}: SBOM & Threat Intel...")
        self.build_slide_07_sbom()
        print(f"Building slide 8 / {self.total_slides}: Secret Intelligence...")
        self.build_slide_08_secrets()
        print(f"Building slide 9 / {self.total_slides}: Explainable Risk Engine...")
        self.build_slide_09_risk_engine()
        print(f"Building slide 10 / {self.total_slides}: Safe Remediation...")
        self.build_slide_10_remediation()
        print(f"Building slide 11 / {self.total_slides}: NEVER_MERGE Invariant...")
        self.build_slide_11_never_merge()
        print(f"Building slide 12 / {self.total_slides}: AI Debugger...")
        self.build_slide_12_debugger()
        print(f"Building slide 13 / {self.total_slides}: ML Research Journey...")
        self.build_slide_13_research_journey()
        print(f"Building slide 14 / {self.total_slides}: Dataset Expansion...")
        self.build_slide_14_dataset_expansion()
        print(f"Building slide 15 / {self.total_slides}: Testing & Verification...")
        self.build_slide_15_testing()
        print(f"Building slide 16 / {self.total_slides}: Live Demo Suite...")
        self.build_slide_16_demo()
        print(f"Building slide 17 / {self.total_slides}: Conclusion & Roadmap...")
        self.build_slide_17_conclusion()

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        self.prs.save(str(output_file))
        print(f"Successfully generated {self.total_slides} slides at: {output_file.resolve()}")


if __name__ == "__main__":
    out = "C:/PATCHPROOF/presentations/PATCHPROOF_Hackathon_Presentation.pptx"
    builder = PresentationBuilder()
    builder.generate_all(out)
