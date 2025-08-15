import sys
import time
import threading
import subprocess
import random
import select
import tty
import termios

STOP_KEY = "q"

LOG_INTERVAL = 0.5


MESSAGES = [
    "Fetching data chunk...",
    "Parsing records...",
    "Transforming values...",
    "Writing to database...",
    "Cleaning up resources...",
    "Finalizing report...",
]


def prevent_sleep():
    """
    Prevents the Mac from sleeping by launching the `caffeinate` subprocess.
    """
    try:
        return subprocess.Popen(["caffeinate", "-s"])
    except FileNotFoundError:
        print("Warning: `caffeinate` not found. The system may sleep during the run.")
        return None


def key_listener(stop_event):
    """
    Listens for a specific keypress (STOP_KEY) in raw mode and sets the event when detected.
    """
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    tty.setcbreak(fd)
    try:
        while not stop_event.is_set():
            dr, _, _ = select.select([sys.stdin], [], [], 0.1)
            if dr:
                ch = sys.stdin.read(1)
                if ch == STOP_KEY:
                    stop_event.set()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def simulate_processing():
    """
    Simulates streaming log output until the STOP_KEY is pressed.
    After stopping, prints the total elapsed time.
    """
    # Prevent system sleep
    caffeinate_proc = prevent_sleep()

    stop_event = threading.Event()
    listener = threading.Thread(target=key_listener, args=(stop_event,), daemon=True)
    listener.start()

    print(f"Simulation running. Press '{STOP_KEY}' to stop.")
    start_time = time.time()

    try:
        while not stop_event.is_set():
            # Print a random log message
            msg = random.choice(MESSAGES)
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] {msg}")
            time.sleep(LOG_INTERVAL)
    except KeyboardInterrupt:
        # Ignore other interrupts
        pass
    finally:
        # Clean up caffeinate
        if caffeinate_proc:
            caffeinate_proc.terminate()

    elapsed = time.time() - start_time
    print(f"\nSimulation stopped. Total run time: {elapsed:.2f} seconds.")


if __name__ == "__main__":
    simulate_processing()
