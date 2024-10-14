"""Textual interface to control Zketech Mono-Channel Battery Testers

Does not provide multi-steps tests
"""

import logging
import os
import sys

from zketech import Zketech, ZketechParametersError, ResponseDataSet


WORKING_DIRECTORY = r"./local_files"
LOGGING_FILENAME = r"zketech.log"
LOGGING_LEVEL = logging.INFO
BLOCKING_SAFETY_WATCHER = True

if not os.path.exists(WORKING_DIRECTORY):
    os.mkdir(WORKING_DIRECTORY)

logging.basicConfig(filename=os.path.join(WORKING_DIRECTORY, LOGGING_FILENAME), 
                    encoding='utf-8', 
                    level=LOGGING_LEVEL,
                    format='%(asctime)s:%(levelname)s:%(message)s')
logger = logging.getLogger(__name__)


com_port = sys.argv[1]


def format_resp_for_print(resp: ResponseDataSet) -> str:
    return f"Voltage: {resp.u:6.3f} V, Current: {resp.i:6.3f} A, Capacity: {resp.c:4.0f} mAh"

class SafetyWatcher:
    """Add additional safety controls to prevent issues with testing batteries
    
    To add a new watcher, create a new functions in this class and add its call
    to the 'check' function
    """

    min_voltage: float|None = None
    min_current: float|None = None
    last_voltage: float|None = None
    last_current: float|None = None

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        pass
    
    def update(self, resp: ResponseDataSet) -> bool:
        """Update internal metrics from a response data set."""
        if not resp.state_code.name == "testing":
            self.min_voltage = None
            self.min_current = None
        if (not self.min_voltage) or (not self.min_current):
            return
        self.last_voltage = resp.u
        self.last_current = resp.i
        if not (self.min_voltage and self.min_current):
            self.min_voltage = self.last_voltage
            self.min_current = self.last_current
            return False
        self.min_voltage = min(self.min_voltage, self.last_voltage)
        self.min_current = min(self.min_current, self.last_current)

    def check(self) -> bool:
        """Call each safety watchers."""
        if self.check_charging_current_increase() == True:
            return True
        return False

    def check_charging_current_increase(self) -> bool:
        """Check for an increase of the charging current.
        
        An increase of the charging current not triggered by an update from the
        user can indicate a thermal runaway.
        
        """
        if not self.last_current:
            return
        if not self.min_current:
            return
        return self.last_current > (self.min_current + 0.05)

class EvaluateDevice:
    """Get device state from next sent frame."""
    
    prompt = "Determinate current device state"
    
    def __init__(self, device: Zketech, sw: SafetyWatcher):
        logger.info("Start program 'EvaluateDevice'")
        device.get_device_state()
        print(f"Device in state {zk.device_state.name}")
        logger.info("Stop program 'EvaluateDevice' with result: zk.device_state")

class StartDevice:
    """Request the device to continuously send response frames."""
    
    prompt = "Start Zketech device on PC mode"
    
    def __init__(self, device: Zketech, sw: SafetyWatcher):
        logger.info("Start program 'StartDevice'")
        device.start_device()
        logger.info("Stop program 'StartDevice'")

class StopDevice:
    """Request the device to stop sending response frames."""
    
    prompt = "Stop Zketech device from PC mode"
    
    def __init__(self, device: Zketech, sw: SafetyWatcher):
        logger.info("Start program 'StopDevice'")
        device.stop_device()
        logger.info("Stop program 'StopDevice'")

class ContinuousRead:
    """Continuously read data from the device"""

    prompt = "Continuously read data from the device (ctrl+c to stop)"

    def __init__(self, device: Zketech, sw: SafetyWatcher):
        logger.info("Start program 'ContinuousRead'")
        while True:
            logger.debug("Request for reading")
            resp = zk.read_response()
            logger.debug(f"Response is: {resp}")
            logger.debug(f"Device state is: {zk.device_state}")
            logger.debug(f"Program is: {zk.prog_state}")
            logger.debug(f"Device reference is: {zk.part_number}")
            if zk.device_state.name in ("disconnected", "idle"):
                print(f"Device in state {zk.device_state.name}; ending continuous read")
                return
            if resp:
                sw.update(resp)
                if sw.check() == True:
                    if BLOCKING_SAFETY_WATCHER == True:
                        print("Received a warning from the safety watcher, halting test")
                        device.stop_test()
                    else:
                        print("Received a warning from the safety watcher, continuing")
                print(format_resp_for_print(resp))
        logger.info("Stop program 'ContinuousRead'")

