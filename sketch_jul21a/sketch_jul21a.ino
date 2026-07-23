#include <EEPROM.h>
#include <assert.h>
#include <avr/wdt.h>

#include "SerialCommands.h"

///////////////////////////////////////////////////////////////////////////////
// Usage Flags for Automotive Ethernet Fault Fixture
///////////////////////////////////////////////////////////////////////////////

const int USAGE_POLARITY_SWAP = 0x01; // Relays DT1 & DT2
const int USAGE_FAULT_OPEN    = 0x02; // Relays ST3 & ST4
const int USAGE_FAULT_SHORT   = 0x04; // Relays ST1 & ST2
const int USAGE_DT_ROUTING    = 0x08; // Relay DT
const int USAGE_PIN_INVERTED  = 0x10; // Inversion flag

const int USAGE_FLAG_COUNT = 5;

const char *DESC_USAGE_FLAG[] = {
    "Polarity Swap (DT1/DT2)",
    "Open Circuit Fault (ST3/ST4)",
    "Short Circuit Fault (ST1/ST2)",
    "Mode Routing (DT)",
    "Pin Inverted"
};

// Configuration structure saved to EEPROM
struct pin_config_t {
    unsigned char inout;
    unsigned char value;
    unsigned char usage_flags;
};

const int FIRMWARE_VERSION_MAJOR = 1;
const int FIRMWARE_VERSION_MINOR = 1;
const int FIRMWARE_VERSION_REV   = 0;

#define PIN_COUNT 22

const pin_config_t DEFAULT_PINS[PIN_COUNT] = {
    /*  0 RX */ { INPUT,  LOW,  0 },
    /*  1 TX */ { INPUT,  LOW,  0 },
    /*  2 D2 */ { OUTPUT, LOW,  USAGE_FAULT_SHORT },   // ST1
    /*  3 D3 */ { OUTPUT, LOW,  USAGE_FAULT_SHORT },   // ST2
    /*  4 D4 */ { OUTPUT, LOW,  USAGE_FAULT_OPEN },    // ST3
    /*  5 D5 */ { OUTPUT, LOW,  USAGE_FAULT_OPEN },    // ST4
    /*  6 D6 */ { OUTPUT, LOW,  USAGE_DT_ROUTING },    // DT
    /*  7 D7 */ { OUTPUT, LOW,  USAGE_POLARITY_SWAP }, // DT1
    /*  8 D8 */ { OUTPUT, LOW,  USAGE_POLARITY_SWAP }, // DT2 / ST1 mirror
    /*  9 D9 */ { OUTPUT, LOW,  0 },
    /* 10 D10*/ { OUTPUT, LOW,  0 },
    /* 11 D11*/ { INPUT,  LOW,  0 },
    /* 12 D12*/ { INPUT,  LOW,  0 },
    /* 13 D13*/ { INPUT,  LOW,  0 },
    /* 14 A0 */ { INPUT,  LOW,  0 },
    /* 15 A1 */ { INPUT,  LOW,  0 },
    /* 16 A2 */ { INPUT,  LOW,  0 },
    /* 17 A3 */ { INPUT,  LOW,  0 },
    /* 18 A4 */ { INPUT,  LOW,  0 },
    /* 19 A5 */ { INPUT,  LOW,  0 },
    /* 20 A6 */ { INPUT,  LOW,  0 },
    /* 21 A7 */ { INPUT,  LOW,  0 },
};

pin_config_t active[PIN_COUNT];

static_assert(sizeof(DEFAULT_PINS) <= 256, "Pin configuration array exceeds EEPROM limits");

const int NV_MEM_MAGIC = 0x10A1;

void soft_reset() {
    wdt_enable(WDTO_15MS);
    while (1) {}
}

void write_pin(int pin, int value, const pin_config_t *pinconfig) {
    if (pinconfig[pin].usage_flags & USAGE_PIN_INVERTED) {
        value = !value;
    }
    digitalWrite(pin, value);
}

void set_pins(int pin_count, pin_config_t *pinconfig) {
    for (int i = 0; i < pin_count; ++i) {
        pinMode(i, pinconfig[i].inout);
        if (pinconfig[i].inout == OUTPUT) {
            write_pin(i, pinconfig[i].value, pinconfig);
        }
    }
}

