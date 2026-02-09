import logging
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any

from langchain_core.tools import tool
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.cash_claim import Claim, ClaimItem
from app.services.azure_services import AzureDocumentIntelligenceService

logger = logging.getLogger(__name__)


def _decimal_to_float(obj):
    """Convert Decimal values to float for JSON serialization."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: _decimal_to_float(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_decimal_to_float(i) for i in obj]
    return obj


def get_claim_tools(db: Session, user_id: int) -> list:
    """Factory that returns LangChain tools scoped to a specific user and DB session."""

    @tool
    def create_claim(
        description: str,
        total_amount: float,
        expense_type: str,
        payment_method: str,
        cash_pickup_date: Optional[str] = None,
        cash_hours: Optional[str] = None,
        mpesa_number: Optional[str] = None,
        bank_account: Optional[str] = None,
    ) -> dict:
        """Create a new expense claim with status Open (draft).

        Args:
            description: A brief description of the expense claim.
            total_amount: The total amount for this claim.
            expense_type: Type of expense - one of: MEDICAL, OPERATIONAL, TRAVEL.
            payment_method: Reimbursement method - one of: CASH, MPESA, BANK.
            cash_pickup_date: Date to pick up cash (YYYY-MM-DD format). Required if payment_method is CASH.
            cash_hours: Time slot for cash pickup - MORNING or AFTERNOON. Required if payment_method is CASH.
            mpesa_number: M-Pesa phone number. Required if payment_method is MPESA.
            bank_account: Bank account number. Required if payment_method is BANK.
        """
        # Validate payment details are complete before creating
        if payment_method == "CASH":
            if not cash_pickup_date:
                return {"error": "Cash pickup date is required for CASH payment. Please ask the user for a pickup date."}
            if not cash_hours:
                return {"error": "Cash pickup time (MORNING or AFTERNOON) is required for CASH payment. Please ask the user."}
        elif payment_method == "MPESA":
            if not mpesa_number:
                return {"error": "M-Pesa phone number is required for MPESA payment. Please ask the user."}
        elif payment_method == "BANK":
            if not bank_account:
                return {"error": "Bank account number is required for BANK payment. Please ask the user."}

        claim = Claim(
            user_id=user_id,
            description=description,
            total_amount=total_amount,
            status="Open",
            expense_type=expense_type,
            payment_method=payment_method,
        )

        if payment_method == "CASH":
            try:
                claim.cash_pickup_date = datetime.strptime(cash_pickup_date, "%Y-%m-%d")
            except ValueError:
                pass
            claim.cash_hours = cash_hours
        elif payment_method == "MPESA":
            claim.mpesa_number = mpesa_number
        elif payment_method == "BANK":
            claim.bank_account = bank_account

        db.add(claim)
        db.commit()
        db.refresh(claim)
        logger.info(f"Created claim {claim.id} for user {user_id}")
        return {
            "claim_id": claim.id,
            "description": claim.description,
            "total_amount": float(claim.total_amount),
            "status": claim.status,
            "expense_type": claim.expense_type,
            "payment_method": claim.payment_method,
        }

    @tool
    def add_claim_item(
        claim_id: int,
        merchant_name: str,
        amount: float,
        date: str,
        category: str,
        receipt_image_url: Optional[str] = None,
    ) -> dict:
        """Add a line item to an existing expense claim.

        Args:
            claim_id: The ID of the claim to add the item to.
            merchant_name: The name of the merchant/vendor.
            amount: The expense amount.
            date: The date of the expense in YYYY-MM-DD format.
            category: The expense category (e.g. meals, transport, accommodation, supplies, other).
            receipt_image_url: Optional URL of the receipt image.
        """
        claim = db.query(Claim).filter(
            Claim.id == claim_id, Claim.user_id == user_id
        ).first()
        if not claim:
            return {"error": f"Claim {claim_id} not found or does not belong to you."}
        if claim.status not in ("draft", "Open"):
            return {"error": f"Claim {claim_id} is already {claim.status} and cannot be modified."}

        try:
            expense_date = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            expense_date = datetime.now()

        item = ClaimItem(
            claim_id=claim_id,
            merchant_name=merchant_name,
            amount=amount,
            date=expense_date,
            category=category,
            receipt_image_url=receipt_image_url,
        )
        db.add(item)

        # Recalculate total
        claim.total_amount = (
            db.query(func.sum(ClaimItem.amount))
            .filter(ClaimItem.claim_id == claim_id)
            .scalar()
            or 0
        ) + amount
        db.commit()
        db.refresh(item)

        return {
            "item_id": item.id,
            "claim_id": claim_id,
            "merchant_name": item.merchant_name,
            "amount": float(item.amount),
            "date": date,
            "category": item.category,
            "new_claim_total": float(claim.total_amount),
        }

    @tool
    def update_claim(
        claim_id: int,
        description: Optional[str] = None,
        expense_type: Optional[str] = None,
        payment_method: Optional[str] = None,
        cash_pickup_date: Optional[str] = None,
        cash_hours: Optional[str] = None,
        mpesa_number: Optional[str] = None,
        bank_account: Optional[str] = None,
        currency: Optional[str] = None,
    ) -> dict:
        """Update an existing Open claim's details.

        Args:
            claim_id: The ID of the claim to update.
            description: New description (optional).
            expense_type: New expense type - MEDICAL, OPERATIONAL, or TRAVEL (optional).
            payment_method: New payment method - CASH, MPESA, or BANK (optional).
            cash_pickup_date: New cash pickup date in YYYY-MM-DD format (optional).
            cash_hours: New cash pickup time - MORNING or AFTERNOON (optional).
            mpesa_number: New M-Pesa phone number (optional).
            bank_account: New bank account number (optional).
            currency: New currency code like KES, USD, EUR (optional).
        """
        claim = db.query(Claim).filter(
            Claim.id == claim_id, Claim.user_id == user_id
        ).first()
        if not claim:
            return {"error": f"Claim {claim_id} not found or does not belong to you."}
        if claim.status not in ("draft", "Open"):
            return {"error": f"Claim {claim_id} is {claim.status} and cannot be modified. Only Open claims can be edited."}

        if description:
            claim.description = description
        if expense_type:
            claim.expense_type = expense_type
        if currency:
            claim.currency = currency
        if payment_method:
            claim.payment_method = payment_method
            if payment_method == "CASH":
                if cash_pickup_date:
                    try:
                        claim.cash_pickup_date = datetime.strptime(cash_pickup_date, "%Y-%m-%d")
                    except ValueError:
                        pass
                if cash_hours:
                    claim.cash_hours = cash_hours
            elif payment_method == "MPESA":
                if mpesa_number:
                    claim.mpesa_number = mpesa_number
            elif payment_method == "BANK":
                if bank_account:
                    claim.bank_account = bank_account

        db.commit()
        db.refresh(claim)
        return {
            "claim_id": claim.id,
            "description": claim.description,
            "total_amount": float(claim.total_amount),
            "currency": claim.currency,
            "status": claim.status,
            "expense_type": claim.expense_type,
            "payment_method": claim.payment_method,
            "message": "Claim updated successfully.",
        }

    @tool
    def update_claim_item(
        item_id: int,
        merchant_name: Optional[str] = None,
        amount: Optional[float] = None,
        date: Optional[str] = None,
        category: Optional[str] = None,
        currency: Optional[str] = None,
    ) -> dict:
        """Update an existing claim item.

        Args:
            item_id: The ID of the item to update.
            merchant_name: New merchant name (optional).
            amount: New amount (optional).
            date: New date in YYYY-MM-DD format (optional).
            category: New category (optional).
            currency: New currency code like KES, USD, EUR (optional).
        """
        item = db.query(ClaimItem).join(Claim).filter(
            ClaimItem.id == item_id, Claim.user_id == user_id
        ).first()
        if not item:
            return {"error": f"Item {item_id} not found or does not belong to you."}
        
        claim = item.claim
        if claim.status not in ("draft", "Open"):
            return {"error": f"Cannot modify items in a {claim.status} claim. Only Open claims can be edited."}

        if merchant_name:
            item.merchant_name = merchant_name
        if amount is not None:
            item.amount = amount
        if date:
            try:
                item.date = datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                pass
        if category:
            item.category = category
        if currency:
            item.currency = currency

        # Recalculate claim total
        claim.total_amount = (
            db.query(func.sum(ClaimItem.amount))
            .filter(ClaimItem.claim_id == claim.id)
            .scalar()
            or 0
        )
        db.commit()
        db.refresh(item)

        return {
            "item_id": item.id,
            "claim_id": claim.id,
            "merchant_name": item.merchant_name,
            "amount": float(item.amount),
            "currency": item.currency,
            "date": item.date.isoformat() if item.date else None,
            "category": item.category,
            "new_claim_total": float(claim.total_amount),
            "message": "Item updated successfully.",
        }

    @tool
    def get_claims(status_filter: Optional[str] = None) -> dict:
        """Get the user's expense claims, optionally filtered by status.

        Args:
            status_filter: Optional status to filter by (Open, Pending Approval, Approved, Rejected). Pass None for all claims.
        """
        query = db.query(Claim).filter(Claim.user_id == user_id)
        if status_filter:
            query = query.filter(Claim.status == status_filter)
        claims = query.order_by(Claim.created_at.desc()).all()

        result = _decimal_to_float([
            {
                "claim_id": c.id,
                "description": c.description,
                "total_amount": float(c.total_amount or 0),
                "currency": c.currency or "KES",
                "status": c.status,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "items_count": len(c.items),
            }
            for c in claims
        ])
        
        return {
            "claims": result,
            "count": len(result),
            "status_filter": status_filter or "all",
        }

    @tool
    def get_claim_detail(claim_id: int) -> dict:
        """Get detailed information about a specific claim including all its line items.

        Args:
            claim_id: The ID of the claim to retrieve.
        """
        claim = db.query(Claim).filter(
            Claim.id == claim_id, Claim.user_id == user_id
        ).first()
        if not claim:
            return {"error": f"Claim {claim_id} not found or does not belong to you."}

        return _decimal_to_float({
            "claim_id": claim.id,
            "description": claim.description,
            "total_amount": float(claim.total_amount or 0),
            "status": claim.status,
            "created_at": claim.created_at.isoformat() if claim.created_at else None,
            "submitted_at": claim.submitted_at.isoformat() if claim.submitted_at else None,
            "approved_at": claim.approved_at.isoformat() if claim.approved_at else None,
            "items": [
                {
                    "item_id": item.id,
                    "merchant_name": item.merchant_name,
                    "amount": float(item.amount),
                    "date": item.date.isoformat() if item.date else None,
                    "category": item.category,
                    "receipt_image_url": item.receipt_image_url,
                }
                for item in claim.items
            ],
        })

    @tool
    def submit_claim(claim_id: int) -> dict:
        """Submit a draft claim for approval. The claim must have at least one item.

        Args:
            claim_id: The ID of the draft claim to submit.
        """
        claim = db.query(Claim).filter(
            Claim.id == claim_id, Claim.user_id == user_id
        ).first()
        if not claim:
            return {"error": f"Claim {claim_id} not found or does not belong to you."}
        if claim.status not in ("draft", "Open"):
            return {"error": f"Claim {claim_id} is already {claim.status}."}
        if not claim.items:
            return {"error": "Cannot submit a claim with no items. Please add at least one expense item first."}

        claim.status = "Pending Approval"
        claim.submitted_at = datetime.utcnow()
        db.commit()

        return {
            "claim_id": claim.id,
            "status": "Pending Approval",
            "submitted_at": claim.submitted_at.isoformat(),
            "total_amount": float(claim.total_amount or 0),
            "message": "Claim submitted successfully and is now Pending Approval.",
        }

    @tool
    def extract_receipt(image_url: str) -> dict:
        """Extract merchant name, amount, date, and line items from a receipt image using OCR.

        Args:
            image_url: The URL of the receipt image to process.
        """
        try:
            service = AzureDocumentIntelligenceService()
            if not service.client:
                return {"error": "Receipt extraction service is not configured."}

            # Call the sync extraction directly (avoids issues with nested event loops)
            raw_result = service._sync_extract_receipt(image_url)

            # Process the raw Azure result the same way as the async method
            extracted_data = {
                "merchant_name": "",
                "total_amount": 0.0,
                "date": datetime.now().isoformat(),
                "items": [],
                "tax_amount": 0.0,
            }
            for receipt in raw_result.documents:
                merchant_name = receipt.fields.get("MerchantName")
                if merchant_name:
                    extracted_data["merchant_name"] = merchant_name.value_string
                transaction_date = receipt.fields.get("TransactionDate")
                if transaction_date:
                    extracted_data["date"] = transaction_date.value_date.isoformat()
                total = receipt.fields.get("Total")
                if total:
                    extracted_data["total_amount"] = float(total.value_currency.amount)
                tax = receipt.fields.get("TotalTax")
                if tax:
                    extracted_data["tax_amount"] = float(tax.value_currency.amount)
                if receipt.fields.get("Items"):
                    items = []
                    for item in receipt.fields["Items"].value_array:
                        item_data = {}
                        desc = item.value_object.get("Description")
                        if desc:
                            item_data["name"] = desc.value_string
                        price = item.value_object.get("TotalPrice")
                        if price:
                            item_data["price"] = float(price.value_currency.amount)
                        qty = item.value_object.get("Quantity")
                        if qty:
                            item_data["quantity"] = qty.value_number
                        items.append(item_data)
                    extracted_data["items"] = items

            return _decimal_to_float(extracted_data)
        except Exception as e:
            logger.error(f"Receipt extraction failed: {e}")
            return {"error": f"Failed to extract receipt data: {str(e)}"}

    @tool
    def query_claims_analytics(
        query_type: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        category: Optional[str] = None,
    ) -> dict:
        """Run analytics queries on the user's expense claims.

        Args:
            query_type: Type of analytics query. One of: total_spend, by_category, by_merchant, by_status.
            start_date: Optional start date filter in YYYY-MM-DD format.
            end_date: Optional end date filter in YYYY-MM-DD format.
            category: Optional category filter.
        """
        base_query = db.query(ClaimItem).join(Claim).filter(Claim.user_id == user_id)

        if start_date:
            try:
                base_query = base_query.filter(
                    ClaimItem.date >= datetime.strptime(start_date, "%Y-%m-%d")
                )
            except ValueError:
                pass
        if end_date:
            try:
                base_query = base_query.filter(
                    ClaimItem.date <= datetime.strptime(end_date, "%Y-%m-%d")
                )
            except ValueError:
                pass
        if category:
            base_query = base_query.filter(ClaimItem.category == category)

        if query_type == "total_spend":
            total = base_query.with_entities(func.sum(ClaimItem.amount)).scalar() or 0
            count = base_query.count()
            return {"total_spend": float(total), "item_count": count}

        elif query_type == "by_category":
            rows = (
                base_query.with_entities(
                    ClaimItem.category, func.sum(ClaimItem.amount), func.count()
                )
                .group_by(ClaimItem.category)
                .all()
            )
            return {
                "breakdown": [
                    {"category": r[0] or "uncategorized", "total": float(r[1]), "count": r[2]}
                    for r in rows
                ]
            }

        elif query_type == "by_merchant":
            rows = (
                base_query.with_entities(
                    ClaimItem.merchant_name, func.sum(ClaimItem.amount), func.count()
                )
                .group_by(ClaimItem.merchant_name)
                .all()
            )
            return {
                "breakdown": [
                    {"merchant": r[0] or "unknown", "total": float(r[1]), "count": r[2]}
                    for r in rows
                ]
            }

        elif query_type == "by_status":
            rows = (
                db.query(Claim.status, func.sum(Claim.total_amount), func.count())
                .filter(Claim.user_id == user_id)
                .group_by(Claim.status)
                .all()
            )
            return {
                "breakdown": [
                    {"status": r[0], "total": float(r[1] or 0), "count": r[2]}
                    for r in rows
                ]
            }

        return {"error": f"Unknown query_type: {query_type}. Use one of: total_spend, by_category, by_merchant, by_status."}

    return [
        create_claim,
        add_claim_item,
        update_claim,
        update_claim_item,
        get_claims,
        get_claim_detail,
        submit_claim,
        extract_receipt,
        query_claims_analytics,
    ]
