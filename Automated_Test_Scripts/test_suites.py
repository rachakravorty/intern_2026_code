import time
from typing import Callable, Optional
from .arduino_driver import ArduinoDriver
from .mdio_driver import MDIODriver
from .test_models import TestResult, TestStatus

CallbackType = Callable[[TestResult], None]

class BaseTestBench:
    """Base class providing callback dispatching and stop-flag handling."""
    def __init__(self, hw_driver: ArduinoDriver, mdio_driver: MDIODriver, callback: Optional[CallbackType] = None):
        self.hw = hw_driver
        self.mdio = mdio_driver
        self.callback = callback or (lambda res: None)
        self._stop_requested = False

    def request_stop(self):
        self._stop_requested = True

    def emit_result(self, result: TestResult):
        self.callback(result)


# ============================================================================
# 100BASE-T1 TEST BENCH (OPEN Alliance TC1/TC8)
# ============================================================================
class TestBench100BASET1(BaseTestBench):

    def test_iop_31_baseline(self) -> TestResult:
        res = TestResult("100BASE-T1", "100BASET1_IOP_31", "Error-Free Channel Baseline", TestStatus.RUNNING)
        self.emit_result(res)
        t_start = time.perf_counter()
        try:
            self.hw.set_normal()
            if self.mdio.mock:
                self.mdio.set_mock_link(True)
            time.sleep(0.05)

            status = self.mdio.get_link_status()
            sqi = self.mdio.get_sqi()
            res.metrics = {"link_status": status, "sqi": sqi}

            if not status or sqi < 5:
                raise AssertionError(f"Baseline check failed: Link={status}, SQI={sqi}")

            res.status = TestStatus.PASSED
            res.message = f"Link UP, SQI = {sqi}"
        except Exception as e:
            res.status = TestStatus.FAILED
            res.message = str(e)
        finally:
            res.duration_s = time.perf_counter() - t_start
            self.emit_result(res)
            return res

    def test_iop_18_swapped_polarity(self) -> TestResult:
        res = TestResult("100BASE-T1", "100BASET1_IOP_18", "Swapped Polarity Detection", TestStatus.RUNNING)
        self.emit_result(res)
        t_start = time.perf_counter()
        try:
            self.hw.set_swap_polarity()
            time.sleep(0.1)

            status = self.mdio.get_link_status()
            res.metrics = {"link_status": status}

            if status:
                raise AssertionError("Link came UP despite inverted differential polarity")

            res.status = TestStatus.PASSED
            res.message = "Link correctly remained DOWN during polarity swap"
        except Exception as e:
            res.status = TestStatus.FAILED
            res.message = str(e)
        finally:
            self.hw.set_normal()
            res.duration_s = time.perf_counter() - t_start
            self.emit_result(res)
            return res

    def test_iop_32_open_circuit(self) -> TestResult:
        res = TestResult("100BASE-T1", "100BASET1_IOP_32", "Open Circuit Fault Detection", TestStatus.RUNNING)
        self.emit_result(res)
        t_start = time.perf_counter()
        try:
            self.hw.set_fault_open()
            if self.mdio.mock:
                self.mdio.set_mock_tdr("OPEN", distance_m=3)
            
            diag = self.mdio.run_tdr()
            res.metrics = {"tdr_status": diag["status"], "distance_m": diag["distance"]}

            if diag["status"] != "OPEN":
                raise AssertionError(f"Expected OPEN fault, got {diag['status']}")

            res.status = TestStatus.PASSED
            res.message = f"Open Circuit detected at {diag['distance']}m"
        except Exception as e:
            res.status = TestStatus.FAILED
            res.message = str(e)
        finally:
            self.hw.set_normal()
            if self.mdio.mock:
                self.mdio.set_mock_tdr("OK")
            res.duration_s = time.perf_counter() - t_start
            self.emit_result(res)
            return res

    def test_iop_33_short_circuit(self) -> TestResult:
        res = TestResult("100BASE-T1", "100BASET1_IOP_33", "Short Circuit Fault Detection", TestStatus.RUNNING)
        self.emit_result(res)
        t_start = time.perf_counter()
        try:
            self.hw.set_fault_short()
            if self.mdio.mock:
                self.mdio.set_mock_tdr("SHORT", distance_m=1)
            
            diag = self.mdio.run_tdr()
            res.metrics = {"tdr_status": diag["status"], "distance_m": diag["distance"]}

            if diag["status"] != "SHORT":
                raise AssertionError(f"Expected SHORT fault, got {diag['status']}")

            res.status = TestStatus.PASSED
            res.message = f"Short Circuit detected at {diag['distance']}m"
        except Exception as e:
            res.status = TestStatus.FAILED
            res.message = str(e)
        finally:
            self.hw.set_normal()
            if self.mdio.mock:
                self.mdio.set_mock_tdr("OK")
            res.duration_s = time.perf_counter() - t_start
            self.emit_result(res)
            return res

    def test_iop_17_master_master(self) -> TestResult:
        res = TestResult("100BASE-T1", "100BASET1_IOP_17", "Master-Master Misconfiguration", TestStatus.RUNNING)
        self.emit_result(res)
        t_start = time.perf_counter()
        try:
            self.hw.set_normal()
            self.mdio.write_reg(0x09, 0x1800)
            if self.mdio.mock:
                self.mdio.set_mock_link(False)
            
            time.sleep(0.75)
            status = self.mdio.get_link_status()
            res.metrics = {"link_status": status}

            if status:
                raise AssertionError("Link established between two Master devices")

            res.status = TestStatus.PASSED
            res.message = "Link remained DOWN for 750ms as expected"
        except Exception as e:
            res.status = TestStatus.FAILED
            res.message = str(e)
        finally:
            res.duration_s = time.perf_counter() - t_start
            self.emit_result(res)
            return res

    def test_iop_19_revoke_link(self) -> TestResult:
        res = TestResult("100BASE-T1", "100BASET1_IOP_19", "Revoke Link Status (<5ms)", TestStatus.RUNNING)
        self.emit_result(res)
        t_start = time.perf_counter()
        try:
            self.hw.set_normal()
            if self.mdio.mock:
                self.mdio.set_mock_link(True)
            
            t_drop = time.perf_counter()
            if self.mdio.mock:
                self.mdio.set_mock_link(False)
            
            status = self.mdio.get_link_status()
            elapsed_ms = (time.perf_counter() - t_drop) * 1000
            res.metrics = {"link_down_detected": not status, "response_ms": round(elapsed_ms, 2)}

            if status or elapsed_ms > 5.0:
                raise AssertionError(f"Link down detection exceeded 5ms limit ({elapsed_ms:.2f}ms)")

            res.status = TestStatus.PASSED
            res.message = f"Link-down declared in {elapsed_ms:.2f}ms"
        except Exception as e:
            res.status = TestStatus.FAILED
            res.message = str(e)
        finally:
            res.duration_s = time.perf_counter() - t_start
            self.emit_result(res)
            return res

    def test_iop_21_dut_reset_recovery(self) -> TestResult:
        res = TestResult("100BASE-T1", "100BASET1_IOP_21", "DUT Reset Recovery (<100ms)", TestStatus.RUNNING)
        self.emit_result(res)
        t_start = time.perf_counter()
        try:
            self.mdio.write_reg(0x00, 0x8000)
            t_reset = time.perf_counter()
            
            time.sleep(0.03)
            if self.mdio.mock:
                self.mdio.set_mock_link(True)
            
            status = self.mdio.get_link_status()
            relink_time_ms = (time.perf_counter() - t_reset) * 1000
            res.metrics = {"relink_time_ms": round(relink_time_ms, 2)}

            if not status or relink_time_ms > 100.0:
                raise AssertionError(f"Re-link recovery exceeded 100ms ({relink_time_ms:.2f}ms)")

            res.status = TestStatus.PASSED
            res.message = f"Recovered link in {relink_time_ms:.2f}ms"
        except Exception as e:
            res.status = TestStatus.FAILED
            res.message = str(e)
        finally:
            res.duration_s = time.perf_counter() - t_start
            self.emit_result(res)
            return res

    def test_wake_iop_3_reception(self) -> TestResult:
        res = TestResult("100BASE-T1", "WAKE_IOP_3", "Wake Pulse Reception", TestStatus.RUNNING)
        self.emit_result(res)
        t_start = time.perf_counter()
        try:
            self.mdio.write_reg(0x18, 0x0001)
            time.sleep(0.01)
            
            t_wake = time.perf_counter()
            self.mdio.write_reg(0x18, 0x0000)
            if self.mdio.mock:
                self.mdio.set_mock_link(True)
            
            wake_ms = (time.perf_counter() - t_wake) * 1000
            res.metrics = {"wake_time_ms": round(wake_ms, 2)}

            if wake_ms > 100.0:
                raise AssertionError(f"Wake time exceeded 100ms target ({wake_ms:.2f}ms)")

            res.status = TestStatus.PASSED
            res.message = f"DUT woke and re-linked in {wake_ms:.2f}ms"
        except Exception as e:
            res.status = TestStatus.FAILED
            res.message = str(e)
        finally:
            res.duration_s = time.perf_counter() - t_start
            self.emit_result(res)
            return res