void sync_aux_outputs() {
    digitalWrite(8, active[2].value);
    digitalWrite(9, active[3].value);
    digitalWrite(10, active[4].value);
}

void save_pinconfig(int pin_count, const pin_config_t *pinconfig) {
    EEPROM.put(0, NV_MEM_MAGIC);
    for (int i = 0; i < pin_count; ++i) {
        EEPROM.put(sizeof(NV_MEM_MAGIC) + (i * sizeof(pin_config_t)), pinconfig[i]);
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
        EEPROM.get(sizeof(magic) + (i * sizeof(pin_config_t)), pinconfig[i]);
    }
}

int get_int_arg(SerialCommands *sender, const char *caller, const char *argname) {
    char *str = sender->Next();
    if (!str) {
        sender->GetSerial()->print("{\"error\":\"missing_arg\",\"arg\":\"");
        sender->GetSerial()->print(argname);
        sender->GetSerial()->println("\"}");
        return -1;
    }
    return atoi(str);
}

// Print full board state as JSON for Python GUI parsing
void send_json_status(Stream *serial) {
    serial->print("{\"ST1\":");  serial->print(active[2].value);
    serial->print(",\"ST2\":"); serial->print(active[3].value);
    serial->print(",\"ST3\":"); serial->print(active[4].value);
    serial->print(",\"ST4\":"); serial->print(active[5].value);
    serial->print(",\"DT\":");  serial->print(active[6].value);
    serial->print(",\"DT1\":"); serial->print(active[7].value);
    serial->print(",\"DT2\":"); serial->print(active[8].value);
    serial->println("}");
}


void cmd_get_status_handler(SerialCommands *sender) {
    send_json_status(sender->GetSerial());
}
SerialCommand cmd_status("status", cmd_get_status_handler);

void cmd_set_config_handler(SerialCommands *sender) {
    char *config_text = sender->Next();
    if (!config_text) {
        sender->GetSerial()->println("{\"error\":\"missing_config\"}");
        return;
    }

    if (strlen(config_text) != 7) {
        sender->GetSerial()->println("{\"error\":\"invalid_config\"}");
        return;
    }

    int pins[7] = {2, 3, 4, 5, 6, 7, 8};
    for (int i = 0; i < 7; ++i) {
        if (config_text[i] != '0' && config_text[i] != '1') {
            sender->GetSerial()->println("{\"error\":\"invalid_config\"}");
            return;
        }

        int value = (config_text[i] == '1') ? HIGH : LOW;
        active[pins[i]].value = value;
        write_pin(pins[i], value, active);
    }

    sync_aux_outputs();
    send_json_status(sender->GetSerial());
}
SerialCommand cmd_set_config("set-config", cmd_set_config_handler);

void help(SerialCommands *sender) {
    sender->GetSerial()->println("Commands: normal, swap-polarity, fault-open, fault-short, set-routing <0|1>, status, set-config <binary>, set-pin <p> <v>, read-pin <p>, reset, version");
}
SerialCommand cmd_help("help", help);

void version(SerialCommands *sender) {
    sender->GetSerial()->print("{\"fw\":\"");
    sender->GetSerial()->print(FIRMWARE_VERSION_MAJOR);
    sender->GetSerial()->print(".");
    sender->GetSerial()->print(FIRMWARE_VERSION_MINOR);
    sender->GetSerial()->println("\"}");
}
SerialCommand cmd_version("version", version);

void reset_cmd(SerialCommands *sender) {
    save_pinconfig(PIN_COUNT, DEFAULT_PINS);
    sender->GetSerial()->println("{\"status\":\"resetting\"}");
    soft_reset();
}
SerialCommand cmd_reset("reset", reset_cmd);

void set_pin(SerialCommands *sender) {
    int pin = get_int_arg(sender, "set-pin", "pin");
    if (pin < 0 || pin >= PIN_COUNT) return;

    int value = get_int_arg(sender, "set-pin", "value");
    if (value < 0) return;

    active[pin].inout = OUTPUT;
    active[pin].value = value;
    write_pin(pin, value, active);

    if (pin == 2 || pin == 3 || pin == 4) {
        sync_aux_outputs();
    }

    send_json_status(sender->GetSerial());
}
SerialCommand cmd_set_pin("set-pin", set_pin);

