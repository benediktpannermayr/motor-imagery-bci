// Pins zum Abgreifen der EEG-Werte
const int ch1Pin = A0;
const int ch2Pin = A1;
const int ch3Pin = A2;
const int ch4Pin = A3;

// Pins zur Fahrzeugsteuerung
const int carReverse = 0;
const int carForward = 1;
const int carLeft = 2;
const int carRight = 3;

const int sampleRate = 250; // Abtastrate EEG in Hz
unsigned long tNext;

void setup() {
  Serial.begin(115200);
  tNext = micros();
}

void loop() {
  // --- Serielle Eingabe prüfen ---
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n'); // Auslesen einer Zeile der seriellen Schnittstelle
    line.trim(); // Leerzeichen und CR entfernen

    // Befehler verarbeiten
    if (line.startsWith("p>a:")) {
      if (line == "p>a:right") {
        changeButtonState(carForward, true);
        changeButtonState(carLeft, false);
        changeButtonState(carRight, true);
      } else if (line == "p>a:left") {
        changeButtonState(carForward, true);
        changeButtonState(carRight, false);
        changeButtonState(carLeft, true);
      } else if (line == "p>a:stop") {
        changeButtonState(carForward, false);
        changeButtonState(carRight, false);
        changeButtonState(carLeft, false);
      }
    }
  }

  // --- ADC Abtastung ---
  if (micros() >= tNext) {
    int ch1 = analogRead(ch1Pin);
    int ch2 = analogRead(ch2Pin);
    int ch3 = analogRead(ch3Pin);
    int ch4 = analogRead(ch4Pin);
    
    // Senden der Werte
    Serial.print(ch1);
    Serial.print(",");
    Serial.println(ch2);
    
    tNext += 1000000 / sampleRate; // Nächste Abtastzeit
  }
}

/*
Simulation eines Tasterdrucks an der Fernbedienung
pressed = true: Pin wird als Output (LOW) definiert. --> Pin ist nicht hochohmig und leitet eingehende Signale automatisch gegen Ground
pressed = false: Pin wird als Input definiert. --> Pin ist hochohmig und leitet daher keine Signale gegen Ground
*/
void changeButtonState(int signalPin, bool pressed) {
  if (pressed) {
    pinMode(signalPin, OUTPUT);
  } else {
    pinMode(signalPin, INPUT);
  }
}
