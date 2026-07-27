import time
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Callable, Optional

# Import the 4 test suite classes from your project modules
from Test_100baset1 import TestBench100BASET1
from Test_1000baset1 import TestBench1000BASET1
from Test_multigbaset1 import TestBenchMultiGBASET1
from Test_10baset1s import TestBench10BASET1S


@dataclass
class LoopConfig:
    iterations: int = 100                       # Total loops to run
    delay_between_loops_sec: float = 0.5       # Settling delay between cycles
    stop_on_first_failure: bool = False         # Break loop if any test fails
    
    # Active Suite Toggles
    enable_100baset1: bool = True
    enable_1000baset1: bool = True
    enable_multigbaset1: bool = True
    enable_10baset1s: bool = True


@dataclass
class TestStatistics:
    """Tracks live pass/fail statistics across loop cycles."""
    total_cycles_planned: int = 0
    current_cycle: int = 0
    passed_cycles: int = 0
    failed_cycles: int = 0
    total_tests_executed: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    start_time: float = 0.0
    elapsed_time_sec: float = 0.0
    test_breakdown: Dict[str, Dict[str, int]] = field(default_factory=dict)

    @property
    def pass_yield_percent(self) -> float:
        if self.current_cycle == 0:
            return 0.0
        return (self.passed_cycles / self.current_cycle) * 100


