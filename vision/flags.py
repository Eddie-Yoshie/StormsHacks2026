"""Active-flag layout shared by the watchdog and the backend. Keep it dependency-free so the backend can import it."""

# Indexes into a device's active-flags list.
FALL_ACTIVE, DEAD_ACTIVE, BATHROOM_ACTIVE = 0, 1, 2

# Bathroom is off by default: it alerts on any long stay in view, which is wrong outside a bathroom.
DEFAULT_ACTIVE_FLAGS = (True, True, False)

# FallEvent.kind -> index of the active flag whose detector emits it.
ACTIVE_INDEX_BY_KIND = {"fall": FALL_ACTIVE, "dead_check": DEAD_ACTIVE, "bathroom_timeout": BATHROOM_ACTIVE}
