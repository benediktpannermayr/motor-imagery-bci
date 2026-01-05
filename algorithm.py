import serial
import numpy as np
from scipy.signal import butter, lfilter
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from collections import deque
import time

# -------------------------------
# Signalverarbeitung
# -------------------------------
def butter_bandpass(lowcut, highcut, fs, order=4):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype='band')
    return b, a

def bandpass_filter(data, lowcut, highcut, fs, order=4):
    b, a = butter_bandpass(lowcut, highcut, fs, order=order)
    return lfilter(b, a, data, axis=0)

def compute_bandpower(epoch):
    # mittlere quadratische Amplitude pro Kanal
    return np.mean(epoch**2, axis=0)

# -------------------------------
# Serielle Schnittstelle
# -------------------------------
SERIAL_PORT = 'COM3'
BAUDRATE = 115200 # Baudrate der Seriellen Schnittstelle (muss mit Arduino übereinstimmen)
SAMPLE_RATE = 250  # Frequenz der vom Arduino ankommenden EEG-Werte in Hz
WINDOW_LENGTH = 2  # Sekunden pro Trial
N_SAMPLES = SAMPLE_RATE * WINDOW_LENGTH # Anzahl der Werte im Ringpuffer
STEP_SIZE = SAMPLE_RATE // 60  # ca. 60 Vorhersagen pro Sekunde

ser = serial.Serial(SERIAL_PORT, BAUDRATE)
time.sleep(2)
buffer = deque(maxlen=N_SAMPLES)

# -------------------------------
# Ruhe-Kalibrierung (mehrere Trials)
# -------------------------------
RUHE_TRIALS = 5
PAUSE_BETWEEN_TRIALS = 2  # Sekunden zwischen Ruhe-Trials
features_baseline = []

print(f"=== RUHE-KALIBRIERUNG ({RUHE_TRIALS} Trials) ===")
print("Bitte Hände entspannen, nichts vorstellen...")

for trial in range(RUHE_TRIALS):
    print(f"\nRuhe-Trial {trial+1}/{RUHE_TRIALS} vorbereiten...")
    time.sleep(PAUSE_BETWEEN_TRIALS)
    print("Ruhe jetzt vorstellen!")

    buffer.clear()
    while len(buffer) < N_SAMPLES:
        line = ser.readline().decode('utf-8').strip()
        if not line:
            continue
        try:
            ch1_str, ch2_str = line.split(',')
            ch1 = int(ch1_str)
            ch2 = int(ch2_str)
            buffer.append([ch1, ch2])
        except ValueError:
            continue

    epoch = np.array(buffer, dtype=float)
    epoch = bandpass_filter(epoch, 8, 30, SAMPLE_RATE)
    bp = compute_bandpower(epoch)
    features_baseline.append(bp)
    buffer.clear()
    print(f"Ruhe-Trial {trial+1} abgeschlossen.")

# Baseline als Durchschnitt über alle Ruhe-Trials
baseline = np.mean(np.array(features_baseline), axis=0)
print("\nRuhe-Kalibrierung abgeschlossen. Baseline gesetzt:", baseline)

# -------------------------------
# Trainingsphase
# -------------------------------
TRIALS_PER_HAND = 5
features = []
labels = []

print("\n=== TRAININGSPHASE ===")
print(f"Du machst {TRIALS_PER_HAND} Trials pro Hand.")
print(f"Vorstellung jeder Hand dauert {WINDOW_LENGTH} Sekunden.")

for hand_label, hand_name in [(0, "Linke Hand"), (1, "Rechte Hand")]:
    for trial in range(TRIALS_PER_HAND):
        print(f"\nTrial {trial+1}/{TRIALS_PER_HAND} – {hand_name} vorbereiten...")
        time.sleep(PAUSE_BETWEEN_TRIALS)
        print("Jetzt vorstellen!")

        buffer.clear()
        while len(buffer) < N_SAMPLES:
            line = ser.readline().decode('utf-8').strip()
            if not line:
                continue
            try:
                ch1_str, ch2_str = line.split(',')
                ch1 = int(ch1_str)
                ch2 = int(ch2_str)
                buffer.append([ch1, ch2])
            except ValueError:
                continue

        epoch = np.array(buffer, dtype=float)
        epoch = bandpass_filter(epoch, 8, 30, SAMPLE_RATE)
        bp = compute_bandpower(epoch)
        features.append(bp)
        labels.append(hand_label)
        buffer.clear()
        print(f"Trial {trial+1} abgeschlossen.")

features = np.array(features)
labels = np.array(labels)

# -------------------------------
# Klassifikator trainieren
# -------------------------------
clf = LinearDiscriminantAnalysis()
clf.fit(features, labels)
print("\nTrainingsphase abgeschlossen. Klassifikator bereit für Echtzeit-Vorhersage.")

# -------------------------------
# Echtzeit-Vorhersage
# -------------------------------
THRESHOLD = 0.6      # minimale Wahrscheinlichkeit
MIN_DIFF = 500.0     # minimale Differenz zur Ruhe-Baseline

print("\n=== ECHTZEIT-VORHERSAGE (ca. 60 Hz) ===")
print("Vorstellung linke oder rechte Hand. STRG+C zum Beenden.")

buffer.clear()
try:
    while True:
        line = ser.readline().decode('utf-8').strip()
        if not line:
            continue
        try:
            ch1_str, ch2_str = line.split(',')
            ch1 = int(ch1_str)
            ch2 = int(ch2_str)
            buffer.append([ch1, ch2])
        except ValueError:
            continue

        if len(buffer) == N_SAMPLES:
            epoch = np.array(buffer, dtype=float)
            epoch = bandpass_filter(epoch, 8, 30, SAMPLE_RATE)
            bp = compute_bandpower(epoch)

            # Prüfen gegen Ruhe-Baseline
            if np.max(np.abs(bp - baseline)) > MIN_DIFF:
                probs = clf.predict_proba(bp.reshape(1, -1))[0]
                max_prob = np.max(probs)
                pred = np.argmax(probs)
                if max_prob > THRESHOLD:
                    if pred == 0:
                        print("Vorhersage: Linke Hand")
                        ser.write(b"p>a:left\n")
                    else:
                        print("Vorhersage: Rechte Hand")
                        ser.write(b"p>a:right\n")
                # sonst keine Ausgabe
            else:
                print('Abweichung: ', np.max(np.abs(bp - baseline)))
                ser.write(b"p>a:stop\n")

            # Sliding Window: nur STEP_SIZE Samples verschieben
            for _ in range(STEP_SIZE):
                if buffer:
                    buffer.popleft()

# -------------------------------
# Stop des Programms durch STRG + C
# -------------------------------
except KeyboardInterrupt:
    ser.write(b"p>a:stop\n")
    ser.close()
    print("\nEchtzeit-Vorhersage beendet.")
