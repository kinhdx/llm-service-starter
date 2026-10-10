from service.redact import luhn_ok, redact


def test_card_number_with_valid_checksum_is_masked():
    r = redact("Số thẻ 4111 1111 1111 1111 bị trừ tiền")
    assert r.text == "Số thẻ [CARD] bị trừ tiền"
    assert r.counts["CARD"] == 1


def test_digit_run_failing_luhn_is_not_called_a_card():
    assert luhn_ok("4111111111111111")
    assert not luhn_ok("4111111111111112")
    assert "[CARD]" not in redact("mã 4111111111111112").text


def test_citizen_and_old_id_numbers():
    r = redact("CCCD 001190012345, CMND cũ 012345678")
    assert r.text == "CCCD [ID_NUMBER], CMND cũ [ID_NUMBER]"


def test_phone_formats():
    r = redact("gọi 0912345678 hoặc +84987654321 hoặc 0912.345.678")
    assert r.text.count("[PHONE]") == 3


def test_email_and_account_after_label():
    r = redact("Email nguyenvana@gmail.com, STK 0123456789")
    assert r.text == "Email [EMAIL], STK [ACCOUNT]"


def test_amounts_and_transaction_codes_are_left_alone():
    text = "Chuyển 15.000.000đ, mã giao dịch FT2610001234, ngày 08/10"
    assert redact(text).text == text
