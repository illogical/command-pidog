from fastapi import APIRouter, Request

from ..models.sensors import DistanceReading, IMUData, SensorData, SoundReading, TouchReading

router = APIRouter(prefix="/sensors", tags=["Sensors"])


def _get_service(request: Request):
    return request.app.state.pidog


@router.get("/all", response_model=SensorData)
async def get_all_sensors(request: Request):
    """Get all sensor readings in a single response."""
    return _get_service(request).get_sensor_data()


@router.get("/distance", response_model=DistanceReading)
async def get_distance(request: Request):
    """Get ultrasonic distance reading in centimeters."""
    service = _get_service(request)
    return DistanceReading(distance=round(service.dog.read_distance(), 2))


@router.get("/imu", response_model=IMUData)
async def get_imu(request: Request):
    """Get IMU pitch and roll angles in degrees."""
    service = _get_service(request)
    return IMUData(
        pitch=round(service.dog.pitch, 2),
        roll=round(service.dog.roll, 2),
    )


@router.get("/touch", response_model=TouchReading)
async def get_touch(request: Request):
    """Get touch sensor state: N (none), L (left/rear), R (right/front), LS/RS (slide)."""
    service = _get_service(request)
    state = "N"
    if hasattr(service.dog, "dual_touch"):
        state = service.dog.dual_touch.read()
    return TouchReading(state=state)


@router.get("/sound", response_model=SoundReading)
async def get_sound(request: Request):
    """Get sound direction sensor reading."""
    service = _get_service(request)
    detected = False
    direction = -1
    if hasattr(service.dog, "ears"):
        detected = service.dog.ears.isdetected()
        if detected:
            direction = service.dog.ears.read()
    return SoundReading(direction=direction, detected=detected)
