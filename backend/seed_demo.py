"""
TrustGuard - Demo Data Seeder

Populates the database with sample verification logs so the dashboard
isn't empty on first load. Run once after starting the server:

    python -m backend.seed_demo
"""

import random
from datetime import datetime, timedelta
from backend.database.session import engine, SessionLocal
from backend.database.models import Base, VerificationLog, AuditLog

# Sample filenames
FILENAMES = [
    "selfie_001.jpg", "profile_photo.png", "id_scan.jpg", "webcam_capture.jpg",
    "upload_face.png", "headshot.jpg", "passport_photo.jpg", "video_frame.jpg",
    "voice_sample.wav", "audio_clip.wav", "recording_01.wav", "mic_input.wav",
]

VERIFICATION_TYPES = [
    "deepfake_image", "deepfake_image", "deepfake_image",  # weighted more common
    "liveness_image", "liveness_image",
    "voice", "voice",
    "behavior",
    "kyc", "kyc",
    "session",
]

def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Check if data already exists
    existing = db.query(VerificationLog).count()
    if existing >= 20:
        print(f"Database already has {existing} records. Skipping seed.")
        db.close()
        return
    print(f"Database has {existing} records. Adding demo data...")

    now = datetime.utcnow()
    logs = []

    for i in range(47):
        vtype = random.choice(VERIFICATION_TYPES)
        is_deepfake = random.random() < 0.15  # ~15% flagged
        confidence = round(random.uniform(0.82, 0.99), 4) if not is_deepfake else round(random.uniform(0.65, 0.95), 4)

        if is_deepfake:
            risk = random.choice(["HIGH", "CRITICAL"])
        elif confidence > 0.90:
            risk = "LOW"
        else:
            risk = random.choice(["LOW", "MEDIUM"])

        processing = round(random.uniform(120, 850), 2)
        created = now - timedelta(hours=random.randint(1, 168))  # last 7 days

        logs.append(VerificationLog(
            verification_type=vtype,
            filename=random.choice(FILENAMES),
            is_deepfake=is_deepfake,
            confidence=confidence,
            risk_level=risk,
            processing_time_ms=processing,
            created_at=created,
        ))

    # Add some audit logs too
    audit_entries = [
        AuditLog(action="seed_demo", details={"records": 47}, created_at=now),
    ]

    db.add_all(logs)
    db.add_all(audit_entries)
    db.commit()
    print(f"Seeded {len(logs)} verification logs.")
    db.close()


if __name__ == "__main__":
    seed()
