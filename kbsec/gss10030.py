from __future__ import annotations
from typing import Any, Dict

from .client import KBSecClient

_USA_EXCHANGE_CODES = {"NAS", "AMX", "NYS"}


def _normalize_exchange_code(value: Any) -> str:
    code = str(value or "").strip().upper()
    if code not in _USA_EXCHANGE_CODES:
        raise ValueError("exchange_code must be one of NAS, AMX, or NYS.")
    return code


def _as_number(value: Any) -> str:
    return str(value or "").strip()


def _parse_integer(value: Any) -> str:
    return str(value or "").strip()


def _format_date(value: Any) -> str:
    s = str(value or "").strip()
    if len(s) == 8:
        return f"{s[:4]}-{s[4:6]}-{s[6:]}"
    return s


def _format_compare_code(code: str) -> str:
    mapping = {"1": "상한", "2": "상승", "3": "보합", "4": "하락", "5": "하한"}
    return mapping.get(code, "")


def _format_signed(sign: str, value: str, suffix: str = "") -> str:
    if not value or value in ("0", "0.00", "0.0000"):
        return value + suffix
    return f"{sign}{value}{suffix}"


def get_usa_stock_price(
    client: KBSecClient,
    exchange_code: Any,
    is_cd: Any,
) -> Dict[str, Any]:
    """GSS10030 미국 주식 현재가 조회."""
    krx_cd = _normalize_exchange_code(exchange_code)
    stock_code = str(is_cd or "").strip().upper()
    body = client.request(
        tr_code="GSS10030",
        params={
            "krxCd": krx_cd,
            "_krxCd": " ",
            "isCd": stock_code,
            "_isCd": " ",
        },
        user_id="",
        account_no="",
    )
    compare_code = str(body.get("bdyCmprCcd", "")).strip()
    if compare_code in ("1", "2"):
        sign = "+"
    elif compare_code in ("4", "5"):
        sign = "-"
    else:
        sign = ""
    return {
        "기본정보": {
            "거래소코드": str(body.get("krxCd", krx_cd)).strip(),
            "종목코드": str(body.get("isCd", stock_code)).strip(),
            "영업일자": _format_date(body.get("bsnssDt")),
            "현지일자": _format_date(body.get("dt")),
            "현지시간": str(body.get("tm", "")).strip(),
            "한국일자": _format_date(body.get("korDt")),
            "한국시간": str(body.get("korTm", "")).strip(),
            "현재가": _as_number(body.get("nowPrcP4")),
            "기준가": _as_number(body.get("sprcP4")),
            "전일대비": _format_signed(sign, _as_number(body.get("bdyCmprP4"))),
            "전일대비구분": _format_compare_code(compare_code),
            "등락율": _format_signed(sign, _as_number(body.get("upDwnRP2")), "%"),
            "거래통화": str(body.get("dlCrncy", "")).strip(),
        },
        "당일가격": {
            "시가": _as_number(body.get("opnPrcP4")),
            "고가": _as_number(body.get("hghPrcP4")),
            "저가": _as_number(body.get("lwPrcP4")),
            "상한가": _as_number(body.get("ulmtPrcP4")),
            "하한가": _as_number(body.get("llmtPrcP4")),
            "가중평균가": _as_number(body.get("wtAvrPrcP4")),
        },
        "호가": {
            "매도호가": _as_number(body.get("sAskprcP4")),
            "매수호가": _as_number(body.get("bAskprcP4")),
            "매도호가단위": _as_number(body.get("sAskprcUntP4")),
            "매수호가단위": _as_number(body.get("bAskprcUntP4")),
        },
        "거래정보": {
            "거래량": _parse_integer(body.get("vlm")),
            "거래대금": _parse_integer(body.get("dlTwAmt")),
            "전일거래량": _parse_integer(body.get("bdyVlm")),
            "전일거래대금": _parse_integer(body.get("bdyDlTwAmt")),
            "거래단위": _parse_integer(body.get("dlUnt")),
        },
        "투자지표": {
            "PER": _as_number(body.get("perP4")),
            "EPS": _as_number(body.get("epsP4")),
            "발행주식수": _parse_integer(body.get("isngStkC")),
            "시가총액": _parse_integer(body.get("opnPrcTlAmt")),
        },
        "52주": {
            "최고가": _as_number(body.get("wk52MaxPrcP4")),
            "최저가": _as_number(body.get("wk52MinPrcP4")),
        },
        "원화가격": {
            "현재가": _as_number(body.get("nowPrcKrwP2")),
            "기준가": _as_number(body.get("sprcKrwP2")),
            "시가": _as_number(body.get("opnPrcKrwP2")),
            "고가": _as_number(body.get("hghPrcKrwP2")),
            "저가": _as_number(body.get("lwPrcKrwP2")),
            "상한가": _as_number(body.get("ulmtPrcKrwP2")),
            "하한가": _as_number(body.get("llmtPrcKrwP2")),
            "전일대비": _format_signed(sign, _as_number(body.get("bdyCmprKrwP2"))),
            "고시환율": _as_number(body.get("ntifExchRP4")),
        },
        "시장상태": {
            "시세구분": str(body.get("mrktPrcClsf", "")).strip(),
            "거래정지구분코드": str(body.get("dlSpsnCcd", "")).strip(),
            "휴장여부": str(body.get("clsdMrktF", "")).strip(),
        },
    }
