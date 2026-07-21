#include <EEPROM.h>
#include <assert.h>

#include "SerialCommands.h"
#include "Reset.h"

//if these are needed is TBD 12/29/21

const int USAGE_DUT_INPUT = 0x01;
const int USAGE_FILTER_BYPASS = 0x02;
const int USAGE_AWG_CONNECTION = 0x04;
const int USAGE_LONG_SHORT_CABLE = 0x08;
const int USAGE_LONG_SHORT_RETURN = 0x10;
const int USAGE_19M_CABLE = 0x20;
const int USAGE_19M_RETURN = 0x40;
const int USAGE_POLARITY_FLIP = 0x80;
const int USAGE_PIN_INVERTED_FLAG = 0x06;

const int USAGE_FLAG_COUNT = 9;

const char *DESC_USAGE_FLAG[] = {
  "DUT input selection",
  "LP filter bypass",
  "AWG connection to scope or noise injection",
  "signal to long or short cable",
  "signal from long or short cable",
  "signal to 19m cable",
  "signal from 19m cable",
  "link polarity flip",
};


// This is used to store desired start-up states in non-volatile memory
// and to know pin functionality.
struct pin_config_t {
  unsigned char inout;
  unsigned char value;
  unsigned char usage_flags;
};


const int FIRMWARE_VERSION_MAJOR = 0;
const int FIRMWARE_VERSION_MINOR = 1;
const int FIRMWARE_VERSION_REV = 0;

///////////////////////////////////////////////////////////////////////////////
// target board ///////////////////////////////////////////////////////////////
///////////////////////////////////////////////////////////////////////////////

// THIS MUST BE UPDATED TO REFLECT THE BOARD + HW REV YOU ARE INSTALLING ON
#define BOARD BOARD_TYPE_EVERY_REV_3_0

///////////////////////////////////////////////////////////////////////////////
// board pinout defines. add new pinouts here when adding support for new /////
// board / hw revs. ///////////////////////////////////////////////////////////
///////////////////////////////////////////////////////////////////////////////

#ifndef BOARD
#error BOARD must be set to the target hardware config
#endif

#if BOARD == BOARD_TYPE_EVERY_REV_3_0
#define PIN_COUNT 22
const pin_config_t DEFAULT_PINS[PIN_COUNT] = {
  /*  0 */ { INPUT, LOW, 0 },
  /*  1 */ { INPUT, LOW, 0 },
  /*  2 */ { OUTPUT, HIGH, 0 },
  /*  3 */ { OUTPUT, HIGH, 0 },
  /*  4 */ { OUTPUT, LOW, 0 },
  /*  5 */ { OUTPUT, LOW, 0 },
  /*  6 */ { OUTPUT, LOW, 0 },
  /*  7 */ { OUTPUT, LOW, 0 },
  /*  8 */ { OUTPUT, LOW, 0 },
  /*  9 */ { OUTPUT, LOW, 0 },
  /* 10 */ { INPUT, LOW, 0 },
  /* 11 */ { INPUT, LOW, 0 },
  /* 12 */ { INPUT, LOW, 0 },
  /* 13 */ { INPUT, LOW, 0 },
  /* 14 */ { INPUT, LOW, 0 },
  /* 15 */ { INPUT, LOW, 0 },
  /* 16 */ { INPUT, LOW, 0 },
  /* 17 */ { INPUT, LOW, 0 },
  /* 18 */ { INPUT, LOW, 0 },
  /* 19 */ { INPUT, LOW, 0 },
  /* 20 */ { INPUT, LOW, 0 },
  /* 21 */ { INPUT, LOW, 0 },
};
#endif /* BOARD == BOARD_TYPE_EVERY_REV_3_0 */

// FIXME: this could be avoided by using locals where needed.
pin_config_t active[PIN_COUNT];

///////////////////////////////////////////////////////////////////////////////
// more things that need to come later ////////////////////////////////////////
///////////////////////////////////////////////////////////////////////////////

