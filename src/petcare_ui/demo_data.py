from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True)
class Customer:
    id: str
    name: str
    phone: str
    address: str


@dataclass(frozen=True)
class Pet:
    name: str
    species: str
    breed: str
    age: int
    owner_id: str


@dataclass(frozen=True)
class Service:
    name: str
    price: int
    description: str


@dataclass(frozen=True)
class Appointment:
    customer_id: str
    pet_name: str
    service_name: str
    when: datetime
    status: str


@dataclass(frozen=True)
class Invoice:
    code: str
    customer_id: str
    pet_name: str
    service_name: str
    total: int
    paid: bool
    created_at: datetime


def seed_demo():
    customers = [
        Customer("KH001", "Nguyễn Thị Lan", "0901234567", "Q. Ninh Kiều, Cần Thơ"),
        Customer("KH002", "Trần Minh Khoa", "0912345678", "Q. Bình Thuỷ, Cần Thơ"),
        Customer("KH003", "Lê Hoàng Yến", "0987654321", "Q. Cái Răng, Cần Thơ"),
        Customer("KH004", "Phạm Quốc Anh", "0934567890", "Q. Ô Môn, Cần Thơ"),
    ]

    pets = [
        Pet("Milu", "Chó", "Poodle", 2, "KH001"),
        Pet("Bông", "Mèo", "Anh lông ngắn", 1, "KH001"),
        Pet("Lucky", "Chó", "Corgi", 3, "KH002"),
        Pet("Mướp", "Mèo", "Ta", 4, "KH003"),
        Pet("Tom", "Mèo", "Maine Coon", 2, "KH004"),
    ]

    services = [
        Service("Tắm rửa", 80000, "Tắm + sấy + vệ sinh tai"),
        Service("Cắt tỉa lông", 120000, "Tỉa gọn + tạo kiểu cơ bản"),
        Service("Spa", 200000, "Spa thư giãn + dưỡng lông"),
        Service("Khám bệnh", 150000, "Khám tổng quát"),
    ]

    now = datetime.now().replace(second=0, microsecond=0)
    appointments = [
        Appointment("KH001", "Milu", "Tắm rửa", now - timedelta(days=1, hours=2), "Hoàn thành"),
        Appointment("KH002", "Lucky", "Cắt tỉa lông", now - timedelta(hours=3), "Đang thực hiện"),
        Appointment("KH003", "Mướp", "Khám bệnh", now + timedelta(hours=2), "Chờ xử lý"),
    ]

    invoices = [
        Invoice("HD0001", "KH001", "Milu", "Tắm rửa", 80000, True, now - timedelta(days=1, hours=1)),
        Invoice("HD0002", "KH002", "Lucky", "Cắt tỉa lông", 120000, False, now - timedelta(hours=2)),
    ]

    return customers, pets, services, appointments, invoices

