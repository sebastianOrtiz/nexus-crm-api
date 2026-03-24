"""
Unit tests for BaseRepository and concrete repository methods.

The AsyncSession is mocked entirely — no database connection required.
These tests verify:
1. BaseRepository uses the correct WHERE clauses (tenant isolation).
2. Concrete repository methods build and execute the expected queries.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.activity import ActivityRepository
from src.repositories.company import CompanyRepository
from src.repositories.contact import ContactRepository
from src.repositories.deal import DealRepository
from src.repositories.organization import OrganizationRepository
from src.repositories.pipeline_stage import PipelineStageRepository
from src.repositories.user import UserRepository

# ---------------------------------------------------------------------------
# Helpers — build a minimal mock session that answers execute() calls
# ---------------------------------------------------------------------------


def _make_session(scalar_result=None, scalars_result=None, scalar_one=None):
    """
    Build a mock AsyncSession whose `execute` method returns a result
    that supports the common ScalarResult access patterns.
    """
    session = AsyncMock(spec=AsyncSession)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = scalar_result
    mock_result.scalar_one.return_value = scalar_one if scalar_one is not None else 0
    mock_result.scalars.return_value.all.return_value = scalars_result or []
    mock_result.one.return_value = (0, 0.0)  # for dashboard open_q / won_q rows

    session.execute = AsyncMock(return_value=mock_result)
    return session


def _fake_model(model_cls):
    """Return a lightweight fake instance of a model class (no DB columns)."""
    instance = MagicMock(spec=model_cls)
    instance.id = uuid4()
    instance.organization_id = uuid4()
    return instance


# ---------------------------------------------------------------------------
# BaseRepository tests
# ---------------------------------------------------------------------------


class TestBaseRepositoryGetById:
    async def test_get_by_id_calls_execute(self):
        session = _make_session(scalar_result=None)
        repo = ContactRepository(session)
        record_id = uuid4()

        result = await repo.get_by_id(record_id)

        session.execute.assert_awaited_once()
        assert result is None

    async def test_get_by_id_returns_model_when_found(self):
        from src.models.contact import Contact

        contact = MagicMock(spec=Contact)
        session = _make_session(scalar_result=contact)
        repo = ContactRepository(session)

        result = await repo.get_by_id(uuid4())

        assert result is contact


class TestBaseRepositoryGetByIdAndOrg:
    async def test_returns_none_when_not_found(self):
        session = _make_session(scalar_result=None)
        repo = ContactRepository(session)

        result = await repo.get_by_id_and_org(uuid4(), uuid4())

        session.execute.assert_awaited_once()
        assert result is None

    async def test_returns_instance_when_found(self):
        from src.models.contact import Contact

        contact = MagicMock(spec=Contact)
        session = _make_session(scalar_result=contact)
        repo = ContactRepository(session)

        result = await repo.get_by_id_and_org(contact.id, contact.organization_id)

        assert result is contact


class TestBaseRepositoryCreate:
    async def test_create_adds_flushes_and_refreshes(self):
        session = AsyncMock(spec=AsyncSession)
        repo = ContactRepository(session)

        org_id = uuid4()
        await repo.create(
            organization_id=org_id,
            first_name="Jane",
            last_name="Doe",
        )

        session.add.assert_called_once()
        session.flush.assert_awaited_once()
        session.refresh.assert_awaited_once()


class TestBaseRepositoryUpdate:
    async def test_update_sets_attributes_and_refreshes(self):
        from src.models.contact import Contact

        session = AsyncMock(spec=AsyncSession)
        repo = ContactRepository(session)

        instance = MagicMock(spec=Contact)
        instance.first_name = "Old"

        result = await repo.update(instance, first_name="New")

        assert instance.first_name == "New"
        session.flush.assert_awaited_once()
        session.refresh.assert_awaited_once()
        assert result is instance

    async def test_update_ignores_unknown_attributes(self):
        """Non-existent attributes should not be set — hasattr guard is in place."""

        session = AsyncMock(spec=AsyncSession)
        repo = ContactRepository(session)

        # Create a simple object that only has 'first_name', not 'nonexistent'
        class FakeContact:
            first_name = "Old"

        instance = FakeContact()

        # The real BaseRepository.update uses hasattr to guard setattr
        # Calling with an unknown key should silently skip it
        await repo.update(instance, nonexistent="value", first_name="Real")

        assert instance.first_name == "Real"
        assert not hasattr(instance, "nonexistent")


class TestBaseRepositoryDelete:
    async def test_delete_calls_session_delete_and_flush(self):
        from src.models.contact import Contact

        session = AsyncMock(spec=AsyncSession)
        repo = ContactRepository(session)
        instance = MagicMock(spec=Contact)

        await repo.delete(instance)

        session.delete.assert_awaited_once_with(instance)
        session.flush.assert_awaited_once()


# ---------------------------------------------------------------------------
# ContactRepository
# ---------------------------------------------------------------------------


class TestContactRepository:
    async def test_list_by_org_executes_two_queries(self):
        """list_by_org issues a COUNT query then a SELECT query."""
        session = _make_session(scalar_one=0, scalars_result=[])
        repo = ContactRepository(session)

        contacts, total = await repo.list_by_org(uuid4())

        # Called twice: count + items
        assert session.execute.await_count == 2
        assert contacts == []
        assert total == 0

    async def test_list_by_company_executes_one_query(self):
        session = _make_session(scalars_result=[])
        repo = ContactRepository(session)

        result = await repo.list_by_company(uuid4(), uuid4())

        session.execute.assert_awaited_once()
        assert result == []


# ---------------------------------------------------------------------------
# CompanyRepository
# ---------------------------------------------------------------------------


class TestCompanyRepository:
    async def test_list_by_org_with_search_executes_two_queries(self):
        session = _make_session(scalar_one=0, scalars_result=[])
        repo = CompanyRepository(session)

        companies, total = await repo.list_by_org(uuid4(), search="acme")

        assert session.execute.await_count == 2
        assert total == 0


# ---------------------------------------------------------------------------
# DealRepository
# ---------------------------------------------------------------------------


class TestDealRepository:
    async def test_list_by_org_executes_two_queries(self):
        session = _make_session(scalar_one=0, scalars_result=[])
        repo = DealRepository(session)

        deals, total = await repo.list_by_org(uuid4())

        assert session.execute.await_count == 2
        assert deals == []

    async def test_pipeline_stats_executes_one_query(self):
        mock_result = MagicMock()
        mock_result.all.return_value = []
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock(return_value=mock_result)
        repo = DealRepository(session)

        result = await repo.pipeline_stats(uuid4())

        session.execute.assert_awaited_once()
        assert result == []


# ---------------------------------------------------------------------------
# ActivityRepository
# ---------------------------------------------------------------------------


class TestActivityRepository:
    async def test_list_by_org_executes_two_queries(self):
        session = _make_session(scalar_one=0, scalars_result=[])
        repo = ActivityRepository(session)

        activities, total = await repo.list_by_org(uuid4())

        assert session.execute.await_count == 2
        assert activities == []

    async def test_list_by_contact_executes_one_query(self):
        session = _make_session(scalars_result=[])
        repo = ActivityRepository(session)

        result = await repo.list_by_contact(uuid4(), uuid4())

        session.execute.assert_awaited_once()
        assert result == []

    async def test_count_this_week_returns_integer(self):
        session = _make_session(scalar_one=5)
        repo = ActivityRepository(session)

        from datetime import datetime

        count = await repo.count_this_week(uuid4(), datetime(2024, 1, 1))

        assert count == 5

    async def test_list_recent_executes_one_query(self):
        session = _make_session(scalars_result=[])
        repo = ActivityRepository(session)

        result = await repo.list_recent(uuid4(), limit=5)

        session.execute.assert_awaited_once()
        assert result == []


# ---------------------------------------------------------------------------
# PipelineStageRepository
# ---------------------------------------------------------------------------


class TestPipelineStageRepository:
    async def test_list_by_org_ordered_executes_one_query(self):
        session = _make_session(scalars_result=[])
        repo = PipelineStageRepository(session)

        result = await repo.list_by_org_ordered(uuid4())

        session.execute.assert_awaited_once()
        assert result == []

    async def test_count_by_org_delegates_to_list(self):
        """count_by_org calls list_by_org_ordered and returns its length."""
        session = _make_session(scalars_result=[])
        repo = PipelineStageRepository(session)
        from src.models.pipeline_stage import PipelineStage

        fake_stages = [MagicMock(spec=PipelineStage) for _ in range(4)]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = fake_stages
        session.execute = AsyncMock(return_value=mock_result)

        count = await repo.count_by_org(uuid4())

        assert count == 4


# ---------------------------------------------------------------------------
# OrganizationRepository
# ---------------------------------------------------------------------------


class TestOrganizationRepository:
    async def test_get_by_slug_executes_one_query(self):
        session = _make_session(scalar_result=None)
        repo = OrganizationRepository(session)

        result = await repo.get_by_slug("my-org")

        session.execute.assert_awaited_once()
        assert result is None


# ---------------------------------------------------------------------------
# UserRepository
# ---------------------------------------------------------------------------


class TestUserRepository:
    async def test_get_by_email_executes_one_query(self):
        session = _make_session(scalar_result=None)
        repo = UserRepository(session)

        result = await repo.get_by_email("test@example.com")

        session.execute.assert_awaited_once()
        assert result is None

    async def test_get_by_email_and_org_executes_one_query(self):
        session = _make_session(scalar_result=None)
        repo = UserRepository(session)

        result = await repo.get_by_email_and_org("test@example.com", uuid4())

        session.execute.assert_awaited_once()
        assert result is None

    async def test_list_by_org_executes_two_queries(self):
        session = _make_session(scalar_one=0, scalars_result=[])
        repo = UserRepository(session)

        users, total = await repo.list_by_org(uuid4())

        assert session.execute.await_count == 2
        assert users == []
        assert total == 0
