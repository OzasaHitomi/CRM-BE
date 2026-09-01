from crm_be.store.enums.deal_status import DealStatus


def can_transition_deal_status(current_status: DealStatus) -> bool:
    return current_status not in {DealStatus.closed_won, DealStatus.closed_lost}