class ContinuousReadDuringTest:
    """Continuously read date from the device, stopping when the test end"""

    prompt = "Continuously read data from the device until the end of the test"

    def __init__(self, device: Zketech, sw: SafetyWatcher):
        logger.info("Start program 'ContinuousReadDuringTest'")
        while True:
            resp = zk.read_response()
            logger.debug(f"Response is: {resp}")
            logger.debug(f"Device state is: {zk.device_state}")
            logger.debug(f"Program is: {zk.prog_state}")
            logger.debug(f"Device reference is: {zk.part_number}")
            if zk.device_state.name in ("disconnected", "idle", "monitoring",):
                print(f"Device in state {zk.device_state.name}; ending continuous read")
                logger.info(f"Stop program 'ContinuousRead' on device state: {zk.device_state}")
                return
            if zk.device_state.name in ("ending",):
                print("The test reached its end")
                logger.info(f"Received a end of test notice on device state: {zk.device_state}")
            if resp:
                sw.update(resp)
                if sw.check() == True:
                    if BLOCKING_SAFETY_WATCHER == True:
                        print("Received a warning from the safety watcher, halting test")
                        device.stop_test()
                    else:
                        print("Received a warning from the safety watcher, continuing")
                print(format_resp_for_print(resp))

class StopTest:
    """Stop current running test."""
    
    prompt = "Stop Zketech running test"
    
    def __init__(self, device: Zketech, sw: SafetyWatcher):
        logger.info("Start program 'StopTest'")
        device.stop_test()
        logger.info("Stop program 'StopTest'")

class ConstantCurrentDischarge:
    """Do a discharge test at constant current."""
    
    prompt = "Do a discharge test at constant current"
    
    def __init__(self, device: Zketech, sw: SafetyWatcher):
        logger.info("Getting parameters for 'ConstantCurrentDischarge'")
        print("Enter current setpoint (A):")
        current = input("> ")
        try:
            self.current = float(current)
        except:
            print("The input parameter shall be a float value")
            logger.info("User types a wrong value")
            return False
        print("Enter cutoff voltage setpoint (V):")
        cutoff_voltage = input("> ")
        try:
            self.cutoff_voltage = float(cutoff_voltage)
        except:
            print("The input parameter shall be a float value")
            logger.info("User types a wrong value")
            return False
        print("Enter timeout (min), '0' for no timeout:")
        max_duration = input("> ")
        try:
            self.max_duration = int(max_duration)
        except:
            print("The input parameter shall be a integer value")
            logger.info("User types a wrong value")
            return False
        logger.info(f"Start program 'ConstantCurrentDischarge' with parameters: {(self.current, self.cutoff_voltage, self.max_duration)}")
        device.discharge_cc(self.current,
                            self.cutoff_voltage,
                            self.max_duration)
        logger.info("Stop program 'ConstantCurrentDischarge'")
        
class ConstantPowerDischarge:
    """Do a discharge test at constant power."""
    
    prompt = "Do a discharge test at constant power"
    
    def __init__(self, device: Zketech, sw: SafetyWatcher):
        logger.info("Getting parameters for 'ConstantPowerDischarge'")
        print("Enter power setpoint (W):")
        power = input("> ")
        try:
            self.power = float(power)
        except:
            print("The input parameter shall be a float value")
            logger.info("User types a wrong value")
            return False
        print("Enter cutoff voltage setpoint (V):")
        cutoff_voltage = input("> ")
        try:
            self.cutoff_voltage = float(cutoff_voltage)
        except:
            print("The input parameter shall be a float value")
            logger.info("User types a wrong value")
            return False
        print("Enter timeout (min), '0' for no timeout:")
        max_duration = input("> ")
        try:
            self.max_duration = int(max_duration)
        except:
            print("The input parameter shall be an int value")
            logger.info("User types a wrong value")
            return False
        logger.info(f"Start program 'ConstantPowerDischarge' with parameters: {(self.current, self.cutoff_voltage, self.max_duration)}")
        device.discharge_cc(self.power,
                            self.cutoff_voltage,
                            self.max_duration)
        logger.info("Stop program 'ConstantPowerDischarge'")

class _GenericCharge:

    def __init__(self, device: Zketech, sw: SafetyWatcher):
        print("Enter current setpoint (A):")
        current = input("> ")
        try:
            self.current = float(current)
        except:
            print("The input parameter shall be a float value")
            logger.info("User types a wrong value")
            return False
        print("Enter the number of cells:")
        nb_cells = input("> ")
        try:
            self.nb_cells = int(nb_cells)
        except:
            print("The input parameter shall be a integer value")
            logger.info("User types a wrong value")
            return False
        print("Enter current setpoint (min), '0' for no timeout:")
        max_duration = input("> ")
        try:
            self.max_duration = int(max_duration)
        except:
            print("The input parameter shall be a integer value")
            logger.info("User types a wrong value")
            return False
        return True

