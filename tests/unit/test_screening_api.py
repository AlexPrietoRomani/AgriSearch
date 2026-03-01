"""
Unit tests for the screening API endpoints.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

@pytest.mark.asyncio
async def test_check_screening_eligibility():
    """
    Test the eligibility check logic to ensure it accurately counts downloaded,
    assigned, and eligible articles.
    """
    from app.api.v1.screening import check_screening_eligibility
    from app.models.schemas import ScreeningEligibilityResponse

    # Create a mock database session
    mock_db = AsyncMock()

    # We need to simulate the 3 database calls:
    # 1. total_downloaded
    # 2. assigned_articles
    # 3. screening_names

    def get_mock_result(return_value, is_scalar=True, is_list=False):
        mock_result = MagicMock()
        if is_scalar:
            mock_result.scalar_one_or_none.return_value = return_value
        elif is_list:
            # For scalars().all()
            mock_scalars = MagicMock()
            mock_scalars.all.return_value = return_value
            mock_result.scalars.return_value = mock_scalars
        return mock_result

    # Configure the responses for consecutive calls to execute()
    # Call 1: 50 total downloaded
    # Call 2: 30 assigned
    # Call 3: ["Session 1"] session names
    mock_db.execute.side_effect = [
        get_mock_result(50, is_scalar=True),
        get_mock_result(30, is_scalar=True),
        get_mock_result(["Session 1"], is_scalar=False, is_list=True)
    ]

    response = await check_screening_eligibility("fake_project_id", db=mock_db)

    assert isinstance(response, ScreeningEligibilityResponse)
    assert response.total_downloaded == 50
    assert response.assigned_articles == 30
    assert response.eligible_articles == 20
    assert response.screening_names == ["Session 1"]


@pytest.mark.asyncio
async def test_check_screening_eligibility_all_assigned():
    """
    Test eligibility when all articles are assigned.
    """
    from app.api.v1.screening import check_screening_eligibility

    def get_mock_result(return_value, is_scalar=True, is_list=False):
        mock_result = MagicMock()
        if is_scalar:
            mock_result.scalar_one_or_none.return_value = return_value
        elif is_list:
            mock_scalars = MagicMock()
            mock_scalars.all.return_value = return_value
            mock_result.scalars.return_value = mock_scalars
        return mock_result

    mock_db = AsyncMock()
    mock_db.execute.side_effect = [
        get_mock_result(100, is_scalar=True),
        get_mock_result(100, is_scalar=True),
        get_mock_result(["S1", "S2"], is_scalar=False, is_list=True)
    ]

    response = await check_screening_eligibility("fake_project", db=mock_db)

    assert response.total_downloaded == 100
    assert response.assigned_articles == 100
    assert response.eligible_articles == 0
    assert response.screening_names == ["S1", "S2"]
