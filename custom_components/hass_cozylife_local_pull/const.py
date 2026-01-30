DOMAIN = "hass_cozylife_local_pull"

# http://doc.doit/project-5/doc-8/
SWITCH_TYPE_CODE = '00'
LIGHT_TYPE_CODE = '01'
ENERGY_STORAGE_TYPE_CODE = '02'
SUPPORT_DEVICE_CATEGORY = [SWITCH_TYPE_CODE, LIGHT_TYPE_CODE, ENERGY_STORAGE_TYPE_CODE]

# http://doc.doit/project-5/doc-8/
SWITCH = '1'
WORK_MODE = '2'
TEMP = '3'
BRIGHT = '4'
HUE = '5'
SAT = '6'

LIGHT_DPID = [SWITCH, WORK_MODE, TEMP, BRIGHT, HUE, SAT]
SWITCH_DPID = [SWITCH, ]

# Energy Storage DPIDs
# DPID 1 is a bitmask: bit 0 (1) = AC, bit 1 (2) = LED, bit 2 (4) = DC
ENERGY_CONTROL = '1'  # Bitmask for AC/LED/DC control
ENERGY_BATTERY_PERCENT = '3'  # Battery percentage (0-100)
ENERGY_OUTPUT_POWER = '4'  # Output power in Watts
ENERGY_TIME_REMAINING = '30'  # Time remaining in minutes until battery empty
ENERGY_INPUT_POWER = '32'  # Input power in Watts
ENERGY_LED_MODE = '33'  # LED mode control
ENERGY_MAX_OUTPUT = '40'  # Max output current/power (constant value)
ENERGY_CAPACITY = '41'  # Battery capacity in Wh (constant value)

# Bit masks for DPID 1
ENERGY_BIT_AC = 1  # Bit 0: AC output
ENERGY_BIT_LED = 2  # Bit 1: LED lamp
ENERGY_BIT_DC = 4  # Bit 2: DC 12V output

# LED Mode values for DPID 33
ENERGY_LED_MODE_LOW = 1  # Steady less bright (app shows as "Low")
ENERGY_LED_MODE_HIGH = 0  # Steady full bright (app shows as "High")
ENERGY_LED_MODE_SOS = 5  # SOS blinking pattern
ENERGY_LED_MODE_AUTO = 8  # Auto/standby (when LED is off)

LANG = 'en'
API_DOMAIN = 'api-us.doiting.com'