class NimhCharge(_GenericCharge):
    """Charge a NiMh battery or battery pack."""

    prompt = "Charge a NiMh battery or battery pack"

    def __init__(self, device: Zketech, sw: SafetyWatcher):
        logger.info("Getting parameters for 'NimhCharge'")
        if not super().__init__(device, sw) == True:
            return
        logger.info(f"Start program 'NimhCharge' with parameters: {(self.current, self.nb_cells, self.max_duration)}")
        device.charge_nimh(self.current,
                           self.nb_cells,
                           self.max_duration)
        logger.info("Stop program 'NimhCharge'")

class NicdCharge(_GenericCharge):
    """Charge a NiCd battery or battery pack."""

    prompt = "Charge a NiCd battery or battery pack"

    def __init__(self, device: Zketech, sw: SafetyWatcher):
        logger.info("Getting parameters for 'NicdCharge'")
        if not super().__init__(device, sw) == True:
            return
        logger.info(f"Start program 'NicdCharge' with parameters: {(self.current, self.nb_cells, self.max_duration)}")
        device.charge_nicd(self.current,
                           self.nb_cells,
                           self.max_duration)
        logger.info("Stop program 'NicdCharge'")

class LiionCharge(_GenericCharge):
    """Charge a LiIon battery or battery pack."""

    prompt = "Charge a LiIon battery or battery pack"

    def __init__(self, device: Zketech, sw: SafetyWatcher):
        logger.info("Getting parameters for 'LiionCharge'")
        if not super().__init__(device, sw) == True:
            return
        logger.info(f"Start program 'LiionCharge' with parameters: {(self.current, self.nb_cells, self.max_duration)}")
        device.charge_liion(self.current,
                            self.nb_cells,
                            self.max_duration)
        logger.info("Stop program 'LiionCharge'")

class LifeCharge(_GenericCharge):
    """Charge a LiFe battery or battery pack."""

    prompt = "Charge a LiFe battery or battery pack"

    def __init__(self, device: Zketech, sw: SafetyWatcher):
        logger.info("Getting parameters for 'LifeCharge'")
        if not super().__init__(device, sw) == True:
            return
        logger.info(f"Start program 'LifeCharge' with parameters: {(self.current, self.nb_cells, self.max_duration)}")
        device.charge_life(self.current,
                           self.nb_cells,
                           self.max_duration)
        logger.info("Stop program 'LifeCharge'")

class VrlaCharge(_GenericCharge):
    """Charge a VRLA battery or battery pack."""

    prompt = "Charge a VRLA battery or battery pack"

    def __init__(self, device: Zketech, sw: SafetyWatcher):
        logger.info("Getting parameters for 'VrlaCharge'")
        if not super().__init__(device, sw) == True:
            return
        logger.info(f"Start program 'VrlaCharge' with parameters: {(self.current, self.nb_cells, self.max_duration)}")
        device.charge_vrla(self.current,
                           self.nb_cells,
                           self.max_duration)
        logger.info("Stop program 'VrlaCharge'")

class CvCharge(_GenericCharge):
    """Charge a generic battery or battery pack at constant voltage."""

    prompt = "Charge a generic battery or battery pack at constant voltage"

    def __init__(self, device: Zketech, sw: SafetyWatcher):
        logger.info("Getting parameters for 'CvCharge'")
        if not super().__init__(device, sw) == True:
            return
        logger.info(f"Start program 'CvCharge' with parameters: {(self.current, self.nb_cells, self.max_duration)}")
        device.charge_cv(self.current,
                         self.nb_cells,
                         self.max_duration)
        logger.info("Stop program 'CvCharge'")

class ResistanceMeasurement:
    """Measure the internal resistance of the battery."""
    
    prompt = "Measure the internal resistance of the battery"
    
    def __init__(self, device: Zketech, sw: SafetyWatcher):
        logger.info("Getting parameter for 'ResistanceMeasurement'")
        print("Enter current setpoint (mA):")
        current = input("> ")
        try:
            self.current = int(current)
        except:
            print("The input parameter shall be an integer value")
            logger.info("User types a wrong value")
            return
        print()
        logger.info(f"Start program 'ResistanceMeasurement' with a current setpoint of {self.current} mA")
        resistance = device.measure_resistance(self.current)
        if not resistance:
            print("No resistance returned from the test")
            logger.info("The program failed to receive a resistance value")
        else:
            print(f"Measured resistance: {resistance} mOhm")
            logger.info(f"Measured resistance: {resistance} mOhm")
        logger.info(f"Stop program 'ConstantCurrentDischarge' with a returned value of '{resistance}'")

