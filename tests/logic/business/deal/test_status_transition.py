import pytest

from crm_be.logic.business.deal.status_transition import can_transition_deal_status
from crm_be.store.enums.deal_status import DealStatus


class TestCanTransitionDealStatus:
    @pytest.mark.parametrize(
        "current_status",
        [DealStatus.lead, DealStatus.hearing, DealStatus.proposal, DealStatus.negotiation],
    )
    def test_returns_true_for_non_terminal_status(self, current_status: DealStatus) -> None:
        assert can_transition_deal_status(current_status) is True

    def test_returns_false_for_closed_won(self) -> None:
        assert can_transition_deal_status(DealStatus.closed_won) is False

    def test_returns_false_for_closed_lost(self) -> None:
        assert can_transition_deal_status(DealStatus.closed_lost) is False
