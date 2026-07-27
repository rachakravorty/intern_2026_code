/*

Automotive Ethernet Test Fixture Controller
MCU: Arduino
Purpose:
    Controls relay PCB for OPEN Alliance
    interoperability testing.

Commands from Python

NORMAL
POLARITY
OPEN
SHORT
DT
RESET_DUT
RESET_LP
ALL_OFF
STATUS


*/

// ---------- Relay Pins ----------

// Update according to the different pins

const int ST1 = 2;
const int ST2 = 3;
const int ST3 = 4;
const int ST4 = 5;

const int DT  = 6;
const int DT1 = 7;
const int DT2 = 8;

const int DUT_RESET = 9;
const int LP_RESET  = 10;

String command = "";

void setup()
{
    pinMode(ST1, OUTPUT);
    pinMode(ST2, OUTPUT);
    pinMode(ST3, OUTPUT);
    pinMode(ST4, OUTPUT);

    pinMode(DT, OUTPUT);
    pinMode(DT1, OUTPUT);
    pinMode(DT2, OUTPUT);

    pinMode(DUT_RESET, OUTPUT);
    pinMode(LP_RESET, OUTPUT);

    Serial.begin(115200);

    allOff();

    Serial.println("READY");
}

void loop()
{
    if (Serial.available())
    {
        command = Serial.readStringUntil('\n');
        command.trim();

        if(command == "NORMAL")
            normalMode();

        else if(command == "POLARITY")
            polarityMode();

        else if(command == "OPEN")
            openCircuit();

        else if(command == "SHORT")
            shortCircuit();

        else if(command == "DT")
            dtMode();

        else if(command == "RESET_DUT")
            resetDUT();

        else if(command == "RESET_LP")
            resetLinkPartner();

        else if(command == "ALL_OFF")
            allOff();

        else if(command == "STATUS")
            sendStatus();
    }
}

void allOff()
{
    digitalWrite(ST1,LOW);
    digitalWrite(ST2,LOW);
    digitalWrite(ST3,LOW);
    digitalWrite(ST4,LOW);

    digitalWrite(DT,LOW);
    digitalWrite(DT1,LOW);
    digitalWrite(DT2,LOW);
}

void normalMode()
{
    allOff();

    Serial.println("NORMAL");
}

void polarityMode()
{
    allOff();

    digitalWrite(DT1,HIGH);
    digitalWrite(DT2,HIGH);

    Serial.println("POLARITY");
}

void openCircuit()
{
    allOff();

    digitalWrite(ST3,HIGH);
    digitalWrite(ST4,HIGH);

    Serial.println("OPEN");
}

void shortCircuit()
{
    allOff();

    digitalWrite(ST1,HIGH);
    digitalWrite(ST2,HIGH);

    Serial.println("SHORT");
}

void dtMode()
{
    allOff();

    digitalWrite(DT,HIGH);

    Serial.println("DT");
}

void resetDUT()
{
    digitalWrite(DUT_RESET,LOW);
    delay(10);
    digitalWrite(DUT_RESET,HIGH);

    Serial.println("DUT RESET");
}

void resetLinkPartner()
{
    digitalWrite(LP_RESET,LOW);
    delay(10);
    digitalWrite(LP_RESET,HIGH);

    Serial.println("LP RESET");
}

void sendStatus()
{
    Serial.print("{");

    Serial.print("\"ST1\":");
    Serial.print(digitalRead(ST1));

    Serial.print(",\"ST2\":");
    Serial.print(digitalRead(ST2));

    Serial.print(",\"ST3\":");
    Serial.print(digitalRead(ST3));

    Serial.print(",\"ST4\":");
    Serial.print(digitalRead(ST4));

    Serial.print(",\"DT\":");
    Serial.print(digitalRead(DT));

    Serial.print(",\"DT1\":");
    Serial.print(digitalRead(DT1));

    Serial.print(",\"DT2\":");
    Serial.print(digitalRead(DT2));

    Serial.println("}");
}