class LoopManager:
    """
    Executes selected test suites in a background thread and streams progress
    and statistics to the GUI.
    """
    def __init__(self, serial_port: str = "COM3"):
        self.serial_port = serial_port
        
        # Hardware/Suite Instances
        self.suite_100m: Optional[TestBench100BASET1] = None
        self.suite_1g: Optional[TestBench1000BASET1] = None
        self.suite_multig: Optional[TestBenchMultiGBASET1] = None
        self.suite_10s: Optional[TestBench10BASET1S] = None

        # Threading & Control Flags
        self._thread: Optional[threading.Thread] = None
        self._stop_requested = False
        self._is_running = False

        # Callbacks for GUI Layer
        self.on_log: Optional[Callable[[str], None]] = None
        self.on_progress: Optional[Callable[[TestStatistics], None]] = None
        self.on_complete: Optional[Callable[[TestStatistics], None]] = None

    def initialize_hardware(self):
        """Initializes test suite instances on the specified COM port."""
        self._log(f"Initializing hardware interfaces on {self.serial_port}...")
        try:
            self.suite_100m = TestBench100BASET1(serial_port=self.serial_port)
            self.suite_1g = TestBench1000BASET1(serial_port=self.serial_port)
            self.suite_multig = TestBenchMultiGBASET1(serial_port=self.serial_port)
            self.suite_10s = TestBench10BASET1S(serial_port=self.serial_port)
            self._log("Hardware initialization complete.")
        except Exception as e:
            self._log(f"[ERROR] Failed to connect to hardware: {e}")

    def start_loop(self, config: LoopConfig):
        if self._is_running:
            self._log("[WARNING] Stress test loop is already running.")
            return

        self._stop_requested = False
        self._is_running = True
        self._thread = threading.Thread(target=self._run_loop_process, args=(config,), daemon=True)
        self._thread.start()

    def stop_loop(self):
        if self._is_running:
            self._log("[ACTION] Stop requested by user. Terminating loop after current test...")
            self._stop_requested = True

    def is_running(self) -> bool:
        return self._is_running

    def _run_loop_process(self, config: LoopConfig):
        """Core execution loop running in background thread."""
        stats = TestStatistics(total_cycles_planned=config.iterations, start_time=time.time())
        self._log(f"=== Starting Stress Test Loop ({config.iterations} Iterations) ===")

        for cycle in range(1, config.iterations + 1):
            if self._stop_requested:
                self._log("Loop execution stopped by user command.")
                break

            stats.current_cycle = cycle
            cycle_failed = False
            self._log(f"\n--- Cycle {cycle} / {config.iterations} ---")

            # Collect active test methods for this cycle
            tests_to_run = self._build_execution_list(config)

            for suite_name, test_name, test_method in tests_to_run:
                if self._stop_requested:
                    break

                stats.total_tests_executed += 1
                if suite_name not in stats.test_breakdown:
                    stats.test_breakdown[suite_name] = {"passed": 0, "failed": 0}

                # Execute individual test case
                try:
                    test_method()
                    stats.passed_tests += 1
                    stats.test_breakdown[suite_name]["passed"] += 1
                    self._log(f"  [PASS] {suite_name} -> {test_name}")
                except AssertionError as err:
                    stats.failed_tests += 1
                    stats.test_breakdown[suite_name]["failed"] += 1
                    cycle_failed = True
                    self._log(f"  [FAIL] {suite_name} -> {test_name}: {err}")
                except Exception as sys_err:
                    stats.failed_tests += 1
                    stats.test_breakdown[suite_name]["failed"] += 1
                    cycle_failed = True
                    self._log(f"  [ERROR] {suite_name} -> {test_name} unexpected exception: {sys_err}")

            # Update Cycle Statistics
            if cycle_failed:
                stats.failed_cycles += 1
            else:
                stats.passed_cycles += 1

            stats.elapsed_time_sec = time.time() - stats.start_time

            # Trigger GUI progress callback
            if self.on_progress:
                self.on_progress(stats)

            if cycle_failed and config.stop_on_first_failure:
                self._log("[STOP] Failure detected and 'stop_on_first_failure' is active.")
                break

            time.sleep(config.delay_between_loops_sec)

        self._is_running = False
        stats.elapsed_time_sec = time.time() - stats.start_time
        
        self._log(f"\n=== Stress Test Finished ===")
        self._log(f"Yield: {stats.pass_yield_percent:.2f}% | Passed Cycles: {stats.passed_cycles}/{stats.current_cycle}")

        # Trigger GUI completion callback
        if self.on_complete:
            self.on_complete(stats)

    def _build_execution_list(self, config: LoopConfig) -> List[tuple]:
        """Maps enabled suites to their execution functions."""
        test_list = []

        if config.enable_100baset1 and self.suite_100m:
            test_list.extend([
                ("100BASE-T1", "IOP_31 Baseline", self.suite_100m.test_iop_31_baseline),
                ("100BASE-T1", "IOP_18 Polarity", self.suite_100m.test_iop_18_swapped_polarity),
                ("100BASE-T1", "IOP_32 Open Circuit", self.suite_100m.test_iop_32_open_circuit),
                ("100BASE-T1", "IOP_33 Short Circuit", self.suite_100m.test_iop_33_short_circuit),
                ("100BASE-T1", "IOP_19 Revoke Link", self.suite_100m.test_iop_19_revoke_link_status)
            ])

        if config.enable_1000baset1 and self.suite_1g:
            test_list.extend([
                ("1000BASE-T1", "IOP_16 Link Frame 0", self.suite_1g.test_iop_16_link_integrity_frame0),
                ("1000BASE-T1", "IOP_32 Gigabit Open", self.suite_1g.test_iop_32_gigabit_open_tdr),
                ("1000BASE-T1", "IOP_33 Gigabit Short", self.suite_1g.test_iop_33_gigabit_short_tdr),
                ("1000BASE-T1", "IOP_21 Reset Recovery", self.suite_1g.test_iop_21_dut_reset_recovery)
            ])

        if config.enable_multigbaset1 and self.suite_multig:
            test_list.extend([
                ("MultiGBASE-T1", "BER Threshold Check", self.suite_multig.test_multigbase_ber_threshold),
                ("MultiGBASE-T1", "IOP_22 LP Reset Window", self.suite_multig.test_iop_22_lp_reset_25ms_ignore_and_stability)
            ])

        if config.enable_10baset1s and self.suite_10s:
            test_list.extend([
                ("10BASE-T1S", "PLCA Config & Sync", self.suite_10s.test_plca_config_and_beacon_sync),
                ("10BASE-T1S", "FIB10 Hard Short", self.suite_10s.test_fib10_hard_short),
                ("10BASE-T1S", "FIB12 Hard Open", self.suite_10s.test_fib12_hard_open)
            ])

        return test_list

    def _log(self, message: str):
        """Internal helper to output logs locally and send to GUI callback."""
        timestamped_msg = f"[{time.strftime('%H:%M:%S')}] {message}"
        print(timestamped_msg)
        if self.on_log:
            self.on_log(timestamped_msg)


# --- Standalone Terminal Test Example ---
if __name__ == "__main__":
    # Create manager and initialize mock hardware
    runner = LoopManager(serial_port="COM3")
    runner.initialize_hardware()

    # Define test configuration (e.g., 5 cycles for quick validation)
    loop_cfg = LoopConfig(
        iterations=5,
        delay_between_loops_sec=0.2,
        enable_100baset1=True,
        enable_1000baset1=True,
        enable_multigbaset1=True,
        enable_10baset1s=True
    )

    # Attach simple print callbacks
    runner.on_progress = lambda stats: print(f"--> Live Yield: {stats.pass_yield_percent:.1f}% ({stats.passed_cycles}/{stats.current_cycle} Passed)")
    runner.on_complete = lambda stats: print(f"--> Done in {stats.elapsed_time_sec:.2f}s")

    # Start loop execution
    runner.start_loop(loop_cfg)

    # Keep main thread alive while background thread runs
    while runner.is_running():
        time.sleep(0.5)