// The size of the EEPROM on Every Nanos is 256 bytes!
// Really this should check based on which board is actually being targeted...
static_assert(sizeof(DEFAULT_PINS) <= 256, "pin data too large to fit in EEPROM");

#define STRINGIFICATION(to_str) "" #to_str

///////////////////////////////////////////////////////////////////////////////
// nv mem interaction / pin convienience //////////////////////////////////////
///////////////////////////////////////////////////////////////////////////////

const int NV_MEM_MAGIC = 0x1234;

bool has_saved_config() {
  int magic;
  EEPROM.get(0, magic);
  return magic == NV_MEM_MAGIC;
}

void set_pins(int pin_count, pin_config_t *pinconfig) {
  for (int i = 0; i < pin_count; ++i) {
    digitalRead(i);  // set the pin to digital // FIXME: is there a real way?
    pinMode(i, pinconfig[i].inout);

    if (pinconfig[i].inout == OUTPUT)
      write_pin(i, pinconfig[i].value, pinconfig);
  }
}

void read_saved_pinconfig(int pin_count, pin_config_t *pinconfig) {
  int magic;
  EEPROM.get(0, magic);
  if (magic != NV_MEM_MAGIC) {
    save_pinconfig(PIN_COUNT, DEFAULT_PINS);
    read_saved_pinconfig(pin_count, pinconfig);
    return;
  }

  for (int i = 0; i < pin_count; ++i) {
    EEPROM.get(sizeof(magic) + i * sizeof(pinconfig[0]), pinconfig[i]);
  }
}

void save_pinconfig(int pin_count, const pin_config_t *pinconfig) {
  EEPROM.put(0, NV_MEM_MAGIC);

  for (int i = 0; i < pin_count; ++i) {
    EEPROM.put(i * sizeof(*pinconfig) + sizeof(NV_MEM_MAGIC), pinconfig[i]);
  }
}

void write_pin(int pin, int value, const pin_config_t *pinconfig) {
  //    if(pinconfig[pin].usage_flags & USAGE_PIN_INVERTED_FLAG)
  //        value = !value;

  digitalWrite(pin, value);
}

///////////////////////////////////////////////////////////////////////////////
// commands ///////////////////////////////////////////////////////////////////
///////////////////////////////////////////////////////////////////////////////

