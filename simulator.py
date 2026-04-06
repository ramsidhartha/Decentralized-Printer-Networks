import numpy as np


def simulate_print_job(scenario: str, duration_seconds: int) -> list:
    """
    Simulate sensor time-series for a 3D print job.

    Args:
        scenario: 'legitimate' or 'fake'
        duration_seconds: total job duration in seconds (use 2820)

    Returns:
        list of dicts, one per second
        each dict has exactly three keys: power (W), thermal (C), filament (mm/s)
        phase key is intentionally excluded — phase is determined externally
        by get_expected_phase() in the snapshot engine, not inferred from readings
    """
    data = []

    for t in range(duration_seconds):

        # fake scenario — idle throughout, printer never runs
        if scenario == "fake":
            power    = np.random.normal(47, 3)
            thermal  = np.random.normal(23, 1)
            filament = 0.0
            data.append({
                'power'   : float(power),
                'thermal' : float(thermal),
                'filament': float(filament)
            })
            continue

        # legitimate scenario — determine phase from time boundaries
        if t <= 60:
            phase = "idle"
        elif t <= 300:
            phase = "heating"
        elif t <= 2700:
            phase = "printing"
        else:
            phase = "cooling"

        # generate readings per phase
        if phase == "idle":
            power    = np.random.normal(45, 3)
            thermal  = np.random.normal(23, 1)
            filament = 0.0

        elif phase == "heating":
            progress = (t - 60) / (300 - 60)
            power    = np.random.normal(200, 20)
            thermal  = 25 + progress * (210 - 25) + np.random.normal(0, 2)
            filament = 0.0

        elif phase == "printing":
            power    = np.random.normal(350, 20)
            thermal  = np.random.normal(210, 2)
            # std reduced from 2 to 0.8 to keep readings within envelope (8, 15)
            # mean=10 std=0.8 gives range approximately 7.6 to 12.4 at 3 sigma
            filament = np.random.normal(10, 0.5)

        elif phase == "cooling":
            progress = (t - 2700) / (2820 - 2700)
            power    = np.random.normal(60, 5)
            thermal  = 210 - progress * (210 - 30) + np.random.normal(0, 2)
            filament = 0.0

        # three keys only — no phase key
        data.append({
            'power'   : float(power),
            'thermal' : float(thermal),
            'filament': float(filament)
        })

    return data


# ------------------ PHASE SCHEDULE ------------------
# phase is determined by time boundaries, not inferred from sensor readings
# this lives here as reference — snapshot engine imports get_expected_phase directly

PHASE_BOUNDARIES = {
    "idle"    : (0,    60),
    "heating" : (60,   300),
    "printing": (300,  2700),
    "cooling" : (2700, 2820)
}

def get_expected_phase(t: int) -> str:
    """
    Returns the expected operational phase at time bucket t.
    Derived from job specification (G-code phase schedule).
    In production this is parsed from G-code. In simulation it is hardcoded.
    """
    if t <= 60:
        return "idle"
    elif t <= 300:
        return "heating"
    elif t <= 2700:
        return "printing"
    else:
        return "cooling"


# ------------------ DEBUG ------------------

def debug_legit(data):
    print("\n--- LEGITIMATE DEBUG ---")
    print("Length:", len(data))
    print("Idle    t=10  :", data[10])
    print("Heating t=150 :", data[150])
    print("Printing t=1500:", data[1500])
    print("Cooling t=2819:", data[-1])


def debug_fake(data):
    print("\n--- FAKE DEBUG ---")
    print("Length:", len(data))
    print("Start  :", data[0])
    print("Middle :", data[1500])
    print("End    :", data[-1])


# ------------------ VALIDATION ------------------

def filament_check(data):
    filament_vals = [d['filament'] for d in data]
    print("\n--- FILAMENT CHECK ---")
    print("Total Filament:", sum(filament_vals))
    print("Max Filament  :", max(filament_vals))
    print("Min Filament  :", min(filament_vals))
    # check no legitimate printing reading exceeds envelope
    printing_vals = [d['filament'] for i, d in enumerate(data)
                     if 301 <= i <= 2700]
    if printing_vals:
        violations = [v for v in printing_vals if v < 8 or v > 15]
        print(f"Envelope violations (8-15): {len(violations)} / {len(printing_vals)}")


def envelope_check(data):
    """Verify all readings stay within expected phase envelopes."""
    envelopes = {
        "idle"    : {"power": (40,  60),  "thermal": (20, 30),  "filament": (0,  0)},
        "heating" : {"power": (150, 250), "thermal": (30, 210), "filament": (0,  0)},
        "printing": {"power": (300, 400), "thermal": (205, 215),"filament": (8,  15)},
        "cooling" : {"power": (40,  80),  "thermal": (25, 210), "filament": (0,  0)}
    }
    print("\n--- ENVELOPE CHECK ---")
    violations = 0
    for t, reading in enumerate(data):
        phase = get_expected_phase(t)
        env   = envelopes[phase]
        if not (env["power"][0]    <= reading["power"]    <= env["power"][1]):
            violations += 1
        if not (env["thermal"][0]  <= reading["thermal"]  <= env["thermal"][1]):
            violations += 1
        if phase == "printing":
            if not (env["filament"][0] <= reading["filament"] <= env["filament"][1]):
                violations += 1
    print(f"Total envelope violations: {violations}")


# ------------------ PLOTTING ------------------

def show_both_plots(legit_data, fake_data):
    try:
        import matplotlib.pyplot as plt

        legit_power    = [d['power']    for d in legit_data]
        legit_thermal  = [d['thermal']  for d in legit_data]
        legit_filament = [d['filament'] for d in legit_data]

        fake_power    = [d['power']    for d in fake_data]
        fake_thermal  = [d['thermal']  for d in fake_data]
        fake_filament = [d['filament'] for d in fake_data]

        plt.figure(figsize=(12, 8))

        plt.subplot(2, 1, 1)
        plt.plot(legit_power,    label='Power (W)')
        plt.plot(legit_thermal,  label='Thermal (C)')
        plt.plot(legit_filament, label='Filament (mm/s)')
        plt.title("Legitimate Job — four phase profile")
        plt.legend()
        plt.grid()

        plt.subplot(2, 1, 2)
        plt.plot(fake_power,    label='Power (W)')
        plt.plot(fake_thermal,  label='Thermal (C)')
        plt.plot(fake_filament, label='Filament (mm/s)')
        plt.title("Fake Job — flat idle throughout")
        plt.legend()
        plt.grid()

        plt.tight_layout()
        plt.show()

    except ImportError:
        print("matplotlib not installed — skipping plots")


# ------------------ MAIN ------------------

if __name__ == "__main__":

    print("\n=== LEGITIMATE JOB ===")
    legit_data = simulate_print_job("legitimate", 2820)
    debug_legit(legit_data)
    filament_check(legit_data)
    envelope_check(legit_data)

    print("\n=== FAKE JOB ===")
    fake_data = simulate_print_job("fake", 2820)
    debug_fake(fake_data)
    filament_check(fake_data)
    envelope_check(fake_data)

    show_both_plots(legit_data, fake_data)