class LowVoltageCalibration:
    """Calibrate the lower values of the voltage measurement."""
    
    prompt = "Calibrate the low voltage measurement"
    
    def __init__(self, device: Zketech, sw: SafetyWatcher):
        logger.info("Getting parameter for 'LowVoltageCalibration'")
        print("Enter low voltage calibration value (V):")
        voltage = input("> ")
        try:
            self.voltage = float(voltage)
        except:
            print("The input parameter shall be a float value")
            logger.info("User typed a wrong value")
            return
        print()
        logger.info(f"Setting low voltage calibration to {voltage} V")
        device.calibrate_voltage(self.voltage, "lower")

class HighVoltageCalibration:
    """Calibrate the upper values of the voltage measurement."""
    
    prompt = "Calibrate the high voltage measurement"
    
    def __init__(self, device: Zketech, sw: SafetyWatcher):
        logger.info("Getting parameter for 'HighVoltageCalibration'")
        print("Enter high voltage calibration value (V):")
        voltage = input("> ")
        try:
            self.voltage = float(voltage)
        except:
            print("The input parameter shall be a float value")
            logger.info("User typed a wrong value")
            return
        print()
        logger.info(f"Setting high voltage calibration to {voltage} V")
        device.calibrate_voltage(self.voltage, "upper")

class LowCurrentCalibration:
    """Calibrate the lower value of the current measurement."""
    
    prompt = "Calibrate the low current measurement"
    
    def __init__(self, device: Zketech, sw: SafetyWatcher):
        logger.info("Getting parameter for 'LowCurrentCalibration'")
        print("The device shall first be supplied a proper tension and be in constant current discharge to calibrate the current")
        print("Enter low current calibration value (A):")
        current = input("> ")
        try:
            self.current = float(current)
        except:
            print("The input parameter shall be a float value")
            logger.info("User typed a wrong value")
            return
        print()
        logger.info(f"Setting low current calibration to {voltage} V")
        device.calibrate_current(self.current, "lower")

class HighCurrentCalibration:
    """Calibrate the upper value of the current measurement."""
    
    prompt = "Calibrate the high current measurement"
    
    def __init__(self, device: Zketech, sw: SafetyWatcher):
        logger.info("Getting parameter for 'HighCurrentCalibration'")
        print("The device shall first be supplied a proper tension and be in constant current discharge to calibrate the current")
        print("Enter high current calibration value (A):")
        current = input("> ")
        try:
            self.current = float(current)
        except:
            print("The input parameter shall be a float value")
            logger.info("User typed a wrong value")
            return
        print()
        logger.info(f"Setting low current calibration to {voltage} V")
        device.calibrate_current(self.current, "upper")


choices_available = [
    EvaluateDevice,
    StopDevice,
    StartDevice,
    ContinuousRead,
    ContinuousReadDuringTest,
    StopTest,
    ConstantCurrentDischarge,
    ConstantPowerDischarge,
    NimhCharge,
    NicdCharge,
    LiionCharge,
    LifeCharge,
    VrlaCharge,
    CvCharge,
    ResistanceMeasurement,
    LowVoltageCalibration,
    HighVoltageCalibration,
    LowCurrentCalibration,
    HighCurrentCalibration,
    ]

if __name__ == "__main__":
    
    try:
        with Zketech(com_port) as zk:
            pass
    except:
        print(f"Could not open serial port at address '{com_port}'")
        sys.exit()
    
    with Zketech(com_port) as zk, SafetyWatcher() as sw:
        
        try:
            while True:
                
                print()
                
                print("Type function number:")
                for i, c in enumerate(choices_available):
                    print(f"{i}: {c.prompt}")
                func_id = input("> ")
                try:
                    choice_made = choices_available[int(func_id)]
                except TypeError:
                    print("Function number shall be an integer")
                    continue
                except ValueError:
                    print("Function number shall be an integer")
                    continue
                except IndexError:
                    print("Function number shall be in the available list")
                    continue
                try:
                    print()
                    choice_made(zk, sw)
                except KeyboardInterrupt:
                    pass
                except ZketechParametersError:
                    print("The function was requested with an improper parameter")
                
        except KeyboardInterrupt:
            pass

