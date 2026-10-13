"""Equivalent application values on PostgreSQL and SQLite."""

from datetime import timezone
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import BigInteger, DateTime, Numeric
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator):
    """SQLite stores UTC without an offset; always return aware UTC values."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("A timezone-aware timestamp is required")
        value = value.astimezone(timezone.utc)
        return value.replace(tzinfo=None) if dialect.name == "sqlite" else value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class Money(TypeDecorator):
    """Decimal currency values: integer minor units on SQLite, NUMERIC on PG.

    For example, INR 10.05 is stored as integer 1005 in SQLite. SQL SUM
    therefore remains exact, and the ORM/API continue to return Decimal.
    """

    impl = Numeric(12, 2)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(BigInteger() if dialect.name == "sqlite" else Numeric(12, 2))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        value = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if not value.is_finite():
            raise ValueError("Money must be finite")
        return int(value * 100) if dialect.name == "sqlite" else value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        value = Decimal(value)
        if dialect.name == "sqlite":
            value /= 100
        return value.quantize(Decimal("0.01"))
