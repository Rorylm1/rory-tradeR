from src.trading.doctor import run_doctor


def test_doctor_reports_betfair_and_smarkets():
    report = run_doctor()

    assert any("betfair" in line.lower() for line in report)
    assert any("smarkets" in line.lower() for line in report)