// const char *help_text = "Help text is too large for UNOs\n";
// /*
const char *help_text =
  "This arudino responds to newline-terminated commands.\n"
  "Please use a single space between command/options\n"
  "\n"
  "Commands: \n"
  "    set-pin <pin> <value>\n"
  "           Set pin <pin> to value <value>. <value> may be 0 or 1\n"
  "           For general startup testing, this should NOT be used, instead, use\n"
  "           the power-on-dut / power-off-dut commands\n"
  "           Pin <pin> will automatically be configured as digital output.\n"
  "    set-pin-default <pin> <mode> [value]\n"
  "           Set the default mode and value of pin <pin> to <mode> and <value>.\n"
  "           <mode> may be IN or OUT. <value> may be 0 or 1, only specified when\n"
  "           <mode> is OUT. When the arduino powers on, the pin configued to these\n"
  "           settings.\n"
  "           This is useful if you are trying to configure the default state of\n"
  "           the DUT on board power on.\n"
  "    read-pin <pin>\n"
  "           A digital read is performed on pin <pin>. The output\n"
  "                   value 0             --or--\n"
  "                   value 1\n"
  "           is written to the serial, followed by a newline.\n"
  "           Pin <pin> will automatically be configured as digital input.\n"
  "    version\n"
  "           Prints the firmware version, board type, and hardware version.\n"
  "           For example:\n"
  "                   firmware: 0.1\n"
  "                   board: uno with rev 1 board\n"
  "    reset\n"
  "           Resets the power-on pin states to default, then resets board.\n"
  "    pin-info\n"
  "           Prints info about pins, their power-on states, and their usage.\n"
  "    set-inverted <pin> (yes|no)\n"
  "           Marks this pin as needs to be inverted or not. If so, any time a\n"
  "           value is written to this pin, it will be inverted.\n"
  "           This allows for controlling active high and active low signaling.\n"
  "           This information is saved to the non-volatile storage for use.\n"
  "           on device start.\n"
  "   scope\n"
  "           Configures the board to connect the DUT to the scope and nothing else.\n"
  "   slave-jitter\n"
  "           Configuration for testing 100Base slave jitter.\n"
  "   distortion\n"
  "           Configuration for distortion test\n"
  "   rx-short\n"
  "           Connects the DUT to the link partner through the short cable port.\n"
  "   rx-long\n"
  "           Connects the DUT to the link partner through the long cable port.\n"
  "   rx-noise\n"
  "           Connects the DUT to the link partner through the 19m and short cable port\n"
  "           as well as connecing the AWG port to the signal path with the resistive\n"
  "           injection network.\n"
  "\n"
  "The arduino can be interfaced with in linux by doing the following:\n"
  "(replace /dev/ttyACM0 with the correct device, found via `dmesg`)\n"
  "  `stty -F /dev/ttyACM0 cs8 115200 ignbrk -brkint -icrnl -imaxbel\n"
  "       -opost -onlcr -isig -icanon -iexten -echo -echoe -echok\n"
  "       -echoctl -echoke noflsh -ixon -crtscts`\n"
  "Then reading from serial in a terminal is:"
  "  `tail -f /dev/ttyACM0`\n"
  "\n"
  "Your user must be in the tty (and maybe dialout) group(s).\n";
// */

void help(SerialCommands *sender) {
  sender->GetSerial()->print(help_text);
}
SerialCommand cmd_set_pin("help", help);

int get_int_arg(SerialCommands *sender, const char *caller, const char *argname) {
  char *str = sender->Next();
  if (!str) {
    // user didn't pass argument
    sender->GetSerial()->print(caller);
    sender->GetSerial()->print(": no ");
    sender->GetSerial()->print(argname);
    sender->GetSerial()->print("pin specified\n");
    return -1;
  }
  return atoi(str);
}

char *get_str_arg(SerialCommands *sender, const char *caller, const char *argname) {
  char *str = sender->Next();
  if (!str) {
    // user didn't pass argument
    sender->GetSerial()->print(caller);
    sender->GetSerial()->print(": no ");
    sender->GetSerial()->print(argname);
    sender->GetSerial()->print("pin specified\n");
    return nullptr;
  }
  return str;
}

void reset(SerialCommands *sender) {
  save_pinconfig(PIN_COUNT, DEFAULT_PINS);
  soft_reset();
}
SerialCommand cmd_reset("reset", reset);

void set_pin(SerialCommands *sender) {
  int pin = get_int_arg(sender, "set-pin", "pin");
  if (pin < 0)
    return;

  int value = get_int_arg(sender, "set-pin", "value");
  if (value < 0)
    return;

  if (pin >= PIN_COUNT) {
    sender->GetSerial()->print("Pin index too high\n");
    return;
  }

  sender->GetSerial()->print("Setting pin ");
  sender->GetSerial()->print(pin);
  sender->GetSerial()->print(" ");
  sender->GetSerial()->print(value ? "high" : "low");
  sender->GetSerial()->print("\n");

  write_pin(pin, value, active);
}
SerialCommand cmd_help("set-pin", set_pin);

