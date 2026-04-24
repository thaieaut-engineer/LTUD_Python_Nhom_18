"""Domain models (dataclass) - dung chung cho DAO & Service & UI."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class User:
    id: int
    role_id: int
    role_name: str
    username: str
    full_name: str
    phone: str | None
    is_active: bool

    @property
    def is_admin(self) -> bool:
        return self.role_name.upper() == "ADMIN"

    @property
    def is_employee(self) -> bool:
        return self.role_name.upper() == "EMPLOYEE"


@dataclass
class Customer:
    id: int
    full_name: str
    phone: str
    address: str | None = None
    email: str | None = None
    created_at: datetime | None = None


@dataclass
class Pet:
    id: int
    customer_id: int
    name: str
    species: str
    breed: str | None = None
    age: int | None = None
    gender: str | None = None
    health_note: str | None = None


@dataclass
class Service:
    id: int
    name: str
    price: Decimal
    description: str | None = None
    duration_min: int | None = None
    is_active: bool = True


@dataclass
class Appointment:
    id: int
    customer_id: int
    pet_id: int
    employee_id: int | None
    scheduled_at: datetime
    status: str
    note: str | None = None


@dataclass
class Invoice:
    id: int
    appointment_id: int
    invoice_no: str
    issued_at: datetime
    subtotal_amount: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    payment_status: str
    note: str | None = None
