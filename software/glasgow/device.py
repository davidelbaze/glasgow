import time
import usb1

from fx2 import *
from fx2.format import input_data


__all__ = ['GlasgowDevice', 'GlasgowDeviceError']


VID_QIHW     = 0x20b7
PID_GLASGOW  = 0x9db1

REQ_EEPROM   = 0x10
REQ_FPGA_CFG = 0x11
REQ_REGISTER = 0x12


class GlasgowDeviceError(FX2DeviceError):
    """An exception raised on a communication error."""


class GlasgowDevice(FX2Device):
    def __init__(self, firmware_file=None):
        super().__init__(VID_QIHW, PID_GLASGOW)
        if self._device.getDevice().getbcdDevice() == 0:
            if firmware_file is None:
                raise GlasgowDeviceError("Firmware is not uploaded")
            else:
                # TODO: log?
                with open(firmware_file, "rb") as f:
                    self.load_ram(input_data(f, fmt="ihex"))

                # let the device re-enumerate and re-acquire it
                time.sleep(1)
                super().__init__(VID_QIHW, PID_GLASGOW)

                # still not the right firmware?
                if self._device.getDevice().getbcdDevice() == 0:
                    raise GlasgowDeviceError("Firmware upload failed")

    def read_eeprom(self, idx, addr, length):
        """Read ``length`` bytes at ``addr`` from EEPROM at index ``idx``."""
        return self.control_read(usb1.REQUEST_TYPE_VENDOR, REQ_EEPROM, addr, idx, length)

    def write_eeprom(self, idx, addr, data):
        """Write ``data`` to ``addr`` in EEPROM at index ``idx``."""
        self.control_write(usb1.REQUEST_TYPE_VENDOR, REQ_EEPROM, addr, idx, data)

    def read_register(self, addr):
        """Read byte register at ``addr``."""
        return self.control_read(usb1.REQUEST_TYPE_VENDOR, REQ_REGISTER, addr, 0, 1)[0]

    def write_register(self, addr, value):
        """Write ``value`` to byte register at ``addr``."""
        self.control_write(usb1.REQUEST_TYPE_VENDOR, REQ_REGISTER, addr, 0, [value])

    def download_bitstream(self, data):
        """Download bitstream ``data`` to FPGA."""
        # Send consecutive chunks of bitstream.
        # Sending 0th chunk resets the FPGA.
        index = 0
        while index * 1024 < len(data):
            self.control_write(usb1.REQUEST_TYPE_VENDOR, REQ_FPGA_CFG, 0, index,
                               data[index * 1024:(index + 1)*1024])
            index += 1
        # Complete configuration by sending a request with no data.
        try:
            self.control_write(usb1.REQUEST_TYPE_VENDOR, REQ_FPGA_CFG, 0, index, [])
        except usb1.USBErrorTimeout:
            raise GlasgowDeviceError("FPGA configuration failed")