void read_pin(SerialCommands *sender) {
    int pin = get_int_arg(sender, "read-pin", "pin");
    if (pin < 0 || pin >= PIN_COUNT) return;

    sender->GetSerial()->print("{\"pin\":");
    sender->GetSerial()->print(pin);
    sender->GetSerial()->print(",\"val\":");
    sender->GetSerial()->print(digitalRead(pin));
    sender->GetSerial()->println("}");
}
SerialCommand cmd_read_pin("read-pin", read_pin);

// Mode: Passthrough (All relays LOW)
void mode_normal(SerialCommands *sender) {
    for (int p = 2; p <= 8; ++p) {
        active[p].value = LOW;
        write_pin(p, LOW, active);
    }
    sync_aux_outputs();
    send_json_status(sender->GetSerial());
}
SerialCommand cmd_normal("normal", mode_normal);

// Mode: Polarity Swapped (DT1 & DT2 HIGH)
void mode_polarity_swap(SerialCommands *sender) {
    active[7].value = HIGH;
    active[8].value = HIGH;
    write_pin(7, HIGH, active);
    write_pin(8, HIGH, active);
    send_json_status(sender->GetSerial());
}
SerialCommand cmd_polarity("swap-polarity", mode_polarity_swap);

// Mode: Open Circuit Fault (ST3 & ST4 HIGH)
void mode_fault_open(SerialCommands *sender) {
    active[4].value = HIGH;
    active[5].value = HIGH;
    write_pin(4, HIGH, active);
    write_pin(5, HIGH, active);
    sync_aux_outputs();
    send_json_status(sender->GetSerial());
}
SerialCommand cmd_fault_open("fault-open", mode_fault_open);

// Mode: Short Circuit Fault (ST1 & ST2 HIGH)
void mode_fault_short(SerialCommands *sender) {
    active[2].value = HIGH;
    active[3].value = HIGH;
    write_pin(2, HIGH, active);
    write_pin(3, HIGH, active);
    sync_aux_outputs();
    send_json_status(sender->GetSerial());
}
SerialCommand cmd_fault_short("fault-short", mode_fault_short);

// Mode: Routing Control (DT Relay)
void mode_routing(SerialCommands *sender) {
    int val = get_int_arg(sender, "set-routing", "state");
    if (val < 0) return;

    active[6].value = val ? HIGH : LOW;
    write_pin(6, active[6].value, active);
    send_json_status(sender->GetSerial());
}
SerialCommand cmd_routing("set-routing", mode_routing);

void unknown_command(SerialCommands *sender, const char *cmd) {
    sender->GetSerial()->println("{\"error\":\"unknown_command\"}");
}

const int BUFFER_SIZE = 64;
char command_buffer[BUFFER_SIZE];
SerialCommands serial_commands(&Serial, command_buffer, BUFFER_SIZE, "\n");

void setup() {
    read_saved_pinconfig(PIN_COUNT, active);
    set_pins(PIN_COUNT, active);
    sync_aux_outputs();

    serial_commands.AddCommand(&cmd_help);
    serial_commands.AddCommand(&cmd_version);
    serial_commands.AddCommand(&cmd_reset);
    serial_commands.AddCommand(&cmd_set_pin);
    serial_commands.AddCommand(&cmd_read_pin);
    serial_commands.AddCommand(&cmd_status);
    serial_commands.AddCommand(&cmd_set_config);
    serial_commands.AddCommand(&cmd_normal);
    serial_commands.AddCommand(&cmd_polarity);
    serial_commands.AddCommand(&cmd_fault_open);
    serial_commands.AddCommand(&cmd_fault_short);
    serial_commands.AddCommand(&cmd_routing);

    serial_commands.SetDefaultHandler(&unknown_command);

    Serial.begin(115200);
    while (!Serial) {}
}

void loop() {
    serial_commands.ReadSerial();
}