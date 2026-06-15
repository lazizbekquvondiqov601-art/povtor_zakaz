from sqlalchemy import Column, Integer, String, BigInteger, Boolean, Float, DateTime, Date, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class InvitedUser(Base):
    __tablename__ = 'invited_users'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    is_registered = Column(Boolean, default=False)

class Supplier(Base):
    __tablename__ = 'suppliers'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False) 
    telegram_id = Column(BigInteger, unique=True, nullable=False)

class AllowedUser(Base):
    """Tizim yopiq bo'lganda ham kira oladiganlar"""
    __tablename__ = 'allowed_users'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True)

class Admin(Base):
    __tablename__ = 'admins'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)

class Setting(Base):
    __tablename__ = 'settings'
    id = Column(Integer, primary_key=True)
    rule_name = Column(String, unique=True, nullable=False)
    rule_value = Column(Float, nullable=False)

class GeneratedOrder(Base):
    __tablename__ = 'generated_orders'

    id = Column(Integer, primary_key=True, autoincrement=True)
    zakaz_id = Column(String, index=True)
    supplier = Column(String)
    artikul = Column(String)
    category = Column(String)
    subcategory = Column(String)
    shop = Column(String)
    color = Column(String)
    photo = Column(String)
    supply_price = Column(Float, default=0.0)
    quantity = Column(Integer)
    hozirgi_qoldiq = Column(Float)
    prodano = Column(Float)
    days_passed = Column(Integer)
    ortacha_sotuv = Column(Float)
    kutilyotgan_sotuv = Column(Float)
    tovar_holati = Column(String)
    import_date = Column(Date)
    created_at = Column(Date, server_default=func.current_date())
    status = Column(String, default='Kutilmoqda')
    initial_stock = Column(Float) 

class SupplierNameHistory(Base):
    __tablename__ = 'supplier_name_history'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, nullable=False, index=True)
    old_name = Column(String, nullable=False)
    new_name = Column(String, nullable=False)
    change_date = Column(DateTime(timezone=True), server_default=func.now())

class BlockedUser(Base):
    __tablename__ = 'blocked_users'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True)
