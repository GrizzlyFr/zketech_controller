"""Control Zketech battery testers via serial communication

Init main class (Zketech) with serial port ID, then use it with the same
functions provided in the original Zketech GUI
"""

import logging
from functools import reduce
from operator import xor
import struct
from serial import Serial
from enum import Enum
from dataclasses import dataclass


ZKETECH_READING_TIMEOUT = 3  # in seconds
# (the EBC-A05+ sends data every two seconds for example)


logger = logging.getLogger(__name__)


# Defined by us for convenience

class DeviceState(Enum):
    """Associate the device state code with its description"""
    
    disconnected =      0
    idle =              1
    monitoring =        2
    testing =           3
    ending =            4

class ProgState(Enum):
    """Associate the set program number with its description"""
    
    d_cc =              0
    d_cp =              1
    c_nimh =            2
    c_nicd =            3
    c_liion =           4
    c_life =            5
    c_vrla =            6
    c_cv =              7
    

# Defined by Zketech

BEGIN_MARKER =          250
END_MARKER =            248

class ReqCode(Enum):
    """Describe the request code of the request frame.
    
    The request code is 8 bits (b7..b0)
    
    b3..b0=0: not used
    b3..b0=1: start test
    b3..b0=2: stop test
    b3..b0=3: not used / unknown
    b3..b0=4: calibration
    b3..b0=5: start device
    b3..b0=6: stop device
    b3..b0=7: update test
    b3..b0=8: continue test
    b3..b0=9: measure resistance
    
    b6..b4=0: set to constant current discharge
    b6..b4=1: set to constant power discharge
    b6..b4=2: set to NiMh charge
    b6..b4=3: set to NiCd charge
    b6..b4=4: set to LiIon charge
    b6..b4=5: set to LiFe charge
    b6..b4=6: set to Lead-Acid charge
    b6..b4=7: set to constant voltage charge
    
    b7: not used (=0)
    
    """
    
    stop_device =       0b00000110
    stop_test =         0b00000010
    start_device =      0b00000101
    mes_resistance =    0b00001001
    update_test =       0b00000111
    calibrate =         0b00000100
    start_d_cc =        0b00000001
    start_d_cp =        0b00010001
    start_c_nimh =      0b00100001
    start_c_nicd =      0b00110001
    start_c_liion =     0b01000001
    start_c_life =      0b01010001
    start_c_vrla =      0b01100001
    start_c_cv =        0b01111000
    conti_d_cc =        0b00001000
    conti_d_cp =        0b00011000
    conti_c_nimh =      0b00101000
    conti_c_nicd =      0b00111000
    conti_c_liion =     0b01001000
    conti_c_life =      0b01011000
    conti_c_vrla =      0b01101000
    conti_c_cv =        0b01111000

class ResCode:
    """Describe the response code of the response frame.
    
    The request code is 8 bits (b7..b0)
    
    It is constructed by multipliing a status code by ten and adding a program
    code
    
    This empty class is kept as information
    
    """
    pass

class StateCode(Enum):
    """Describe the status code of the response code of the response frame.
    
    Associate the code with its description
    
    """
    
    init =              10
    ended =             0
    testing =           1
    ending =            2

class ProgCode(Enum):
    """Describe the program code of the response code of the response frame.
    
    Associate the code with its description
    
    """
    
    d_cc =              0
    d_cp =              1
    c_nimh =            2
    c_nicd =            3
    c_liion =           4
    c_life =            5
    c_vrla =            6
    c_cv =              7
    
class PartNumber(Enum):
    """Describe the device Part Number code of the response frame.
    
    Associate the code with its Part Number
    
    """
    
    ebc_a =             1
    ebc_ah =            2
    ebc_b =             3
    ebc_bh =            4
    ebc_a05 =           5
    ebc_a10h =          6
    ebc_a10 =           7
    ebc_b10 =           8
    ebc_a20 =           9
    ebc_a40l =          10
    ebd_a =             11
    ebd_ah =            12
    ebd_b =             13
    ebd_bh =            14
    ebd_a10 =           15
    ebd_a15 =           16
    ebd_a2s =           17
    ebd_a5s =           18
    ebd_a20h =          19

    
