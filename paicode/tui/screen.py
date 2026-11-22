from textual import events
from textual.screen import Screen

DETACHED_SELECTION_ERROR = "'NoneType' object has no attribute 'region'"


class PaiCodeScreen(Screen[None]):
    """Default screen hardened against stale widgets during markdown refresh."""

    def _forward_event(self, event: events.Event) -> None:
        try:
            super()._forward_event(event)
        except AttributeError as error:
            if (
                not isinstance(event, events.MouseDown)
                or DETACHED_SELECTION_ERROR not in str(error)
            ):
                raise
            self.log.warning(
                "Ignored mouse down on a detached markdown widget replaced by a refresh."
            )
