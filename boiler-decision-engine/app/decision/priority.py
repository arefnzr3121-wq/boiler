from dataclasses import dataclass

from app.config.constants import DecisionPriority


@dataclass(frozen=True)
class PriorityRule:
    """
    تعریف یک سطح اولویت تصمیم.
    """

    priority: DecisionPriority
    name: str
    description: str


EMERGENCY_RULE = PriorityRule(
    priority=DecisionPriority.EMERGENCY,
    name="emergency",
    description="Emergency condition requires immediate shutdown",
)

SAFETY_RULE = PriorityRule(
    priority=DecisionPriority.SAFETY,
    name="safety",
    description="Safety condition overrides normal operation",
)

FAULT_RULE = PriorityRule(
    priority=DecisionPriority.FAULT,
    name="fault",
    description="Equipment or system fault",
)

MANUAL_RULE = PriorityRule(
    priority=DecisionPriority.MANUAL,
    name="manual",
    description="Manual operator command",
)

SCHEDULE_RULE = PriorityRule(
    priority=DecisionPriority.SCHEDULE,
    name="schedule",
    description="Scheduled operation",
)

COMFORT_RULE = PriorityRule(
    priority=DecisionPriority.COMFORT,
    name="comfort",
    description="Comfort demand",
)

ENERGY_OPTIMIZATION_RULE = PriorityRule(
    priority=DecisionPriority.ENERGY_OPTIMIZATION,
    name="energy_optimization",
    description="Energy optimization decision",
)

DEFAULT_RULE = PriorityRule(
    priority=DecisionPriority.DEFAULT,
    name="default",
    description="Default system state",
)


class DecisionPriorityResolver:
    """
    انتخاب بالاترین اولویت بین تصمیم‌های موجود.
    """

    def resolve(
        self,
        priorities: list[DecisionPriority],
    ) -> DecisionPriority:

        if not priorities:
            return DecisionPriority.DEFAULT

        return min(priorities)