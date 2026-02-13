import os
import hmac
import hashlib
import razorpay
from loguru import logger
from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime, timezone
from ..auth_service import get_current_user_id
from ..user_service import user_service
from ..models import (
    CreateOrderRequest, CreateOrderResponse, 
    VerifyPaymentRequest, VerifyPaymentResponse,
    Tier
)

router = APIRouter(prefix="/payment", tags=["Payment"])

# Environment Variables
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

# Price Mapping (in INR)
TIER_PRICES = {
    Tier.TIER_1: 1200,
    Tier.TIER_2: 2500, 
    Tier.TIER_3: 5000,
}

@router.post("/create-order", response_model=CreateOrderResponse)
async def create_order(req: CreateOrderRequest, uid: str = Depends(get_current_user_id)):
    logger.info(f"Initiating order creation for user_id={uid}, plan_id={req.planId}")
    
    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        logger.critical("Razorpay configuration missing on server")
        raise HTTPException(status_code=500, detail="Payment configuration missing on server")

    if req.planId not in TIER_PRICES:
        logger.warning(f"Invalid plan ID requested: {req.planId} by user_id={uid}")
        raise HTTPException(status_code=400, detail="Invalid plan ID")
    
    amount_inr = TIER_PRICES[req.planId]
    amount_paise = amount_inr * 100
    
    client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
    
    # Create Order
    data = {
        "amount": amount_paise,
        "currency": req.currency,
        "receipt": f"receipt_{uid[:8]}_{int(datetime.now().timestamp())}",
        "notes": {
            "planId": req.planId.value,
            "userId": uid
        }
    }
    
    try:
        order = client.order.create(data=data)
        logger.info(f"Razorpay order created successfully: {order['id']} for user_id={uid}")
    except Exception as e:
        logger.exception(f"Failed to create Razorpay order for user_id={uid}: {e}")
        raise HTTPException(status_code=500, detail=f"Razorpay Error: {str(e)}")
        
    return CreateOrderResponse(
        id=order['id'],
        currency=order['currency'],
        amount=order['amount'],
        keyId=RAZORPAY_KEY_ID
    )

@router.post("/verify", response_model=VerifyPaymentResponse)
async def verify_payment(req: VerifyPaymentRequest, uid: str = Depends(get_current_user_id)):
    logger.info(f"Verifying payment for user_id={uid}, order_id={req.razorpay_order_id}")
    
    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
         logger.critical("Razorpay configuration missing on server during verification")
         raise HTTPException(status_code=500, detail="Payment configuration missing on server")
         
    # Logic: Verify Signature
    # hmac_sha256(order_id + "|" + payment_id, secret)
    msg = f"{req.razorpay_order_id}|{req.razorpay_payment_id}"
    
    generated_signature = hmac.new(
        RAZORPAY_KEY_SECRET.encode(),
        msg.encode(),
        hashlib.sha256
    ).hexdigest()
    
    # Use hmac.compare_digest for secure comparison
    if not hmac.compare_digest(generated_signature, req.razorpay_signature):
        logger.warning(f"Invalid payment signature for user_id={uid}, order_id={req.razorpay_order_id}")
        raise HTTPException(status_code=400, detail="Invalid payment signature")
        
    # Logic: Update User Tier
    # Fetch order to get planId from notes to be secure
    client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
    try:
        order = client.order.fetch(req.razorpay_order_id)
        plan_id_str = order.get('notes', {}).get('planId')
        
        if not plan_id_str:
             logger.error(f"Order notes missing planId for order_id={req.razorpay_order_id}")
             raise HTTPException(status_code=400, detail="Order Notes missing planId. Cannot upgrade.")
             
        new_tier = Tier(plan_id_str)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch order details: {str(e)}")


    # Update DB
    try:
        await user_service.update_tier(uid, new_tier, expiry=None)
        logger.info(f"User tier updated to {new_tier} for user_id={uid} after successful payment")
    except Exception as e:
        logger.exception(f"Failed to update user tier in DB for user_id={uid} post-payment: {e}")
        # Even though payment succeeded, we failed to update DB. This is critical.
        # We might want to alert the user or have a reconciliation process.
        # For now, we raise 500 so the client knows something went wrong.
        raise HTTPException(status_code=500, detail="Payment verified but failed to update user profile. Please contact support.")
    
    return VerifyPaymentResponse(
        status="success",
        tier=new_tier,
        updatedAt=datetime.now(timezone.utc)
    )