# Main usage functions

def ZketechParametersError(Exception):
    """To be raised when an improper parameter is passed"""
    pass


def zketech_checksum(buff: bytes) -> int:
    """Compute the chekcum used by zketech equipments."""
    return reduce(xor, buff) % 240


def check_buffer_validity(buff:bytes) -> bool:
    """Check if the response buffer is compliant with the frame definition."""
    if not len(buff) in (10, 19):
        logger.warning(f"Buffer's length ({len(buff)}) does not correspond to a request or a response")
        return False
    if not buff[0] == BEGIN_MARKER:
        logger.warning(f"Buffer's first byte ({buff[0]}) does not correspond to a begin marker ({BEGIN_MARKER})")
        return False
    if not buff[-1] == END_MARKER:
        logger.warning(f"Buffer's last byte ({buff[-1]}) does not correspond to a end marker ({END_MARKER})")
        return False
    if not buff[-2] == zketech_checksum(buff[1:-2]):
        logger.warning(f"Buffer's computed checksum ({reduce(xor, buff[1:-2])}) does not correspond to checksum field value ({buff[-2]})")
        return False
    if len(buff) == 10:
        try:
            ReqCode(buff[1])
        except:
            logger.warning(f"Unknown request ReqCode ({buff[1]})")
            return False
    if len(buff) == 19:
        state_code_val = buff[1] // 10
        try:
            StateCode(state_code_val)
        except:
            logger.warning(f"Unknown response StateCode ({state_code_val})")
            return False
        prog_code_val = buff[1] % 10
        try:
            ProgCode(prog_code_val)
        except:
            logger.warning(f"Unknown response ProgCode ({prog_code_val})")
            return False
        part_number_val = buff[-3]
        try:
            PartNumber(part_number_val)
        except:
            logger.warning(f"Unknown zketech part number ({part_number_val})")
            return False
    return True


# Main usage classes

@dataclass
class RequestDataSet:
    """Store the parameters of a request frame.
    
    p1 to p3 are raw values, with scaling different for each request code.
    
    """
    
    req_code: ReqCode
    p1: int
    p2: int
    p3: int
    
    def __init__(self, 
                 req_code: ReqCode,
                 p1: int=0,
                 p2: int=0,
                 p3: int=0):
        """Init a request data set.
        
        Check the parameters, split them in parts, compute checksum.
        
        """
        if any([p1<0, p2<0, p3<0]):
            raise ValueError("p1 to P3 parameters shall not be negative")
        if any([p1>57600, p2>57600, p3>57600]):
            raise ValueError("p1 to P3 parameters shall ne inferior to 57600")
        self.begin_marker = BEGIN_MARKER
        self.req_code = req_code
        self.req_code_val = req_code.value
        self.p1 = p1
        self.p1_h = p1 // 240
        self.p1_l = p1 % 240
        self.p2 = p2
        self.p2_h = p2 // 240
        self.p2_l = p2 % 240
        self.p3 = p3
        self.p3_h = p3 // 240
        self.p3_l = p3 % 240
        values_to_checksum = (
            self.req_code_val,
            self.p1_h,
            self.p1_l,
            self.p2_h,
            self.p2_l,
            self.p3_h,
            self.p3_l,
            )
        self.checksum = zketech_checksum(values_to_checksum)
        self.end_marker = END_MARKER