void set_pin_default(SerialCommands *sender) {
  int pin = get_int_arg(sender, "set-pin-default", "pin");
  char *mode_str = get_str_arg(sender, "set-pin-default", "mode");

  if (pin >= PIN_COUNT) {
    sender->GetSerial()->print("Pin index too high\n");
    return;
  }

  // convert string to lowercase
  for (char *tmp = mode_str; *tmp != '\0'; tmp++)
    *tmp = tolower(*tmp);

  if (strcmp(mode_str, "in") == 0) {
    active[pin].inout = INPUT;
  } else if (strcmp(mode_str, "out") == 0) {
    int value = get_int_arg(sender, "set-pin-default", "value");
    if (value < 0)
      return;

    active[pin].inout = OUTPUT;
    active[pin].value = value;
  } else {
    sender->GetSerial()->print("set-pin-default: unrecognized mode specified. Must be IN or OUT.\n");
    return;
  }

  save_pinconfig(PIN_COUNT, active);
}
SerialCommand cmd_set_pin_default("set-pin-default", set_pin_default);

void set_inverted(SerialCommands *sender) {
  int pin = get_int_arg(sender, "set-inverted", "pin");
  char *mode_str = get_str_arg(sender, "set-inverted", "inverted");

  if (pin >= PIN_COUNT) {
    sender->GetSerial()->print("Pin index too high\n");
    return;
  }

  // convert string to lowercase
  for (char *tmp = mode_str; *tmp != '\0'; tmp++)
    *tmp = tolower(*tmp);

  if (strcmp(mode_str, "yes") == 0) {
    active[pin].usage_flags |= USAGE_PIN_INVERTED_FLAG;
    sender->GetSerial()->print("set-inverted: inverted pin ");
    sender->GetSerial()->print(pin);
    sender->GetSerial()->print("\n");
  } else if (strcmp(mode_str, "no") == 0) {
    active[pin].usage_flags &= ~USAGE_PIN_INVERTED_FLAG;
    sender->GetSerial()->print("set-inverted: un-inverted pin ");
    sender->GetSerial()->print(pin);
    sender->GetSerial()->print("\n");
  } else {
    sender->GetSerial()->print("set-inverted: unrecognized mode specified. Must be YES or NO.\n");
    return;
  }

  write_pin(pin, active[pin].value, active);

  save_pinconfig(PIN_COUNT, active);
}
SerialCommand cmd_set_inverted("set-inverted", set_inverted);

void read_pin(SerialCommands *sender) {
  int pin = get_int_arg(sender, "read-pin", "pin");

  if (pin >= PIN_COUNT) {
    sender->GetSerial()->print("Pin index too high\n");
    return;
  }

  sender->GetSerial()->print("value ");
  sender->GetSerial()->print(digitalRead(pin));
  sender->GetSerial()->print("\n");
}
SerialCommand cmd_read_pin("read-pin", read_pin);

void version(SerialCommands *sender) {
  sender->GetSerial()->print("firmware: ");
  sender->GetSerial()->print(FIRMWARE_VERSION_MAJOR);
  sender->GetSerial()->print(".");
  sender->GetSerial()->print(FIRMWARE_VERSION_MINOR);
  sender->GetSerial()->print(".");
  sender->GetSerial()->print(FIRMWARE_VERSION_REV);
  sender->GetSerial()->print("\n");

  sender->GetSerial()->print("board: ");
  sender->GetSerial()->print("\n");
}
SerialCommand cmd_version("version", version);

void pin_info(SerialCommands *sender) {
  for (int i = 0; i < PIN_COUNT; ++i) {
    sender->GetSerial()->print(i);
    sender->GetSerial()->print(": ");

    if (active[i].inout == INPUT) {
      sender->GetSerial()->print("IN ");
    } else {
      sender->GetSerial()->print("OUT ");
    }

    sender->GetSerial()->print(active[i].value);

    sender->GetSerial()->print(": ");

    for (int flag_index = 0; flag_index < USAGE_FLAG_COUNT; ++flag_index) {
      if (active[i].usage_flags & (1 << flag_index)) {
        sender->GetSerial()->print(DESC_USAGE_FLAG[flag_index]);
        sender->GetSerial()->print(", ");
      }
    }

    sender->GetSerial()->print("\n");
  }
}
SerialCommand cmd_pin_info("pin-info", pin_info);

