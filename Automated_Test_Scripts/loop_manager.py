import time
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Callable, Optional, Tuple

from .arduino_driver import ArduinoDriver
from .mdio_driver import MDIODriver
from .test_models import TestResult, TestStatus
from .test_suites import (
    TestBench10BASET1S,
    TestBench100BASET1,
    TestBench1000BASET1,
    TestBenchMultiGBASET1,
)

@dataclass
class LoopConfig:
    iterations: int = 10
    delay_between_loops_sec: float = 0.1
    stop_on_first_failure: bool = False
    enable_10baset1s: bool = True
    enable_100baset1: bool = True
    enable_1000baset1: bool = True
    enable_multigbaset1: bool = True

@dataclass
class TestStatistics:
    total_cycles_planned: int = 0
    current_cycle: int = 0
    passed_cycles: int = 0
    failed_cycles: int = 0
    total_tests_executed: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    start_time: float = 0.0
    elapsed_time_sec: float = 0.0

    @property
    def pass_yield_percent(self) -> float:
        if self.current_cycle == 0:
            return 0.0
        return (self.passed_cycles / self.current_cycle) * 100

class LoopManager:
    """Controls background execution for tests and sends streams to the GUI."""
    def __init__(self, serial_port: str = "COM3"):
        self.serial_port = serial_port
        self.hw: Optional[ArduinoDriver] = None
        self.mdio: Optional[MDIODriver] = None
        
        self.suite_10m: Optional[TestBench10BASET1S] = None
        self.suite_100m: Optional[TestBench100BASET1] = None
        self.suite_1g: Optional[TestBench1000BASET1] = None
        self.suite_multig: Optional[TestBenchMultiGBASET1] = None

        self._thread: Optional[threading.Thread] = None
        self._stop_requested = False
        self._is_running = False

        # Callbacks for GUI
        self.on_log: Optional[Callable[[str], None]] = None
        self.on_result: Optional[Callable[[TestResult], None]] = None
        self.on_progress: Optional[Callable[[TestStatistics], None]] = None
        self.on_complete: Optional[Callable[[TestStatistics], None]] = None

    def initialize_hardware(self) -> bool:
        """Instantiates shared hardware and links callbacks to test benches."""
        self._log(f"Initializing hardware on {self.serial_port}...")
        try:
            self.hw = ArduinoDriver(port=self.serial_port)
            self.mdio = MDIODriver(phy_addr=1, mock=True)
            
            # Pass shared drivers and GUI result callback to all test suites
            self.suite_10m = TestBench10BASET1S(self.hw, self.mdio, callback=self.on_result)
            self.suite_100m = TestBench100BASET1(self.hw, self.mdio, callback=self.on_result)
            self.suite_1g = TestBench1000BASET1(self.hw, self.mdio, callback=self.on_result)
            self.suite_multig = TestBenchMultiGBASET1(self.hw, self.mdio, callback=self.on_result)
            
            self._log("Hardware initialized successfully.")
            return True
        except Exception as e:
            self._log(f"[ERROR] Failed hardware init: {e}")
            return False

    def start_loop(self, config: LoopConfig):
        if self._is_running:
            return
        self._stop_requested = False
        self._is_running = True
        self._thread = threading.Thread(target=self._run_loop_process, args=(config,), daemon=True)
        self._thread.start()

    def stop_loop(self):
        self._stop_requested = True

    def is_running(self) -> bool:
        return self._is_running

    def _run_loop_process(self, config: LoopConfig):
        suite_map = self._build_suite_map(config)
        total_enabled_standards = len(suite_map)
        
        # Calculate total cycles across all enabled standards sequentially
        total_cycles_planned = total_enabled_standards * config.iterations
        stats = TestStatistics(total_cycles_planned=total_cycles_planned, start_time=time.time())

        overall_cycle_counter = 0

        # Outer Loop: Run sequentially through each enabled Ethernet standard
        for suite_name, test_methods in suite_map:
            if self._stop_requested:
                break

            self._log(f"=== Starting Test Block: {suite_name} ({config.iterations} iterations) ===")

            # Inner Loop: Repeat tests for the active standard for all requested iterations
            for cycle_in_suite in range(1, config.iterations + 1):
                if self._stop_requested:
                    break

                overall_cycle_counter += 1
                stats.current_cycle = overall_cycle_counter
                cycle_failed = False

                for s_name, test_name, test_method in test_methods:
                    if self._stop_requested:
                        break

                    stats.total_tests_executed += 1
                    result: TestResult = test_method()

                    if result.status == TestStatus.PASSED:
                        stats.passed_tests += 1
                        self._log(f"  [PASS] {s_name} -> {test_name}")
                    else:
                        stats.failed_tests += 1
                        cycle_failed = True
                        self._log(f"  [FAIL] {s_name} -> {test_name}: {result.message}")

                if cycle_failed:
                    stats.failed_cycles += 1
                else:
                    stats.passed_cycles += 1

                stats.elapsed_time_sec = time.time() - stats.start_time

                if self.on_progress:
                    self.on_progress(stats)

                if cycle_failed and config.stop_on_first_failure:
                    self._log(f"Stopping loop early due to failure in {suite_name} at cycle {cycle_in_suite}.")
                    break

                time.sleep(config.delay_between_loops_sec)

            if cycle_failed and config.stop_on_first_failure:
                break

        self._is_running = False
        if self.on_complete:
            self.on_complete(stats)

    def _build_suite_map(self, config: LoopConfig) -> List[Tuple[str, List[Tuple]]]:
        """Groups test cases by their Ethernet standard."""
        suite_map = []

        if config.enable_10baset1s and self.suite_10m:
            suite_map.append((
                "10BASE-T1S", [
                    ("10BASE-T1S", "FIB10 Hard Short", self.suite_10m.test_fib10_hard_short),
                    ("10BASE-T1S", "FIB12 Hard Open", self.suite_10m.test_fib12_hard_open),
                ]
            ))

        if config.enable_100baset1 and self.suite_100m:
            suite_map.append((
                "100BASE-T1", [
                    ("100BASE-T1", "IOP_31 Baseline", self.suite_100m.test_iop_31_baseline),
                    ("100BASE-T1", "IOP_32 Open Circuit", self.suite_100m.test_iop_32_open_circuit),
                ]
            ))

        if config.enable_1000baset1 and self.suite_1g:
            suite_map.append((
                "1000BASE-T1", [
                    ("1000BASE-T1", "IOP_32 Gigabit Open", self.suite_1g.test_iop_32_gigabit_open_tdr),
                ]
            ))

        if config.enable_multigbaset1 and self.suite_multig:
            suite_map.append((
                "MultiGBASE-T1", [
                    ("MultiGBASE-T1", "Clause 45 Link Check", self.suite_multig.test_multig_baseline_link_clause45),
                    ("MultiGBASE-T1", "RS-FEC Health", self.suite_multig.test_multig_rs_fec_health),
                    ("MultiGBASE-T1", "PAM4 Eye Margin", self.suite_multig.test_multig_pam4_eye_margin),
                ]
            ))

        return suite_map

    def _log(self, message: str):
        msg = f"[{time.strftime('%H:%M:%S')}] {message}"
        print(msg)
        if self.on_log:
            self.on_log(msg)