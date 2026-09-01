from enum import StrEnum


class DealStatus(StrEnum):
    lead = "lead"
    hearing = "hearing"
    proposal = "proposal"
    negotiation = "negotiation"
    closed_won = "closed_won"
    closed_lost = "closed_lost"
