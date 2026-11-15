from vocalize.audio import is_loud_enough, rms_int16


def test_silence_has_zero_rms():
    assert rms_int16(b"\x00\x00" * 16) == 0


def test_constant_samples_report_their_amplitude():
    chunk = (1000).to_bytes(2, "little", signed=True) * 8
    assert rms_int16(chunk) == 1000


def test_quiet_chunk_is_dropped():
    assert is_loud_enough(b"\x00\x00" * 8, threshold=300) is False
    loud = (1000).to_bytes(2, "little", signed=True) * 8
    assert is_loud_enough(loud, threshold=300) is True
