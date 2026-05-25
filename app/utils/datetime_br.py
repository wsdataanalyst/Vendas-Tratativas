"""Datas e horários no fuso de Brasília."""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

try:
    TZ_BR = ZoneInfo("America/Sao_Paulo")
except ZoneInfoNotFoundError:
    TZ_BR = timezone(timedelta(hours=-3))


def agora() -> datetime:
    return datetime.now(TZ_BR)


def agora_iso() -> str:
    return agora().strftime("%Y-%m-%d %H:%M:%S")


def formatar(data_str: str | None, com_hora: bool = True) -> str:
    if not data_str:
        return "—"
    try:
        dt = datetime.fromisoformat(data_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=TZ_BR)
        else:
            dt = dt.astimezone(TZ_BR)
        if com_hora:
            return dt.strftime("%d/%m/%Y %H:%M")
        return dt.strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return data_str[:16] if len(data_str) > 16 else data_str
