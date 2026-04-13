from pydantic import BaseModel
from decorators.db import database_registry
from utils import get_attrs_formatted
from config import config

"""
--- Entity-Relationship Diagram (ERD) Relationships:
    [Customers] 1 ---* [Reviews] (One-to-Many)
    [Products] * ---* [Reviews] (Many-to-Many)
    [Products] * ---* [Categories] (Many-to-Many)
    [Orders] 1 ---* [Customers] (One-to-Many)
    [Orders] 1 ---* [Addresses] (One-to-Many)
    [Orders] 1 ---* [Payment Methods] (One-to-Many)
    [Order Items] 1 ---* [Orders] (One-to-Many)
    [Order Items] 1 ---* [Products] (One-to-Many)
    [Order Payments] 1 ---* [Orders] (One-to-Many)
    [Order Payments] 1 ---* [Payment Methods] (One-to-Many)
"""

"""
@TODO: The DatabaseRegistry needs to handle constraints for table columns 
       in the data models. Can I reuse pydantic's Field(...)? Also, the id
       field needs to be implicitly unique.
"""

@database_registry(
    config.CUSTOMER_DATABASE,
    table_name="customers", 
    key_field="id",
    autoincrement=True, 
    unique_fields=["email"]
)
class Customer(BaseModel):
    id: int | None=None
    name: str
    email: str
    passwd_hash: str
    created_at: str
    updated_at: str

@database_registry(
    config.CUSTOMER_DATABASE,
    table_name="addresses", 
    key_field="id",
    autoincrement=True, 
)
class Address(BaseModel):
    id: int | None=None
    street: str
    city: str
    state: str
    country: str
    zip_code: str
    is_default: bool
    created_at: str
    updated_at: str
    
@database_registry(
    config.CUSTOMER_DATABASE,
    table_name="products", 
    key_field="id",
    autoincrement=True, 
)
class Product(BaseModel):
    id: int | None=None
    name: str
    description: str
    price: float
    stock: int
    created_at: str
    updated_at: str

@database_registry(
    config.CUSTOMER_DATABASE,
    table_name="payment_methods", 
    key_field="id",
    autoincrement=True, 
)
class PaymentMethod(BaseModel):
    id: int | None=None
    customer_id: int | None=None
    method_name: str
    details: str
    created_at: str
    updated_at: str
    
@database_registry(
    config.CUSTOMER_DATABASE,
    table_name="categories", 
    key_field="id",
    autoincrement=True, 

)
class Category(BaseModel):
    id: int | None=None
    name: str
    parent_category_id: int | None=None
    created_at: str
    updated_at: str
    
@database_registry(
    config.CUSTOMER_DATABASE,
    table_name="tags", 
    key_field="id",
    autoincrement=True, 
)
class Tag(BaseModel):
    id: int | None=None
    name: str
    created_at: str
    updated_at: str
    
@database_registry(
    config.CUSTOMER_DATABASE,
    table_name="product_categories", 
    key_field="id",
    autoincrement=True, 
)
class ProductCategory(BaseModel):
    id: int | None=None
    product_id: int | None=None
    category_id: int | None=None
    created_at: str
    updated_at: str
    
@database_registry(
    config.CUSTOMER_DATABASE,
    table_name="product_tags", 
    key_field="id",
    autoincrement=True, 
)
class ProductTag(BaseModel):
    id: int | None=None
    product_id: int | None=None
    tag_id: int | None=None
    created_at: str
    updated_at: str
    
@database_registry(
    config.CUSTOMER_DATABASE,
    table_name="reviews", 
    key_field="id",
    autoincrement=True, 
)
class Review(BaseModel):
    id: int | None=None
    product_id: int | None=None
    customer_id: int | None=None
    rating: int
    comment: str
    created_at: str
    updated_at: str
    
@database_registry(
    config.CUSTOMER_DATABASE,
    table_name="orders", 
    key_field="id",
    autoincrement=True, 
)
class Order(BaseModel):
    id: int | None=None
    customer_id: int | None=None
    address_id: int | None=None
    payment_method_id: int | None=None
    total_amount: float
    created_at: str
    updated_at: str
    
@database_registry(
    config.CUSTOMER_DATABASE,
    table_name="order_items", 
    key_field="id",
    autoincrement=True, 
)
class OrderItem(BaseModel):
    id: int | None=None
    order_id: int | None=None
    product_id: int | None=None
    quantity: int
    price: float
    created_at: str
    updated_at: str
    
@database_registry(
    config.CUSTOMER_DATABASE,
    table_name="order_payments", 
    key_field="id",
    autoincrement=True,
)
class OrderPayment(BaseModel):
    id: int | None=None
    order_id: int | None=None
    payment_method_id: int | None=None
    amount: float
    created_at: str
    updated_at: str
    