@dataclass
class ResponseDataSet:
    """ Store the parameters and metrics received in a response frame.
    
    Scaling from raw values to metrics is not dependant of the program.
    
    """
    
    state_code: StateCode
    prog_code: ProgCode
    i: int
    u: int
    c: int
    unknown: int
    p1: int
    p2: int
    p3: int
    part_number: PartNumber
    checksum: int
    
    def __init__(self,
                 begin_marker: int,
                 res_code_val: int,
                 i_h: int,
                 i_l: int,
                 u_h: int,
                 u_l: int,
                 c_h: int,
                 c_l: int,
                 unknown_h: int,
                 unknown_l: int,
                 p1_h: int,
                 p1_l: int,
                 p2_h: int,
                 p2_l: int,
                 p3_h: int,
                 p3_l: int,
                 part_number_val: int,
                 checksum: int,
                 end_marker: int):
        """Init a response data set.
        
        Join and scale metrics parts, join parameters parts.
        
        """
        self.state_code = StateCode(res_code_val//10)
        self.prog_code = ProgCode(res_code_val%10)
        self.i = (i_h * 240 + i_l) / 1000
        self.u = (u_h * 240 + u_l) / 1000
        self.c = c_h * 240 + c_l
        self.unknown = unknown_h * 240 + unknown_l
        self.p1 = p1_h * 240 + p1_l
        self.p2 = p2_h * 240 + p2_l
        self.p3 = p3_h * 240 + p3_l
        self.part_number = PartNumber(part_number_val)
        self.checksum = checksum


class RequestFrame:
    """ Define request frames.
    
    Handle parameters to bytes conversion.
    
    Request frames are built as (10 bytes ; little endian):
        - A begin marker
        - A request code
        - Three parameters in two parts each
        - The checksum
        - A end marker
    
    """
    
    labels = (
        "begin_marker",
        "req_code",
        "p1_h"
        "p1_l",
        "p2_h"
        "p2_l",
        "p3_h"
        "p3_l",
        "checksum",
        "end_marker",
        )
    
    def get_buffer(self, data: RequestDataSet) -> bytes:
        """Compute the bytes from the IDs and parameters."""
        values = (
            data.begin_marker,
            data.req_code.value,
            data.p1_h,
            data.p1_l,
            data.p2_h,
            data.p2_l,
            data.p3_h,
            data.p3_l,
            data.checksum,
            data.end_marker)
        buff = struct.pack("<"+"B"*10, *values)
        if not check_buffer_validity(buff):
            return b''
        return buff

class ResponseFrame:
    """ Define response frames.
    
    Handle bytes to IDs, parameters and metrics conversion.
    
    Response frames are built as (19 bytes ; little endian):
        - A begin marker
        - A response code
        - Three metrics in two parts each
        - One field of unknown usage
        - Three parameters in two parts each
        - The Part Number of the device
        - The checksum
        - A end marker
    
    """
    
    labels = (
        "begin_marker",
        "res_code_val",
        "i_h",
        "i_l",
        "u_h",
        "u_l",
        "c_h",
        "c_l",
        "unknown_h",
        "unknown_l",
        "p1_h",
        "p1_l",
        "p2_h",
        "p2_l",
        "p3_h",
        "p3_l",
        "part_number_val",
        "checksum",
        "end_marker",
        )

    def get_response_data_set(self, buff: bytes) -> ResponseDataSet:
        """Compute IDs, parameters parts and metrics parts from bytes."""
        if not check_buffer_validity(buff):
            return None
        values = struct.unpack("<"+"B"*19, buff)
        kwargs = {k:v for k,v in zip(self.labels, values)}
        return ResponseDataSet(**kwargs)

    
class Zketech(Serial):
    """Handle exchange between device and terminal.
    
    Handle low level exchange functions and high level programs ; provide data
    on device current set program and device current state.
    
    Low level:
        - Send request and read response
        
    High level:
        - Get device state
        - Start and stop device
        - Start charge programs
        - Start discharge programs
        - Stop programs
        - Perform internal resistance measurement
        
    When connected to a computer and initialised, the device display a 'PC'
    label on screen and send continuously response frames, indenpendently of it
    unning a program or not. The device is always set on one program,
    independently of its state.
    
    The device can be in states:
        - Serial port closed (physical unit can still be running programs)
        - Serial port opened but not connected (physical unit can still be
        running programs) ; while connected the device continuously send frames
        - Connected and not performing tests
        - Performing tests
        - In the last step of a test
    
    """
    
    device_state: DeviceState = DeviceState["disconnected"]
    prog_state: ProgState|None = None
    part_number: PartNumber|None = None
    
    def __init__(self, com_port: str) -> None:
        """Init device by opening serial port."""
        super().__init__(port=com_port,
                         baudrate=9600,
                         bytesize=8,
                         parity='E',
                         stopbits=1,
                         timeout=ZKETECH_READING_TIMEOUT)
        if self.isOpen():
            self.device_state = DeviceState["idle"]
            self.flush()
    
    def send_request(self,
                     req_code: ReqCode,
                     p1: int,
                     p2: int,
                     p3: int) -> None:
        """Send request to device
        
        Build request data, get the frame buffer, and send it.
        
        """
        if not self.isOpen():
            self.device_state = DeviceState["disconnected"]
            return
        frame = RequestFrame()
        data = RequestDataSet(req_code, p1, p2, p3)
        buff = frame.get_buffer(data)
        if buff:
            self.write(buff)
            logger.debug(f"Sended request to device ({data})")
            logger.debug(f"Sended buffer: 0x{buff.hex()}")
    
    def read_response(self) -> None|ResponseDataSet:
        """Read response from device.
        
        Check buffer, parse data.
        
        """
        self.part_number = None
        self.battery_type = None
        if not self.isOpen():
            self.device_state = DeviceState["disconnected"]
            logger.debug("Tried to read response from a disconnected device")
            return
        # TBDone : Improvements: either have a constant async read on background or automatically
        # stop the PC connection so the device does not fill continuously the buffer
        if self.in_waiting > 19:
            self.reset_input_buffer()
        # end of the to be improved section
        buff = self.read(size=19)
        if len(buff) == 0:
            self.device_state = DeviceState["idle"]
            logger.debug("Tried to read response from an idled device")
            return
        if not check_buffer_validity(buff):
            logger.debug("Buffer invalid")
            return
        self.device_state = DeviceState["monitoring"]
        frame = ResponseFrame()
        data = frame.get_response_data_set(buff)
        self.part_number = data.part_number
        if data.state_code.name == "testing":
            self.device_state = DeviceState["testing"]
        if data.state_code.name == "ending":
            self.device_state = DeviceState["ending"]
        self.prog_state = ProgState(data.prog_code.value)
        logger.debug(f"Received response from device ({data})")
        logger.debug(f"Received buffer: 0x{buff.hex()}")
        return data
    
    def get_device_state(self) -> None:
        """Get device state from next sent frame."""
        self.read_response()
    
    def start_device(self) -> None:
        """Request the device to start sending frames."""
        if not self.device_state == DeviceState["idle"]:
            logger.warning(f"A startup of the device was requested while device in wrong state ({self.device_state})")
            return
        req_code = ReqCode["start_device"]
        p1 = 0
        p2 = 0
        p3 = 0
        logger.debug(f"Sending request {(req_code, p1, p2, p3)}")
        self.send_request(req_code, p1, p2, p3)
    
    def stop_device(self) -> None:
        """Request the device to stop sending frames."""
        if not self.device_state == DeviceState["monitoring"]:
            logger.warning(f"A stopping of the device was requested while device in wrong state ({self.device_state})")
            return
        req_code = ReqCode["stop_device"]
        p1 = 0
        p2 = 0
        p3 = 0
        logger.debug(f"Sending request {(req_code, p1, p2, p3)}")
        self.send_request(req_code, p1, p2, p3)

    def stop_test(self):
        """Request the device to stop sending frames."""
        if not self.device_state == DeviceState["testing"]:
            logger.warning(f"A stopping of a test was requested while device in wrong state ({self.device_state})")
            return
        req_code = ReqCode["stop_test"]
        p1 = 0
        p2 = 0
        p3 = 0
        logger.debug(f"Sending request {(req_code, p1, p2, p3)}")
        self.send_request(req_code, p1, p2, p3)
     
    def continue_test(self) -> None:
        # The EB software display an incoherent behavior with this function:
        #     When resuming at startup, start with charge of 0 mAh (ok)
        #     When resuming after a stop, display incoherent charge (nok)
        # Thus we didn't implemented this function as we don't fully understand it
        raise NotImplementedError()
     
    def update_test(self) -> None:
        # The EB software allows only an update on constant current discharge
        # Thus we didn't implemented this function as we don't fully understand it
        raise NotImplementedError()
    
    def discharge_cc(self,
                     current: float,
                     cutoff_voltage: float,
                     max_duration: int=0) -> None:
        """Request the device to start a discharge test at constant current."""
        if not self.device_state == DeviceState["monitoring"]:
            logger.warning(f"A startup of a test was requested while device in wrong state ({self.device_state})")
            return
        if current < 0:
            raise ZketechParametersError("Current shall be positive")
        if cutoff_voltage < 0:
            raise ZketechParametersError("Cutoff Voltage shall be 1 or more")
        if max_duration < 0:
            raise ZketechParametersError("Max Duration shall be positive")
        if max_duration > 999:
            raise ZketechParametersError("Max Duration shall be inferior to 999")
        # #TBDone: checking bad parameters for superior boundaries
        req_code = ReqCode["start_d_cc"]
        p1 = int(current*1000)
        p2 = int(cutoff_voltage*100)
        p3 = int(max_duration)
        logger.debug(f"Sending request {(req_code, p1, p2, p3)}")
        self.send_request(req_code, p1, p2, p3)

    def discharge_cp(self,
                     power: float,
                     cutoff_voltage: float,
                     max_duration: int=0) -> None:
        """Request the device to start a discharge test at constant power."""
        if not self.device_state == DeviceState["monitoring"]:
            logger.warning(f"A startup of a test was requested while device in wrong state ({self.device_state})")
            return
        if power < 0:
            raise ZketechParametersError("Power shall be positive")
        if cutoff_voltage < 0:
            raise ZketechParametersError("Cutoff Voltage shall be 1 or more")
        if max_duration < 0:
            raise ZketechParametersError("Max Duration shall be positive")
        if max_duration > 999:
            raise ZketechParametersError("Max Duration shall be inferior to 999")
        # #TBDone: checking bad parameters for superior boundaries
        req_code = ReqCode["start_d_cp"]
        p1 = int(power*10)
        p2 = int(cutoff_voltage*100)
        p3 = int(max_duration)
        logger.debug(f"Sending request {(req_code, p1, p2, p3)}")
        self.send_request(req_code, p1, p2, p3)

    def _charge_generic(self,
                        req_code: ReqCode,
                        current: float,
                        nb_cells: int,
                        max_duration: int) -> None:
        if not self.device_state == DeviceState["monitoring"]:
            logger.warning(f"A startup of a test was requested while device in wrong state ({self.device_state})")
            return
        if current < 0:
            raise ZketechParametersError("Current shall be positive")
        if nb_cells < 1:
            raise ZketechParametersError("Number of cells shall be 1 or more")
        if max_duration < 0:
            raise ZketechParametersError("Max Duration shall be positive")
        if max_duration > 999:
            raise ZketechParametersError("Max Duration shall be inferior to 999")
        # #TBDone: checking bad parameters for superior boundaries
        req_code = req_code
        p1 = int(current*1000)
        p2 = int(nb_cells)
        p3 = int(max_duration)
        logger.debug(f"Sending request {(req_code, p1, p2, p3)}")
        self.send_request(req_code, p1, p2, p3)
    
    def charge_nimh(self,
                    current: float,
                    nb_cells: int,
                    max_duration: int) -> None:
        """Request the device to start a charge of a NiMh type battery."""
        req_code = ReqCode["start_c_nimh"]
        self._charge_generic(req_code, current, nb_cells, max_duration)
     
    def charge_nicd(self,
                    current: float,
                    nb_cells: int,
                    max_duration: int) -> None:
        """Request the device to start a charge of a NiCd type battery."""
        req_code = ReqCode["start_c_nicd"]
        self._charge_generic(req_code, current, nb_cells, max_duration)
     
    def charge_liion(self,
                    current: float,
                    nb_cells: int,
                    max_duration: int) -> None:
        """Request the device to start a charge of a lithium-ion type battery."""
        req_code = ReqCode["start_c_liion"]
        self._charge_generic(req_code, current, nb_cells, max_duration)
     
    def charge_life(self,
                    current: float,
                    nb_cells: int,
                    max_duration: int) -> None:
        """Request the device to start a charge of a LiFe type battery."""
        req_code = ReqCode["start_c_life"]
        self._charge_generic(req_code, current, nb_cells, max_duration)
     
    def charge_vrla(self,
                    current: float,
                    nb_cells: int,
                    max_duration: int) -> None:
        """Request the device to start a charge of a lead-acid type battery."""
        req_code = ReqCode["start_c_vrla"]
        self._charge_generic(req_code, current, nb_cells, max_duration)
     
    def charge_cv(self,
                  current: float,
                  nb_cells: int,
                  max_duration: int) -> None:
        """Request the device to start a charge at constant voltage."""
        req_code = ReqCode["start_c_cv"]
        self._charge_generic(req_code, current, nb_cells, max_duration)
     
    def measure_resistance(self,
                           current: int) -> None:
        """Request the device to perform an internal resistance measurement.
        
        Current is in mA.
        
        """
        if not self.device_state == DeviceState["monitoring"]:
            logger.warning(f"A performing of a resistance measurement was requested while device in wrong state ({self.device_state})")
            return
        if current < 0:
            raise ZketechParametersError("Current shall be positive")
        if current > 30000:  # Is it only for EBC-A05+ or is it standard?
            raise ZketechParametersError("Current shall be inferior to 3 A")
        req_code = ReqCode["mes_resistance"]
        p1 = int(current)
        p2 = 0
        p3 = 0
        logger.debug(f"Sending request {(req_code, p1, p2, p3)}")
        self.send_request(req_code, p1, p2, p3)
        self.reset_input_buffer()
        res = self.read_response()
        if not res:
            logger.debug("The resistance measurement request got no response")
            return
        return int(res.c/(p1/1000))

    def calibrate_voltage(self,
                          voltage: float,
                          level:str) -> None:
        """Calibrate the voltage measurement of the device.
        
        Voltage is in Volts. Level is 'lower' or 'upper'.
        
        """
        if not self.device_state == DeviceState["monitoring"]:
            logger.warning(f"A performing of a voltage calibration was requested while device in wrong state ({self.device_state})")
            return
        if voltage < 0:
            raise ZketechParametersError("Voltage shall be positive")
        if not level in ("lower", "upper"):
            raise ZketechParametersError("Level shall be 'lower' or 'upper'")
        req_code = ReqCode["calibrate"]
        ### Fix for weird Zketech coding: for calibration, they add one field and shift p1
        p1 = int(voltage * 1000) // 240
        p2 = int(voltage * 1000) % 240 * 240
        p3 = 0
        if level == "lower":
            p1 += 240 * 0
        if level == "upper":
            p1 += 240 * 1
        ###
        logger.debug(f"Sending request {(req_code, p1, p2, p3)}")
        self.send_request(req_code, p1, p2, p3)
        self.reset_input_buffer()

    def calibrate_current(self,
                         current: float,
                         level:str) -> None:
        """Calibrate the current measurement of the device.
        
        Current is in Amp. Level is 'lower' or 'upper'.
        
        """
        if (not self.device_state == DeviceState["testing"]) or \
           (not self.prog_state == ProgState["d_cc"]):
            logger.warning(f"A performing of a current calibration was requested while device in wrong state ({self.device_state}, {self.prog_state})")
            return
        if current < 0:
            raise ZketechParametersError("Current shall be positive")
        if not level in ("lower", "upper"):
            raise ZketechParametersError("Level shall be 'lower' or 'upper'")
        ### Fix for weird Zketech coding: for calibration, they add one field and shift p1
        req_code = ReqCode["calibrate"]
        p1 = int(current * 1000) // 240
        p2 = int(current * 1000) % 240 * 240
        p3 = 0
        if level == "lower":
            p1 += 240 * 2
        if level == "upper":
            p1 += 240 * 3
        logger.debug(f"Sending request {(req_code, p1, p2, p3)}")
        self.send_request(req_code, p1, p2, p3)
        self.reset_input_buffer()