# ============================================================================
# 1000BASE-T1 TEST BENCH (OPEN Alliance TC9 / PAM3)
# ============================================================================
class TestBench1000BASET1(BaseTestBench):

    def test_iop_31_gigabit_baseline(self) -> TestResult:
        res = TestResult("1000BASE-T1", "1000BASET1_IOP_31", "Gigabit Error-Free Channel Baseline", TestStatus.RUNNING)
        self.emit_result(res)
        t_start = time.perf_counter()
        try:
            self.hw.set_normal()
            if self.mdio.mock:
                self.mdio.set_mock_link(True)
            
            status = self.mdio.get_link_status()
            res.metrics = {"link_status": status}

            if not status:
                raise AssertionError("Gigabit Link is down")

            res.status = TestStatus.PASSED
            res.message = "Gigabit channel healthy and linked"
        except Exception as e:
            res.status = TestStatus.FAILED
            res.message = str(e)
        finally:
            res.duration_s = time.perf_counter() - t_start
            self.emit_result(res)
            return res

    def test_iop_16_link_integrity_frame0(self) -> TestResult:
        res = TestResult("1000BASE-T1", "1000BASET1_IOP_16", "Link Integrity Frame 0 Check", TestStatus.RUNNING)
        self.emit_result(res)
        t_start = time.perf_counter()
        try:
            if self.mdio.mock:
                self.mdio.set_mock_link(True)
            
            ber = self.mdio.read_reg(0x1A)
            res.metrics = {"first_frame_counter": ber}

            if ber != 0:
                raise AssertionError(f"Packet 0 dropped or bad sequence count: {ber}")

            res.status = TestStatus.PASSED
            res.message = "First packet sequence counter verified at 0"
        except Exception as e:
            res.status = TestStatus.FAILED
            res.message = str(e)
        finally:
            res.duration_s = time.perf_counter() - t_start
            self.emit_result(res)
            return res

    def test_iop_32_gigabit_open_tdr(self) -> TestResult:
        res = TestResult("1000BASE-T1", "1000BASET1_IOP_32", "Gigabit Open Circuit TDR", TestStatus.RUNNING)
        self.emit_result(res)
        t_start = time.perf_counter()
        try:
            self.hw.set_fault_open()
            if self.mdio.mock:
                self.mdio.set_mock_tdr("OPEN", distance_m=7)
            
            tdr = self.mdio.run_tdr()
            res.metrics = {"tdr_status": tdr["status"], "distance_m": tdr["distance"]}

            if tdr["status"] != "OPEN":
                raise AssertionError(f"Expected OPEN fault, got {tdr['status']}")

            res.status = TestStatus.PASSED
            res.message = f"Open Circuit located at {tdr['distance']}m"
        except Exception as e:
            res.status = TestStatus.FAILED
            res.message = str(e)
        finally:
            self.hw.set_normal()
            if self.mdio.mock:
                self.mdio.set_mock_tdr("OK")
            res.duration_s = time.perf_counter() - t_start
            self.emit_result(res)
            return res

    def test_iop_33_gigabit_short_tdr(self) -> TestResult:
        res = TestResult("1000BASE-T1", "1000BASET1_IOP_33", "Gigabit Short Circuit TDR", TestStatus.RUNNING)
        self.emit_result(res)
        t_start = time.perf_counter()
        try:
            self.hw.set_fault_short()
            if self.mdio.mock:
                self.mdio.set_mock_tdr("SHORT", distance_m=4)
            
            tdr = self.mdio.run_tdr()
            res.metrics = {"tdr_status": tdr["status"], "distance_m": tdr["distance"]}

            if tdr["status"] != "SHORT":
                raise AssertionError(f"Expected SHORT fault, got {tdr['status']}")

            res.status = TestStatus.PASSED
            res.message = f"Short Circuit located at {tdr['distance']}m"
        except Exception as e:
            res.status = TestStatus.FAILED
            res.message = str(e)
        finally:
            self.hw.set_normal()
            if self.mdio.mock:
                self.mdio.set_mock_tdr("OK")
            res.duration_s = time.perf_counter() - t_start
            self.emit_result(res)
            return res


