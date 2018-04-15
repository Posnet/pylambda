from typing import Dict

credential_type = Dict[str, str]
context_type = Dict[str, str]


def init_runtime() -> None:
    pass


def get_remaining_time() -> int:
    pass


def log_bytes(message: str, fileno: int) -> None:
    pass


def log_sb(message: str) -> None:
    pass


def send_console_message(message: str, length: int) -> None:
    pass


def receive_invoke(
) -> (str, int, credential_type, str, context_type, str, str):
    pass


def receive_start() -> (str, str, str, int, credential_type):
    pass


def report_user_init_start() -> None:
    pass


def report_user_init_end() -> None:
    pass


def report_user_invoke_start() -> None:
    pass


def report_user_invoke_end() -> None:
    pass


def report_fault(invoke_id: str, message: str, exception: str,
                 backtrace: str) -> None:
    pass


def report_running(invoke_id: str) -> None:
    pass


def report_done(invoke_id: str, errortype: str, result: str) -> None:

    pass


def report_xray_exception(xray_json: str) -> None:
    pass