void scope(SerialCommands *sender) {
  write_pin(2, 1, active);
  write_pin(3, 0, active);
  write_pin(4, 0, active);
  sender->GetSerial()->print("Scope Connection Mode\n");
}
SerialCommand cmd_scope("scope", scope);

void slave_jitter(SerialCommands *sender) {
  write_pin(2, 0, active);
  write_pin(4, 1, active);
  sender->GetSerial()->print("Slave Jitter Mode\n");
}
SerialCommand cmd_s_jitter("slave-jitter", slave_jitter);

void distortion(SerialCommands *sender) {
  write_pin(2, 1, active);
  write_pin(3, 1, active);
  write_pin(4, 1, active);
  sender->GetSerial()->print("Distortion Mode\n");
}
SerialCommand cmd_distortion("distortion", distortion);

void rx_short(SerialCommands *sender) {
  write_pin(2, 0, active);
  write_pin(4, 0, active);
  write_pin(5, 0, active);
  write_pin(6, 0, active);
  write_pin(7, 0, active);
  write_pin(8, 1, active);
  write_pin(9, 1, active);
  sender->GetSerial()->print("Reciever Short Cable Mode\n");
}
SerialCommand cmd_rx_short("rx-short", rx_short);

void rx_long(SerialCommands *sender) {
  write_pin(2, 0, active);
  write_pin(4, 0, active);
  write_pin(5, 1, active);
  write_pin(6, 1, active);
  write_pin(7, 0, active);
  write_pin(8, 1, active);
  write_pin(9, 1, active);
  sender->GetSerial()->print("Reciever Long Cable Mode\n");
}
SerialCommand cmd_rx_long("rx-long", rx_long);

void rx_noise(SerialCommands *sender) {
  write_pin(2, 0, active);
  write_pin(4, 0, active);
  write_pin(5, 0, active);
  write_pin(6, 0, active);
  write_pin(7, 1, active);
  write_pin(8, 0, active);
  write_pin(9, 1, active);
  sender->GetSerial()->print("Reciever Noise Injection Mode\n");
}
SerialCommand cmd_rx_noise("rx-noise", rx_noise);
// FIXME: power on verification

///////////////////////////////////////////////////////////////////////////////
///////////////////////////////////////////////////////////////////////////////
///////////////////////////////////////////////////////////////////////////////

void unknown_command(SerialCommands *sender, const char *cmd) {
  sender->GetSerial()->print("Unknown command\n");
}

///////////////////////////////////////////////////////////////////////////////
// serial interaction /////////////////////////////////////////////////////////
///////////////////////////////////////////////////////////////////////////////

const int buffer_size = 64;
char command_buffer[buffer_size];
SerialCommands serial_commands(&Serial, command_buffer, buffer_size, "\n");

void setup() {
  read_saved_pinconfig(PIN_COUNT, active);
  set_pins(PIN_COUNT, active);

  serial_commands.AddCommand(&cmd_help);
  serial_commands.AddCommand(&cmd_reset);
  serial_commands.AddCommand(&cmd_set_pin);
  serial_commands.AddCommand(&cmd_set_pin_default);
  serial_commands.AddCommand(&cmd_set_inverted);
  serial_commands.AddCommand(&cmd_read_pin);
  serial_commands.AddCommand(&cmd_version);
  serial_commands.AddCommand(&cmd_pin_info);
  serial_commands.AddCommand(&cmd_scope);
  serial_commands.AddCommand(&cmd_s_jitter);
  serial_commands.AddCommand(&cmd_distortion);
  serial_commands.AddCommand(&cmd_rx_short);
  serial_commands.AddCommand(&cmd_rx_long);
  serial_commands.AddCommand(&cmd_rx_noise);

  serial_commands.SetDefaultHandler(&unknown_command);

  Serial.begin(115200);
  while (!Serial) {
    // apparently this is needed (or at least good practice)
    // for the native use port. Seen in Arduino example code
  }
}

void loop() {
  serial_commands.ReadSerial();
}
