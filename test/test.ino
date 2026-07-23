int relays[] = {8,9,10};
const int DT_RELAY = relays[0];
const int ST_RELAY = relays[1];
const int POL_RELAY = relays[2];

// How many relays are in the array
const int NUM_RELAYS = sizeof(relays) / sizeof(relays[0]);

void setup()
{
  for (int i = 0; i < NUM_RELAYS; i++)
  {
  pinMode(relays[i], OUTPUT);
  //start all relays off
  digitalWrite(relays[i], LOW);
  }


  Serial.begin(9600);

  all_off();

  Serial.println("Enter a command:");
  Serial.println("1 = Normal Mode");
  Serial.println("2 = Alternate Mode");
  Serial.println("3 = Polarity Mode");
  Serial.println("0 = All Off");
}


void normal_mode()
{
  all_off();
  digitalWrite(relays[0], HIGH);

}

void alternate_mode()
{
  all_off();

  digitalWrite(ST_RELAY, HIGH);

}

void polarity_mode()
{
  all_off(); 
  digitalWrite(DT_RELAY, HIGH);
  digitalWrite(POL_RELAY, HIGH);
}
 
void all_off()
{
    for (int i = 0; i < NUM_RELAYS; i++)
    {
        digitalWrite(relays[i], LOW);
    }
}

void blink_mode()
{
  for(int i = 0; i < 5; i++)
  {
  for (int i = 0; i < NUM_RELAYS; i++)
      {
          digitalWrite(relays[i], HIGH);
      }
      delay(500);

    all_off();
    delay(500);
  }
  
}

void loop()
{
  if (Serial.available() > 0)
  {
    char command = Serial.read();

    if (command == '1')
    {
      normal_mode();
      Serial.println("Normal mode selected");
    }
    else if (command == '2')
    {
      alternate_mode();
      Serial.println("Alternate mode selected");
    }
    else if (command == '3')
    {
      polarity_mode();
      Serial.println("Polarity mode selected");
    }
    else if (command == '0')
    {
      all_off();
      Serial.println("All outputs off");
    }
    else if (command == 't')
    {
      normal_mode();
      delay (1000);

      alternate_mode();
      delay (1000);

      polarity_mode();
      delay (1000);

      all_off();
      delay (1000);
      Serial.println("Test complete.");
    }

    else if (command == 'b')
    {
        blink_mode();
        Serial.println("Blink mode selected.");
    }
    
  }
}