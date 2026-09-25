import uuid
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.billing import PACKAGES, add_credits
from app.config import get_settings
from app.database import get_db
from app.models import CreditTransaction, PaymentOrder, User
from app.schemas import (
    CreditTransactionOut,
    OrderCreate,
    OrderOut,
    PackageOut,
    PaymentConfig,
    PaymentConfigOut,
    PaymentConfirm,
    PaymentResult,
) if False else None  # placeholder removed below
