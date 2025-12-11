import smbus2
import struct

__version__ = "1.0.1"
_CARD_BASE_ADDRESS = 0x16
_STACK_LEVEL_MAX = 7
_IN_CH_COUNT = 8
_THERMISTOR_CH_COUNT = 8  # On-board thermistor channels
_TEMP_SIZE_BYTES = 2
_TEMP_SCALE_FACTOR = 10.0

_TCP_VAL1_ADD = 0
_TCP_TYPE1_ADD = 16
_REVISION_HW_MAJOR_MEM_ADD = 50
_REVISION_HW_MINOR_MEM_ADD = 51
_DIAG_TEMPERATURE_MEM_ADD = 24  # On-board diagnostic temperature sensor
_DIAG_5V_MEM_ADD = 26  # On-board 5V supply voltage
_TCP_MV1_ADD = 54
_I2C_THERMISTOR1_ADD = 101  # On-board thermistor temperature registers (verified via debug)
_MV_SCALE_FACTOR = 100.0
_DIAG_TEMP_SCALE_FACTOR = 10.0  # Same scale as thermocouple temperature
_DIAG_5V_SCALE_FACTOR = 100.0  # 5V reading scale
_THERMISTOR_SCALE_FACTOR = 10.0  # Thermistor temperature scale

_TC_TYPE_B = 0
_TC_TYPE_E = 1
_TC_TYPE_J = 2
_TC_TYPE_K = 3
_TC_TYPE_N = 4
_TC_TYPE_R = 5
_TC_TYPE_S = 6
_TC_TYPE_T = 7

_TC_TYPES = ['B', 'E', 'J', 'K', 'N', 'R', 'S', 'T']

class SMtc:
    def __init__(self, stack = 0, i2c = 1):
        if stack < 0 or stack > _STACK_LEVEL_MAX:
            raise ValueError('Invalid stack level!')
        self._hw_address_ = _CARD_BASE_ADDRESS + stack
        self._i2c_bus_no = i2c
        bus = smbus2.SMBus(self._i2c_bus_no)
        try:
            self._card_rev_major = bus.read_byte_data(self._hw_address_, _REVISION_HW_MAJOR_MEM_ADD)
            self._card_rev_minor = bus.read_byte_data(self._hw_address_, _REVISION_HW_MINOR_MEM_ADD)
        except Exception as e:
            bus.close()
            raise Exception("Fail to read with exception " + str(e))
        bus.close()

    def set_sensor_type(self, channel, cfg):
        if channel < 1 or channel > _IN_CH_COUNT:
            raise ValueError('Invalid input channel number number must be [1..8]!')
        if cfg < _TC_TYPE_B or cfg > _TC_TYPE_T:
            raise ValueError('Invalid thermocouple type, must be [0..7]!')
        bus = smbus2.SMBus(self._i2c_bus_no)
        try:
            bus.write_byte_data(self._hw_address_, _TCP_TYPE1_ADD + channel - 1, cfg)
        except Exception as e:
            bus.close()
            raise Exception("Fail to read with exception " + str(e))
        bus.close()

    def get_sensor_type(self, channel):
        if channel < 1 or channel > _IN_CH_COUNT:
            raise ValueError('Invalid input channel number number must be [1..8]!')
        bus = smbus2.SMBus(self._i2c_bus_no)
        try:
            val = bus.read_byte_data(self._hw_address_, _TCP_TYPE1_ADD + channel - 1)
        except Exception as e:
            bus.close()
            raise Exception("Fail to read with exception " + str(e))
        bus.close()
        return val

    def get_temp(self, channel):
        if channel < 1 or channel > _IN_CH_COUNT:
            raise ValueError('Invalid input channel number number must be [1..8]!')
        bus = smbus2.SMBus(self._i2c_bus_no)
        try:
            buff = bus.read_i2c_block_data(self._hw_address_, _TCP_VAL1_ADD + (channel - 1) * _TEMP_SIZE_BYTES, 2)
            val = struct.unpack('h', bytearray(buff))
        except Exception as e:
            bus.close()
            raise Exception("Fail to read with exception " + str(e))
        bus.close()
        return val[0] / _TEMP_SCALE_FACTOR

    def get_mv(self, channel):
        """Read channel voltage in mV and return as float."""
        if channel < 1 or channel > _IN_CH_COUNT:
            raise ValueError('Invalid input channel number number must be [1..8]!')
        bus = smbus2.SMBus(self._i2c_bus_no)
        try:
            buff = bus.read_i2c_block_data(self._hw_address_, _TCP_MV1_ADD + (channel - 1) * _TEMP_SIZE_BYTES, 2)
            val = struct.unpack('h', bytearray(buff))
        except Exception as e:
            bus.close()
            raise Exception("Fail to read with exception " + str(e))
        bus.close()
        return val[0] / _MV_SCALE_FACTOR

    def get_diag_temperature(self):
        """Read on-board diagnostic temperature in °C and return as float."""
        bus = smbus2.SMBus(self._i2c_bus_no)
        try:
            buff = bus.read_i2c_block_data(self._hw_address_, _DIAG_TEMPERATURE_MEM_ADD, 2)
            val = struct.unpack('h', bytearray(buff))
        except Exception as e:
            bus.close()
            raise Exception("Fail to read diagnostic temperature with exception " + str(e))
        bus.close()
        return val[0] / _DIAG_TEMP_SCALE_FACTOR

    def get_diag_5v(self):
        """Read on-board 5V supply voltage in volts and return as float."""
        bus = smbus2.SMBus(self._i2c_bus_no)
        try:
            buff = bus.read_i2c_block_data(self._hw_address_, _DIAG_5V_MEM_ADD, 2)
            val = struct.unpack('h', bytearray(buff))
        except Exception as e:
            bus.close()
            raise Exception("Fail to read 5V supply with exception " + str(e))
        bus.close()
        return val[0] / _DIAG_5V_SCALE_FACTOR

    def get_thermistor_temp(self, channel):
        """Read on-board thermistor temperature in °C and return as float.
        
        Reads one of the 8 on-board RTD/thermistor temperature sensors.
        Channels are numbered 1-8.
        
        Args:
            channel (int): Thermistor channel number [1..8]
            
        Returns:
            float: Temperature in degrees Celsius
            
        Raises:
            ValueError: If channel is not in valid range [1..8]
            Exception: If I2C read fails
        """
        if channel < 1 or channel > _THERMISTOR_CH_COUNT:
            raise ValueError('Invalid thermistor channel number, must be [1..8]!')
        bus = smbus2.SMBus(self._i2c_bus_no)
        try:
            buff = bus.read_i2c_block_data(self._hw_address_, _I2C_THERMISTOR1_ADD + (channel - 1) * _TEMP_SIZE_BYTES, 2)
            val = struct.unpack('h', bytearray(buff))
        except Exception as e:
            bus.close()
            raise Exception("Fail to read thermistor channel {} with exception ".format(channel) + str(e))
        bus.close()
        return val[0] / _THERMISTOR_SCALE_FACTOR

    def print_sensor_type(self, channel):
        print(_TC_TYPES[self.get_sensor_type(channel)])