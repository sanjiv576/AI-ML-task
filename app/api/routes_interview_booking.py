from fastapi import APIRouter, HTTPException, status
from app.models.schemas import InterviewBookingSchema
from app.models.database import insert_interview_booking


router = APIRouter(prefix="/api",  tags=["Interview Booking"])


@router.post("/interview_booking", response_model=InterviewBookingSchema,  status_code=status.HTTP_201_CREATED)
async def interview_booking(name: str, email: str, date: str, time: str) -> InterviewBookingSchema:

    user_details = InterviewBookingSchema(
        name=name,
        email=email,
        date=date,
        time=time
    )

    try:
        await insert_interview_booking(user_details)
        return user_details
    except Exception as err:
        raise HTTPException(
            status_code=500, detail=f"Interview booking error: {err}")
