"""Fire a DOWN and a recovered notification by hand.

This is a development tool developed with Clauude. It is not part of the installed package.

    python dev/try_notify.py                 # uses the name "My website"
    python dev/try_notify.py "Home proxy"    # uses your own name

You should see two popups, two seconds apart. To check what happens with no
desktop session, run it with the desktop variables removed:

    env -u DBUS_SESSION_BUS_ADDRESS -u XDG_RUNTIME_DIR -u DISPLAY \
        -u WAYLAND_DISPLAY python dev/try_notify.py

and to check what happens when notify-send is missing (use your venv's full
path to python so only notify-send disappears):

    env PATH=/nonexistent .venv/bin/python dev/try_notify.py

In both cases there should be no popup, a WARNING in the output, and the
script should still finish normally. It always exits with status 0, because a
failed alert must never stop the program.
"""

import logging
import sys
import time

from service_chaperone.models import ServiceState
from service_chaperone.notify import notify


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    name = sys.argv[1] if len(sys.argv) > 1 else "My website"

    print(f"Sending DOWN for {name!r} ...")
    print(f"  delivered: {notify(name, ServiceState.DOWN)}")

    time.sleep(2)

    print(f"Sending recovered for {name!r} ...")
    print(f"  delivered: {notify(name, ServiceState.UP)}")

    print("Done. The script kept running either way.")
    return 0


if __name__ == "__main__":
    sys.exit(main())