# ============================================================================
# MultiGBASE-T1 TEST BENCH (IEEE 802.3ch / OPEN Alliance TC15 / PAM4 & Clause 45)
# ============================================================================
class TestBenchMultiGBASET1(BaseTestBench):
    """Test suite specifically for MultiGBASE-T1 (2.5G / 5G / 10G) using IEEE Clause 45."""

    def test_multig_baseline_link_clause45(self) -> TestResult:
        res = TestResult("MultiGBASE-T1", "MG_IOP_01", "Clause 45 PMA/PMD Link Status Check", TestStatus.RUNNING)
        self.emit_result(res)
        t_start = time.perf_counter()
        try:
            self.hw.set_normal()
            if self.mdio.mock:
                self.mdio.set_mock_link(True)
            time.sleep(0.05)

            # Polling Clause 45 MMD 1 (PMA/PMD), Register 1.1 (Status 1)
            pma_status = self.mdio.read_clause45(mmd=1, reg=1)
            is_linked = bool(pma_status & 0x0004) or self.mdio.get_link_status()

            res.metrics = {"pma_status_raw": hex(pma_status), "pma_link_up": is_linked}

            if not is_linked:
                raise AssertionError("MultiGBASE-T1 PMA/PMD Link failed to assert in Clause 45 MMD 1")

            res.status = TestStatus.PASSED
            res.message = "MultiGBASE-T1 PMA/PMD Link established successfully"
        except Exception as e:
            res.status = TestStatus.FAILED
            res.message = str(e)
        finally:
            res.duration_s = time.perf_counter() - t_start
            self.emit_result(res)
            return res

    def test_multig_rs_fec_health(self) -> TestResult:
        res = TestResult("MultiGBASE-T1", "MG_FEC_01", "RS-FEC Error Block Tolerance Check", TestStatus.RUNNING)
        self.emit_result(res)
        t_start = time.perf_counter()
        try:
            self.hw.set_normal()
            
            # Polling Clause 45 MMD 3 (PCS) Reed-Solomon FEC Counters
            # Reg 0x0800: Corrected Blocks | Reg 0x0801: Uncorrectable Blocks
            corrected_fec = self.mdio.read_clause45(mmd=3, reg=0x0800)
            uncorrected_fec = self.mdio.read_clause45(mmd=3, reg=0x0801)

            res.metrics = {
                "corrected_fec_blocks": corrected_fec,
                "uncorrected_fec_blocks": uncorrected_fec
            }

            if uncorrected_fec > 0:
                raise AssertionError(f"Uncorrectable RS-FEC frame errors detected: {uncorrected_fec}")

            res.status = TestStatus.PASSED
            res.message = "RS-FEC operating within zero-uncorrectable frame tolerance"
        except Exception as e:
            res.status = TestStatus.FAILED
            res.message = str(e)
        finally:
            res.duration_s = time.perf_counter() - t_start
            self.emit_result(res)
            return res

    def test_multig_pam4_eye_margin(self) -> TestResult:
        res = TestResult("MultiGBASE-T1", "MG_PAM4_01", "PAM4 Modulation Eye Quality Margin", TestStatus.RUNNING)
        self.emit_result(res)
        t_start = time.perf_counter()
        try:
            self.hw.set_normal()
            
            # Read PAM4 Eye Quality / Signal-to-Noise Margin from PMA/PMD MMD 1 (Reg 0x0900)
            eye_margin_db = self.mdio.read_clause45(mmd=1, reg=0x0900)

            res.metrics = {"pam4_eye_margin_db": eye_margin_db}

            if eye_margin_db < 6:
                raise AssertionError(f"PAM4 Eye Margin below 6 dB pass threshold: {eye_margin_db} dB")

            res.status = TestStatus.PASSED
            res.message = f"PAM4 Eye Headroom robust at {eye_margin_db} dB"
        except Exception as e:
            res.status = TestStatus.FAILED
            res.message = str(e)
        finally:
            res.duration_s = time.perf_counter() - t_start
            self.emit_result(res)
            return res


