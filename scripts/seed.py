"""
Database seeder for NexusCRM API.

Creates a complete demo dataset for the Acme Corporation tenant including:
- 1 organization + 1 owner user
- 6 pipeline stages
- 8 companies
- 15 contacts
- 12 deals with stage history
- 25 activities

Run with:
    cd /workspace/apps/nexus-crm-api && python -m scripts.seed
"""

# ruff: noqa: E501 S608

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.core.config import settings
from src.core.enums import (
    ActivityType,
    ContactSource,
    DealCurrency,
    OrganizationPlan,
    UserRole,
)
from src.core.security import hash_password
from src.models.activity import Activity
from src.models.base import SCHEMA
from src.models.company import Company
from src.models.contact import Contact
from src.models.deal import Deal
from src.models.deal_stage_history import DealStageHistory
from src.models.organization import Organization
from src.models.pipeline_stage import PipelineStage
from src.models.user import User

# ---------------------------------------------------------------------------
# Engine setup
# ---------------------------------------------------------------------------

engine = create_async_engine(str(settings.DATABASE_URL), echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NOW = datetime.now(UTC)


def days_ago(n: int) -> datetime:
    """Return a timezone-aware UTC datetime n days in the past."""
    return NOW - timedelta(days=n)


def hours_ago(n: int) -> datetime:
    """Return a timezone-aware UTC datetime n hours in the past."""
    return NOW - timedelta(hours=n)


# ---------------------------------------------------------------------------
# Seed functions
# ---------------------------------------------------------------------------


DEMO_EMAIL = "demo@nexuscrm.dev"


async def cleanup_demo_data(session: AsyncSession) -> bool:
    """Delete all demo user data and recreate from scratch."""
    result = await session.execute(select(User).where(User.email == DEMO_EMAIL))
    user = result.scalar_one_or_none()
    if user is None:
        return False

    oid = user.organization_id
    s = SCHEMA

    # Delete in FK-safe order
    hist_q = (
        f"DELETE FROM {s}.deal_stage_history"  # noqa: S608
        f" WHERE deal_id IN"
        f" (SELECT id FROM {s}.deals WHERE organization_id = :oid)"
    )
    await session.execute(text(hist_q), {"oid": oid})
    for tbl in [
        "activities",
        "deals",
        "contacts",
        "companies",
        "pipeline_stages",
        "users",
    ]:
        q = f"DELETE FROM {s}.{tbl} WHERE organization_id = :oid"  # noqa: S608
        await session.execute(text(q), {"oid": oid})
    org_q = f"DELETE FROM {s}.organizations WHERE id = :oid"  # noqa: S608
    await session.execute(text(org_q), {"oid": oid})
    await session.flush()
    return True


async def create_organization(session: AsyncSession) -> Organization:
    """Create the demo tenant organization."""
    org = Organization(
        id=uuid.uuid4(),
        name="Acme Corporation",
        slug="acme-corp",
        plan=OrganizationPlan.PROFESSIONAL.value,
        is_active=True,
    )
    session.add(org)
    await session.flush()
    return org


async def create_owner_user(session: AsyncSession, org_id: uuid.UUID) -> User:
    """Create the demo owner user."""
    user = User(
        id=uuid.uuid4(),
        organization_id=org_id,
        email="demo@nexuscrm.dev",
        password_hash=hash_password("Demo1234!"),
        first_name="John",
        last_name="Smith",
        role=UserRole.OWNER.value,
        is_active=True,
        created_at=days_ago(60),
    )
    session.add(user)
    await session.flush()
    return user


async def create_pipeline_stages(session: AsyncSession, org_id: uuid.UUID) -> list[PipelineStage]:
    """Create the 6 default pipeline stages."""
    stages_data = [
        {"name": "Lead", "order": 1, "color": "#3b82f6", "is_won": False, "is_lost": False},
        {"name": "Qualified", "order": 2, "color": "#8b5cf6", "is_won": False, "is_lost": False},
        {"name": "Proposal", "order": 3, "color": "#f59e0b", "is_won": False, "is_lost": False},
        {"name": "Negotiation", "order": 4, "color": "#ec4899", "is_won": False, "is_lost": False},
        {"name": "Closed Won", "order": 5, "color": "#10b981", "is_won": True, "is_lost": False},
        {"name": "Closed Lost", "order": 6, "color": "#ef4444", "is_won": False, "is_lost": True},
    ]

    stages = []
    for data in stages_data:
        stage = PipelineStage(
            id=uuid.uuid4(),
            organization_id=org_id,
            name=data["name"],
            order=data["order"],
            is_won=data["is_won"],
            is_lost=data["is_lost"],
        )
        session.add(stage)
        stages.append(stage)

    await session.flush()
    return stages


async def create_companies(session: AsyncSession, org_id: uuid.UUID) -> list[Company]:
    """Create 8 realistic tech/SaaS demo companies."""
    companies_data = [
        {
            "name": "TechVista Solutions",
            "domain": "techvista.io",
            "industry": "Software",
            "phone": "+1 (415) 555-0101",
            "address": "100 Market St, Suite 300, San Francisco, CA 94105",
            "notes": "Enterprise software provider specializing in cloud migration. Key decision maker is the CTO.",
        },
        {
            "name": "CloudPeak Inc",
            "domain": "cloudpeak.com",
            "industry": "Cloud Services",
            "phone": "+1 (206) 555-0142",
            "address": "2200 Westlake Ave, Seattle, WA 98121",
            "notes": "Fast-growing cloud infrastructure startup. Series B funded. Strong interest in our analytics module.",
        },
        {
            "name": "DataForge Analytics",
            "domain": "dataforgeanalytics.com",
            "industry": "Data & Analytics",
            "phone": "+1 (512) 555-0187",
            "address": "701 Brazos St, Austin, TX 78701",
            "notes": "Business intelligence consultancy with 200+ clients. Looking for a scalable CRM solution.",
        },
        {
            "name": "NorthBridge Systems",
            "domain": "northbridgesys.com",
            "industry": "IT Consulting",
            "phone": "+1 (617) 555-0234",
            "address": "53 State St, Boston, MA 02109",
            "notes": "IT consulting firm serving the financial sector. Compliance requirements are a top priority.",
        },
        {
            "name": "PulseMedia Group",
            "domain": "pulsemedia.co",
            "industry": "Digital Media",
            "phone": "+1 (212) 555-0378",
            "address": "245 W 17th St, New York, NY 10011",
            "notes": "Digital media company with a growing SaaS product line. Budget approved for Q2.",
        },
        {
            "name": "IronWave Technologies",
            "domain": "ironwave.tech",
            "industry": "Hardware & IoT",
            "phone": "+1 (408) 555-0421",
            "address": "3000 Patrick Henry Dr, Santa Clara, CA 95054",
            "notes": "IoT platform developer. Expanding into enterprise market. Warm referral from TechVista.",
        },
        {
            "name": "Meridian Health Tech",
            "domain": "meridianhealth.io",
            "industry": "Health Technology",
            "phone": "+1 (312) 555-0512",
            "address": "227 W Monroe St, Chicago, IL 60606",
            "notes": "Healthcare SaaS company. HIPAA compliance is non-negotiable. Long sales cycle expected.",
        },
        {
            "name": "Apex Retail Solutions",
            "domain": "apexretail.com",
            "industry": "Retail Technology",
            "phone": "+1 (972) 555-0633",
            "address": "8750 N Central Expy, Dallas, TX 75231",
            "notes": "Omnichannel retail platform. Interested in integrating our CRM with their existing ERP.",
        },
    ]

    companies = []
    for data in companies_data:
        company = Company(
            id=uuid.uuid4(),
            organization_id=org_id,
            name=data["name"],
            domain=data["domain"],
            industry=data["industry"],
            phone=data["phone"],
            address=data["address"],
            notes=data["notes"],
        )
        session.add(company)
        companies.append(company)

    await session.flush()
    return companies


async def create_contacts(
    session: AsyncSession,
    org_id: uuid.UUID,
    owner_id: uuid.UUID,
    companies: list[Company],
) -> list[Contact]:
    """Create 15 realistic English-named contacts distributed across companies."""
    contacts_data = [
        {
            "first_name": "Michael",
            "last_name": "Torres",
            "email": "m.torres@techvista.io",
            "phone": "+1 (415) 555-0102",
            "position": "Chief Technology Officer",
            "source": ContactSource.REFERRAL.value,
            "company_idx": 0,
            "assigned": True,
            "notes": "Decision maker for the cloud migration project. Prefers calls on Thursday afternoons.",
        },
        {
            "first_name": "Sarah",
            "last_name": "Johnson",
            "email": "sjohnson@techvista.io",
            "phone": "+1 (415) 555-0103",
            "position": "VP of Engineering",
            "source": ContactSource.REFERRAL.value,
            "company_idx": 0,
            "assigned": True,
            "notes": "Works closely with Michael Torres. Technical evaluator on the team.",
        },
        {
            "first_name": "David",
            "last_name": "Chen",
            "email": "david.chen@cloudpeak.com",
            "phone": "+1 (206) 555-0143",
            "position": "CEO & Co-Founder",
            "source": ContactSource.EVENT.value,
            "company_idx": 1,
            "assigned": True,
            "notes": "Met at SaaStr Annual. Very interested in scaling the sales pipeline.",
        },
        {
            "first_name": "Emily",
            "last_name": "Rodriguez",
            "email": "e.rodriguez@cloudpeak.com",
            "phone": "+1 (206) 555-0144",
            "position": "Head of Operations",
            "source": ContactSource.EVENT.value,
            "company_idx": 1,
            "assigned": False,
            "notes": "Handles vendor contracts and procurement at CloudPeak.",
        },
        {
            "first_name": "James",
            "last_name": "Whitfield",
            "email": "jwhitfield@dataforgeanalytics.com",
            "phone": "+1 (512) 555-0188",
            "position": "Director of Business Development",
            "source": ContactSource.COLD_OUTREACH.value,
            "company_idx": 2,
            "assigned": True,
            "notes": "Responded positively to our LinkedIn outreach. Evaluating 3 CRM vendors.",
        },
        {
            "first_name": "Amanda",
            "last_name": "Brooks",
            "email": "a.brooks@northbridgesys.com",
            "phone": "+1 (617) 555-0235",
            "position": "Managing Partner",
            "source": ContactSource.WEBSITE.value,
            "company_idx": 3,
            "assigned": True,
            "notes": "Signed up via website contact form. Looking to replace Salesforce.",
        },
        {
            "first_name": "Robert",
            "last_name": "Nguyen",
            "email": "rnguyen@northbridgesys.com",
            "phone": "+1 (617) 555-0236",
            "position": "IT Director",
            "source": ContactSource.WEBSITE.value,
            "company_idx": 3,
            "assigned": False,
            "notes": "Technical point of contact for the NorthBridge evaluation.",
        },
        {
            "first_name": "Jessica",
            "last_name": "Park",
            "email": "jessica.park@pulsemedia.co",
            "phone": "+1 (212) 555-0379",
            "position": "Chief Product Officer",
            "source": ContactSource.SOCIAL_MEDIA.value,
            "company_idx": 4,
            "assigned": True,
            "notes": "Found us through Twitter. Very active on LinkedIn. Interested in the API integration.",
        },
        {
            "first_name": "Thomas",
            "last_name": "Walsh",
            "email": "t.walsh@ironwave.tech",
            "phone": "+1 (408) 555-0422",
            "position": "VP of Sales",
            "source": ContactSource.REFERRAL.value,
            "company_idx": 5,
            "assigned": True,
            "notes": "Referred by Michael Torres at TechVista. Already familiar with our product.",
        },
        {
            "first_name": "Nicole",
            "last_name": "Harrison",
            "email": "nharrison@ironwave.tech",
            "phone": "+1 (408) 555-0423",
            "position": "Sales Operations Manager",
            "source": ContactSource.REFERRAL.value,
            "company_idx": 5,
            "assigned": False,
            "notes": "Will manage the CRM implementation if deal closes.",
        },
        {
            "first_name": "Kevin",
            "last_name": "Patel",
            "email": "k.patel@meridianhealth.io",
            "phone": "+1 (312) 555-0513",
            "position": "CTO",
            "source": ContactSource.EVENT.value,
            "company_idx": 6,
            "assigned": True,
            "notes": "Met at Health Tech Summit. Compliance and data residency are top concerns.",
        },
        {
            "first_name": "Laura",
            "last_name": "Montgomery",
            "email": "l.montgomery@meridianhealth.io",
            "phone": "+1 (312) 555-0514",
            "position": "Head of Data & Analytics",
            "source": ContactSource.EVENT.value,
            "company_idx": 6,
            "assigned": False,
            "notes": "Technical stakeholder. Will be the primary admin user if they sign.",
        },
        {
            "first_name": "Brian",
            "last_name": "Coleman",
            "email": "b.coleman@apexretail.com",
            "phone": "+1 (972) 555-0634",
            "position": "SVP of Technology",
            "source": ContactSource.COLD_OUTREACH.value,
            "company_idx": 7,
            "assigned": True,
            "notes": "Outreach via email sequence. Responded after 3rd touch. Budget decision in Q3.",
        },
        {
            "first_name": "Catherine",
            "last_name": "Foster",
            "email": "cfoster@apexretail.com",
            "phone": "+1 (972) 555-0635",
            "position": "Director of IT",
            "source": ContactSource.COLD_OUTREACH.value,
            "company_idx": 7,
            "assigned": False,
            "notes": "Reports to Brian Coleman. Hands-on with vendor evaluations.",
        },
        {
            "first_name": "Alex",
            "last_name": "Turner",
            "email": "alex.turner@dataforgeanalytics.com",
            "phone": "+1 (512) 555-0189",
            "position": "Senior Data Scientist",
            "source": ContactSource.OTHER.value,
            "company_idx": 2,
            "assigned": False,
            "notes": "Attended our product webinar. Interested in the analytics integrations.",
        },
    ]

    contacts = []
    for data in contacts_data:
        contact = Contact(
            id=uuid.uuid4(),
            organization_id=org_id,
            company_id=companies[data["company_idx"]].id,
            first_name=data["first_name"],
            last_name=data["last_name"],
            email=data["email"],
            phone=data["phone"],
            position=data["position"],
            source=data["source"],
            notes=data["notes"],
            assigned_to_id=owner_id if data["assigned"] else None,
        )
        session.add(contact)
        contacts.append(contact)

    await session.flush()
    return contacts


async def create_deals(
    session: AsyncSession,
    org_id: uuid.UUID,
    owner_id: uuid.UUID,
    stages: list[PipelineStage],
    contacts: list[Contact],
    companies: list[Company],
) -> list[Deal]:
    """
    Create 12 deals distributed across pipeline stages.

    Distribution:
        - Lead: 4 deals
        - Qualified: 3 deals
        - Proposal: 2 deals
        - Negotiation: 1 deal
        - Closed Won: 7 deals (spread across 6 months)
        - Closed Lost: 2 deals
    """
    stage_map = {s.name: s for s in stages}

    deals_data = [
        # --- Lead (4) ---
        {
            "title": "Enterprise SaaS Platform Rollout",
            "value": 48000.00,
            "currency": DealCurrency.USD.value,
            "stage": "Lead",
            "contact_idx": 0,  # Michael Torres / TechVista
            "company_idx": 0,
            "expected_close_days": 45,
            "closed_at": None,
        },
        {
            "title": "Starter Team Plan — DataForge",
            "value": 3600.00,
            "currency": DealCurrency.USD.value,
            "stage": "Lead",
            "contact_idx": 4,  # James Whitfield / DataForge
            "company_idx": 2,
            "expected_close_days": 30,
            "closed_at": None,
        },
        {
            "title": "API Integration Package",
            "value": 8500.00,
            "currency": DealCurrency.USD.value,
            "stage": "Lead",
            "contact_idx": 7,  # Jessica Park / PulseMedia
            "company_idx": 4,
            "expected_close_days": 60,
            "closed_at": None,
        },
        {
            "title": "CRM Onboarding & Training Bundle",
            "value": 2400.00,
            "currency": DealCurrency.USD.value,
            "stage": "Lead",
            "contact_idx": 12,  # Brian Coleman / Apex Retail
            "company_idx": 7,
            "expected_close_days": 90,
            "closed_at": None,
        },
        # --- Qualified (3) ---
        {
            "title": "CloudPeak Growth Plan — Annual",
            "value": 14400.00,
            "currency": DealCurrency.USD.value,
            "stage": "Qualified",
            "contact_idx": 2,  # David Chen / CloudPeak
            "company_idx": 1,
            "expected_close_days": 30,
            "closed_at": None,
        },
        {
            "title": "Sales Force Replacement — NorthBridge",
            "value": 22000.00,
            "currency": DealCurrency.USD.value,
            "stage": "Qualified",
            "contact_idx": 5,  # Amanda Brooks / NorthBridge
            "company_idx": 3,
            "expected_close_days": 45,
            "closed_at": None,
        },
        {
            "title": "IoT Sales Ops Dashboard",
            "value": 9800.00,
            "currency": DealCurrency.USD.value,
            "stage": "Qualified",
            "contact_idx": 8,  # Thomas Walsh / IronWave
            "company_idx": 5,
            "expected_close_days": 20,
            "closed_at": None,
        },
        # --- Proposal (2) ---
        {
            "title": "Healthcare CRM Compliance Package",
            "value": 36000.00,
            "currency": DealCurrency.USD.value,
            "stage": "Proposal",
            "contact_idx": 10,  # Kevin Patel / Meridian
            "company_idx": 6,
            "expected_close_days": 60,
            "closed_at": None,
        },
        {
            "title": "Professional Services Retainer",
            "value": 7200.00,
            "currency": DealCurrency.USD.value,
            "stage": "Proposal",
            "contact_idx": 14,  # Alex Turner / DataForge
            "company_idx": 2,
            "expected_close_days": 25,
            "closed_at": None,
        },
        # --- Negotiation (1) ---
        {
            "title": "TechVista Multi-Seat Enterprise License",
            "value": 50000.00,
            "currency": DealCurrency.USD.value,
            "stage": "Negotiation",
            "contact_idx": 1,  # Sarah Johnson / TechVista
            "company_idx": 0,
            "expected_close_days": 10,
            "closed_at": None,
        },
        # --- Closed Won (7) — spread across 6 months for revenue chart ---
        {
            "title": "Annual Support Contract — CloudPeak",
            "value": 5000.00,
            "currency": DealCurrency.USD.value,
            "stage": "Closed Won",
            "contact_idx": 3,
            "company_idx": 1,
            "expected_close_days": None,
            "closed_at": days_ago(5),
        },
        {
            "title": "Data Migration Service — DataForge",
            "value": 12000.00,
            "currency": DealCurrency.USD.value,
            "stage": "Closed Won",
            "contact_idx": 4,
            "company_idx": 2,
            "expected_close_days": None,
            "closed_at": days_ago(35),
        },
        {
            "title": "NorthBridge Consulting Retainer",
            "value": 18500.00,
            "currency": DealCurrency.USD.value,
            "stage": "Closed Won",
            "contact_idx": 5,
            "company_idx": 3,
            "expected_close_days": None,
            "closed_at": days_ago(65),
        },
        {
            "title": "PulseMedia Ad Platform Integration",
            "value": 9200.00,
            "currency": DealCurrency.USD.value,
            "stage": "Closed Won",
            "contact_idx": 7,
            "company_idx": 4,
            "expected_close_days": None,
            "closed_at": days_ago(95),
        },
        {
            "title": "IronWave IoT Sensor Dashboard",
            "value": 24000.00,
            "currency": DealCurrency.USD.value,
            "stage": "Closed Won",
            "contact_idx": 8,
            "company_idx": 5,
            "expected_close_days": None,
            "closed_at": days_ago(125),
        },
        {
            "title": "Meridian Patient CRM Setup",
            "value": 31000.00,
            "currency": DealCurrency.USD.value,
            "stage": "Closed Won",
            "contact_idx": 10,
            "company_idx": 6,
            "expected_close_days": None,
            "closed_at": days_ago(150),
        },
        {
            "title": "TechVista Q4 License Renewal",
            "value": 15000.00,
            "currency": DealCurrency.USD.value,
            "stage": "Closed Won",
            "contact_idx": 1,
            "company_idx": 0,
            "expected_close_days": None,
            "closed_at": days_ago(175),
        },
        # --- Closed Lost (2) ---
        {
            "title": "SMB Starter Pilot — Apex Retail",
            "value": 1200.00,
            "currency": DealCurrency.USD.value,
            "stage": "Closed Lost",
            "contact_idx": 13,
            "company_idx": 7,
            "expected_close_days": None,
            "closed_at": days_ago(12),
        },
        {
            "title": "CloudPeak Budget Tier Proposal",
            "value": 3500.00,
            "currency": DealCurrency.USD.value,
            "stage": "Closed Lost",
            "contact_idx": 2,
            "company_idx": 1,
            "expected_close_days": None,
            "closed_at": days_ago(80),
        },
    ]

    deals = []
    for data in deals_data:
        stage = stage_map[data["stage"]]
        expected_close = (
            NOW + timedelta(days=data["expected_close_days"])
            if data["expected_close_days"] is not None
            else None
        )
        deal = Deal(
            id=uuid.uuid4(),
            organization_id=org_id,
            title=data["title"],
            value=data["value"],
            currency=data["currency"],
            stage_id=stage.id,
            contact_id=contacts[data["contact_idx"]].id,
            company_id=companies[data["company_idx"]].id,
            assigned_to_id=owner_id,
            expected_close=expected_close,
            closed_at=data["closed_at"],
        )
        session.add(deal)
        deals.append(deal)

    await session.flush()
    return deals


async def create_stage_history(
    session: AsyncSession,
    deals: list[Deal],
    stages: list[PipelineStage],
    owner_id: uuid.UUID,
) -> None:
    """
    Create realistic stage history entries for each deal.

    Each deal gets history entries reflecting its progression from Lead up to
    its current stage. Deals in later stages have more history entries.
    """
    stage_map = {s.name: s for s in stages}
    stage_order = ["Lead", "Qualified", "Proposal", "Negotiation", "Closed Won", "Closed Lost"]

    # Map deal title prefix to determine progression path
    # Deals in Closed Won/Lost have a specific path; others advance linearly from Lead
    for deal in deals:
        current_stage_name = next(s.name for s in stages if s.id == deal.stage_id)

        # Determine stages this deal passed through
        if current_stage_name == "Closed Lost":
            progression = ["Lead", "Qualified", "Closed Lost"]
        elif current_stage_name == "Closed Won":
            progression = ["Lead", "Qualified", "Proposal", "Closed Won"]
        else:
            idx = stage_order.index(current_stage_name)
            progression = stage_order[: idx + 1]

        # Build history entries with realistic timestamps
        # Each stage transition is spaced 3-7 days apart going backwards
        num_stages = len(progression)
        history_entries = []

        for i, stage_name in enumerate(progression):
            stage = stage_map[stage_name]
            is_last = i == num_stages - 1

            # entered_at: progressively more recent as index increases
            days_back_base = (num_stages - 1 - i) * 5 + 5
            entered = days_ago(days_back_base)

            exited: datetime | None = None
            if not is_last:
                days_back_next = (num_stages - 2 - i) * 5 + 5
                exited = days_ago(days_back_next)

            entry = DealStageHistory(
                id=uuid.uuid4(),
                deal_id=deal.id,
                stage_id=stage.id,
                moved_by_id=owner_id,
                entered_at=entered,
                exited_at=exited,
            )
            history_entries.append(entry)

        for entry in history_entries:
            session.add(entry)

    await session.flush()


async def create_activities(
    session: AsyncSession,
    org_id: uuid.UUID,
    owner_id: uuid.UUID,
    contacts: list[Contact],
    deals: list[Deal],
) -> list[Activity]:
    """Create 25 activities spread over the last 30 days."""
    activities_data = [
        # --- Completed calls ---
        {
            "type": ActivityType.CALL.value,
            "subject": "Discovery call with VP of Engineering",
            "description": (
                "Discussed current pain points with their CRM setup. "
                "Team is using spreadsheets for pipeline tracking. "
                "Decision expected within 6 weeks."
            ),
            "contact_idx": 1,  # Sarah Johnson
            "deal_idx": 0,  # Enterprise SaaS Platform
            "scheduled_hours_ago": 24 * 20,
            "completed": True,
        },
        {
            "type": ActivityType.CALL.value,
            "subject": "Qualification call with David Chen",
            "description": (
                "Confirmed budget of $15K/year. "
                "Main requirements: pipeline visualization, email integration, reporting. "
                "Asked for a formal proposal by end of month."
            ),
            "contact_idx": 2,  # David Chen
            "deal_idx": 4,  # CloudPeak Growth Plan
            "scheduled_hours_ago": 24 * 15,
            "completed": True,
        },
        {
            "type": ActivityType.CALL.value,
            "subject": "Intro call with Amanda Brooks",
            "description": (
                "NorthBridge has been on Salesforce for 5 years but finds it too expensive. "
                "They want migration support included. Sent follow-up resources."
            ),
            "contact_idx": 5,  # Amanda Brooks
            "deal_idx": 5,  # Sales Force Replacement
            "scheduled_hours_ago": 24 * 18,
            "completed": True,
        },
        {
            "type": ActivityType.CALL.value,
            "subject": "Technical pre-sales call — Meridian Health",
            "description": (
                "Deep dive into HIPAA compliance features, data residency options, "
                "and audit logging. Kevin wants a security whitepaper before proceeding."
            ),
            "contact_idx": 10,  # Kevin Patel
            "deal_idx": 7,  # Healthcare CRM Compliance Package
            "scheduled_hours_ago": 24 * 10,
            "completed": True,
        },
        {
            "type": ActivityType.CALL.value,
            "subject": "Follow-up call with Thomas Walsh",
            "description": (
                "Thomas confirmed internal approval to move forward. "
                "Waiting on procurement to finalize vendor onboarding paperwork."
            ),
            "contact_idx": 8,  # Thomas Walsh
            "deal_idx": 6,  # IoT Sales Ops Dashboard
            "scheduled_hours_ago": 24 * 8,
            "completed": True,
        },
        {
            "type": ActivityType.CALL.value,
            "subject": "Negotiation call — TechVista enterprise license",
            "description": (
                "Discussed pricing for 50-seat license. "
                "They want a 15% discount and phased rollout option. "
                "Counter-proposal being prepared."
            ),
            "contact_idx": 0,  # Michael Torres
            "deal_idx": 9,  # TechVista Multi-Seat
            "scheduled_hours_ago": 24 * 3,
            "completed": True,
        },
        # --- Completed emails ---
        {
            "type": ActivityType.EMAIL.value,
            "subject": "Sent proposal to NorthBridge Systems",
            "description": (
                "Emailed the full proposal document including migration timeline, "
                "support SLA, and pricing breakdown. Requested feedback by Friday."
            ),
            "contact_idx": 5,  # Amanda Brooks
            "deal_idx": 5,  # Sales Force Replacement
            "scheduled_hours_ago": 24 * 14,
            "completed": True,
        },
        {
            "type": ActivityType.EMAIL.value,
            "subject": "Security whitepaper delivered to Meridian",
            "description": (
                "Sent the security & compliance whitepaper as requested. "
                "CC'd legal team on both sides."
            ),
            "contact_idx": 10,  # Kevin Patel
            "deal_idx": 7,  # Healthcare CRM
            "scheduled_hours_ago": 24 * 9,
            "completed": True,
        },
        {
            "type": ActivityType.EMAIL.value,
            "subject": "Counter-proposal sent to TechVista",
            "description": (
                "Offered 10% discount for 2-year commitment with phased rollout "
                "over 90 days. Added dedicated onboarding support as a sweetener."
            ),
            "contact_idx": 0,  # Michael Torres
            "deal_idx": 9,  # TechVista Multi-Seat
            "scheduled_hours_ago": 24 * 2,
            "completed": True,
        },
        {
            "type": ActivityType.EMAIL.value,
            "subject": "Welcome email — CloudPeak support contract",
            "description": (
                "Sent onboarding instructions and assigned their dedicated account manager. "
                "Invoice for $5,000 attached."
            ),
            "contact_idx": 3,  # Emily Rodriguez
            "deal_idx": 10,  # Annual Support Contract (Won)
            "scheduled_hours_ago": 24 * 5,
            "completed": True,
        },
        {
            "type": ActivityType.EMAIL.value,
            "subject": "Outreach to James Whitfield — DataForge",
            "description": (
                "Initial outreach email following LinkedIn connection. "
                "Introduced NexusCRM capabilities for analytics teams."
            ),
            "contact_idx": 4,  # James Whitfield
            "deal_idx": 1,  # Starter Team Plan DataForge
            "scheduled_hours_ago": 24 * 25,
            "completed": True,
        },
        {
            "type": ActivityType.EMAIL.value,
            "subject": "Feature overview sent to Jessica Park",
            "description": (
                "Sent one-pager on API integration capabilities. "
                "She shared it with her engineering lead."
            ),
            "contact_idx": 7,  # Jessica Park
            "deal_idx": 2,  # API Integration Package
            "scheduled_hours_ago": 24 * 22,
            "completed": True,
        },
        # --- Completed meetings ---
        {
            "type": ActivityType.MEETING.value,
            "subject": "Product demo — CloudPeak executive team",
            "description": (
                "60-minute product demo for David Chen and 3 team members. "
                "Demonstrated pipeline management, reporting dashboard, and Slack integration. "
                "Very positive reception."
            ),
            "contact_idx": 2,  # David Chen
            "deal_idx": 4,  # CloudPeak Growth Plan
            "scheduled_hours_ago": 24 * 12,
            "completed": True,
        },
        {
            "type": ActivityType.MEETING.value,
            "subject": "On-site workshop at NorthBridge HQ",
            "description": (
                "Visited their Boston office for a half-day requirements workshop. "
                "Mapped out 12 key workflows to migrate from Salesforce. "
                "Robert Nguyen was very engaged."
            ),
            "contact_idx": 6,  # Robert Nguyen
            "deal_idx": 5,  # Sales Force Replacement
            "scheduled_hours_ago": 24 * 11,
            "completed": True,
        },
        {
            "type": ActivityType.MEETING.value,
            "subject": "Contract review meeting — TechVista",
            "description": (
                "Legal teams reviewed MSA and DPA. Two minor changes requested. "
                "Final version to be sent Monday."
            ),
            "contact_idx": 1,  # Sarah Johnson
            "deal_idx": 9,  # TechVista Multi-Seat
            "scheduled_hours_ago": 24 * 1,
            "completed": True,
        },
        {
            "type": ActivityType.MEETING.value,
            "subject": "Kickoff meeting — IronWave IoT Dashboard",
            "description": (
                "Introduced the implementation team. Agreed on a 30-day go-live timeline. "
                "Nicole Harrison will lead day-to-day coordination."
            ),
            "contact_idx": 8,  # Thomas Walsh
            "deal_idx": 6,  # IoT Sales Ops
            "scheduled_hours_ago": 24 * 6,
            "completed": True,
        },
        # --- Notes ---
        {
            "type": ActivityType.NOTE.value,
            "subject": "Apex Retail lost — went with HubSpot",
            "description": (
                "Brian confirmed they chose HubSpot due to native marketing automation. "
                "They may reconsider in 12 months when their HubSpot contract expires. "
                "Keep on nurture list."
            ),
            "contact_idx": 12,  # Brian Coleman
            "deal_idx": 11,  # SMB Starter Pilot (Lost)
            "scheduled_hours_ago": 24 * 12,
            "completed": True,
        },
        {
            "type": ActivityType.NOTE.value,
            "subject": "Internal note — TechVista pricing strategy",
            "description": (
                "CFO sign-off required for any discount above 10%. "
                "Will escalate if they push for more. "
                "Deal is strategic — worth some flexibility."
            ),
            "contact_idx": None,
            "deal_idx": 9,  # TechVista Multi-Seat
            "scheduled_hours_ago": 24 * 3,
            "completed": True,
        },
        {
            "type": ActivityType.NOTE.value,
            "subject": "Research note — Meridian Health compliance scope",
            "description": (
                "Reviewed HIPAA Technical Safeguards checklist. "
                "Our platform covers 9/12 requirements out of the box. "
                "Custom audit log export needed for the remaining 3."
            ),
            "contact_idx": 10,  # Kevin Patel
            "deal_idx": 7,  # Healthcare CRM
            "scheduled_hours_ago": 24 * 7,
            "completed": True,
        },
        {
            "type": ActivityType.NOTE.value,
            "subject": "Contact profile note — Alex Turner",
            "description": (
                "Alex attended our webinar and asked several advanced questions about "
                "the analytics connector. Not a decision maker but strong internal champion."
            ),
            "contact_idx": 14,  # Alex Turner
            "deal_idx": 8,  # Professional Services Retainer
            "scheduled_hours_ago": 24 * 16,
            "completed": True,
        },
        # --- Upcoming / scheduled (not completed) ---
        {
            "type": ActivityType.CALL.value,
            "subject": "Follow-up call with Jessica Park — API pricing",
            "description": "Scheduled to discuss API tier pricing and integration timeline.",
            "contact_idx": 7,  # Jessica Park
            "deal_idx": 2,  # API Integration Package
            "scheduled_hours_ago": -24 * 2,  # 2 days in the future
            "completed": False,
        },
        {
            "type": ActivityType.MEETING.value,
            "subject": "Product demo — Brian Coleman at Apex Retail",
            "description": "Re-engagement demo for Apex Retail after initial lost deal.",
            "contact_idx": 12,  # Brian Coleman
            "deal_idx": 3,  # CRM Onboarding Bundle
            "scheduled_hours_ago": -24 * 3,  # 3 days in the future
            "completed": False,
        },
        {
            "type": ActivityType.EMAIL.value,
            "subject": "Send ROI calculator to DataForge",
            "description": "Prepare and send the ROI calculator spreadsheet to James Whitfield.",
            "contact_idx": 4,  # James Whitfield
            "deal_idx": 1,  # Starter Team Plan
            "scheduled_hours_ago": -24 * 1,  # tomorrow
            "completed": False,
        },
        {
            "type": ActivityType.CALL.value,
            "subject": "Scheduled check-in with Kevin Patel — Meridian",
            "description": "Weekly progress check on the proposal review.",
            "contact_idx": 10,  # Kevin Patel
            "deal_idx": 7,  # Healthcare CRM
            "scheduled_hours_ago": -24 * 4,  # 4 days in the future
            "completed": False,
        },
        {
            "type": ActivityType.MEETING.value,
            "subject": "Final contract signing — TechVista",
            "description": "Executive sign-off meeting to close the enterprise deal.",
            "contact_idx": 0,  # Michael Torres
            "deal_idx": 9,  # TechVista Multi-Seat
            "scheduled_hours_ago": -24 * 5,  # 5 days in the future
            "completed": False,
        },
    ]

    activities = []
    for data in activities_data:
        scheduled = hours_ago(int(data["scheduled_hours_ago"]))
        completed_at: datetime | None = scheduled if data["completed"] else None

        activity = Activity(
            id=uuid.uuid4(),
            organization_id=org_id,
            type=data["type"],
            subject=data["subject"],
            description=data["description"],
            contact_id=contacts[data["contact_idx"]].id
            if data["contact_idx"] is not None
            else None,
            deal_id=deals[data["deal_idx"]].id,
            user_id=owner_id,
            scheduled_at=scheduled,
            completed_at=completed_at,
            created_at=scheduled,
        )
        session.add(activity)
        activities.append(activity)

    await session.flush()
    return activities


# ---------------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------------


async def seed() -> None:
    """Run the full seed sequence inside a single transaction."""
    async with AsyncSessionLocal() as session:
        async with session.begin():
            # Ensure the crm schema exists (idempotent)
            await session.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}"))

            # Clean up existing demo data before re-creating
            cleaned = await cleanup_demo_data(session)
            if cleaned:
                print("🧹 Previous demo data cleaned up")

            print("🌱 Starting NexusCRM seed...")

            # 1. Organization
            org = await create_organization(session)
            print(f"🏢 Organization created: {org.name} (slug: {org.slug})")

            # 2. Owner user
            user = await create_owner_user(session, org.id)
            print(f"👤 User created: {user.email} ({user.role})")

            # 3. Pipeline stages
            stages = await create_pipeline_stages(session, org.id)
            print(f"📊 Pipeline stages created: {len(stages)} stages")
            for s in stages:
                flag = " [WON]" if s.is_won else " [LOST]" if s.is_lost else ""
                print(f"   • {s.name}{flag}")

            # 4. Companies
            companies = await create_companies(session, org.id)
            print(f"🏭 Companies created: {len(companies)}")
            for c in companies:
                print(f"   • {c.name} ({c.industry})")

            # 5. Contacts
            contacts = await create_contacts(session, org.id, user.id, companies)
            print(f"👥 Contacts created: {len(contacts)}")

            # 6. Deals
            deals = await create_deals(session, org.id, user.id, stages, contacts, companies)
            print(f"💼 Deals created: {len(deals)}")
            stage_map = {s.id: s.name for s in stages}
            for d in deals:
                print(f"   • [{stage_map[d.stage_id]}] {d.title} — ${d.value:,.2f}")

            # 7. Stage history
            await create_stage_history(session, deals, stages, user.id)
            print("📈 Deal stage history created")

            # 8. Activities
            activities = await create_activities(session, org.id, user.id, contacts, deals)
            completed = sum(1 for a in activities if a.completed_at is not None)
            pending = len(activities) - completed
            print(
                f"📅 Activities created: {len(activities)} ({completed} completed, {pending} upcoming)"
            )

    print()
    print("=" * 50)
    print("✅ Seed completed successfully!")
    print()
    print("  🔐 Demo credentials:")
    print("     Email   : demo@nexuscrm.dev")
    print("     Password: Demo1234!")
    print("     Org     : Acme Corporation (acme-corp)")
    print("=" * 50)


def main() -> None:
    """Synchronous entry point used by python -m scripts.seed."""
    asyncio.run(seed())


if __name__ == "__main__":
    main()