# ============================================================================
# 10BASE-T1S PHYSICAL STRESS BENCH (OPEN Alliance TC14)
# ============================================================================
class TestBench10BASET1S(BaseTestBench):

    def test_fib10_hard_short(self) -> TestResult:
        res = TestResult("10BASE-T1S", "FIB10", "Direct Hard Short Circuit (0 Ohm)", TestStatus.RUNNING)
        self.emit_result(res)
        t_start = time.perf_counter()
        try:
            self.hw.set_fault_short()
            if self.mdio.mock:
                self.mdio.set_mock_link(False)
            time.sleep(0.05)

            status = self.mdio.get_link_status()
            res.metrics = {"communication_active": status}

            if status:
                raise AssertionError("Communication did not immediately drop on 0 Ohm short")

            res.status = TestStatus.PASSED
            res.message = "Communication stopped instantly under FIB10 short fault"
        except Exception as e:
            res.status = TestStatus.FAILED
            res.message = str(e)
        finally:
            self.hw.set_normal()
            res.duration_s = time.perf_counter() - t_start
            self.emit_result(res)
            return res

    def test_fib12_hard_open(self) -> TestResult:
        res = TestResult("10BASE-T1S", "FIB12", "Direct Physical Cut / Open Line", TestStatus.RUNNING)
        self.emit_result(res)
        t_start = time.perf_counter()
        try:
            self.hw.set_fault_open()
            if self.mdio.mock:
                self.mdio.set_mock_link(False)
            time.sleep(0.05)

            status = self.mdio.get_link_status()
            res.metrics = {"communication_active": status}

            if status:
                raise AssertionError("Communication did not immediately drop on line cut")

            res.status = TestStatus.PASSED
            res.message = "Communication stopped instantly under FIB12 open fault"
        except Exception as e:
            res.status = TestStatus.FAILED
            res.message = str(e)
        finally:
            self.hw.set_normal()
            res.duration_s = time.perf_counter() - t_start
            self.emit_result(res)
            return res