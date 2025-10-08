from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
import asyncio
import logging

logging.basicConfig(level=logging.INFO)

DATABASE_URL = "sqlite:///events.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    location = Column(String(200), nullable=True)
    owner_email = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    participants = relationship("Participant", back_populates="event", cascade="all, delete-orphan")
    reminders = relationship("Reminder", back_populates="event", cascade="all, delete-orphan")

class Participant(Base):
    __tablename__ = "participants"
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    name = Column(String(200), nullable=True)
    email = Column(String(200), nullable=False)
    status = Column(String(30), default="invited")  
    invited_at = Column(DateTime, default=datetime.utcnow)
    responded_at = Column(DateTime, nullable=True)

    event = relationship("Event", back_populates="participants")

class Reminder(Base):
    __tablename__ = "reminders"
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    minutes_before = Column(Integer, nullable=False)
    sent = Column(Boolean, default=False)

    event = relationship("Event", back_populates="reminders")

class ParticipantCreate(BaseModel):
    name: Optional[str] = None
    email: EmailStr

class ParticipantRead(BaseModel):
    id: int
    name: Optional[str]
    email: EmailStr
    status: str
    invited_at: datetime
    responded_at: Optional[datetime]

    class Config:
        orm_mode = True

class ReminderCreate(BaseModel):
    minutes_before: int = Field(..., ge=0)

class ReminderRead(BaseModel):
    id: int
    minutes_before: int
    sent: bool

    class Config:
        orm_mode = True

class EventCreate(BaseModel):
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    location: Optional[str] = None
    owner_email: Optional[EmailStr] = None
    participants: Optional[List[ParticipantCreate]] = None
    reminders: Optional[List[ReminderCreate]] = None

class EventRead(BaseModel):
    id: int
    title: str
    description: Optional[str]
    start_time: datetime
    end_time: Optional[datetime]
    location: Optional[str]
    owner_email: Optional[EmailStr]
    created_at: datetime
    participants: List[ParticipantRead] = []
    reminders: List[ReminderRead] = []

    class Config:
        orm_mode = True


app = FastAPI(title="Event Planner", version="0.1")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.on_event("startup")
async def on_startup():
  
    Base.metadata.create_all(bind=engine)
  
    loop = asyncio.get_event_loop()
    loop.create_task(reminder_worker())


@app.post("/events", response_model=EventRead)
def create_event(payload: EventCreate, db=Depends(get_db)):
    ev = Event(
        title=payload.title,
        description=payload.description,
        start_time=payload.start_time,
        end_time=payload.end_time,
        location=payload.location,
        owner_email=str(payload.owner_email) if payload.owner_email else None,
    )
    if payload.participants:
        for p in payload.participants:
            ev.participants.append(Participant(name=p.name, email=str(p.email)))
    if payload.reminders:
        for r in payload.reminders:
            ev.reminders.append(Reminder(minutes_before=r.minutes_before))
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev

@app.get("/events", response_model=List[EventRead])
def list_events(skip: int = 0, limit: int = 100, db=Depends(get_db)):
    events = db.query(Event).order_by(Event.start_time).offset(skip).limit(limit).all()
    return events

@app.get("/events/{event_id}", response_model=EventRead)
def get_event(event_id: int, db=Depends(get_db)):
    ev = db.query(Event).filter(Event.id == event_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
    return ev

@app.post("/events/{event_id}/invite", response_model=ParticipantRead)
def invite_participant(event_id: int, payload: ParticipantCreate, db=Depends(get_db)):
    ev = db.query(Event).filter(Event.id == event_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
    p = Participant(name=payload.name, email=str(payload.email), event=ev)
    db.add(p)
    db.commit()
    db.refresh(p)
    
    logging.info(f"Приглашен участник {p.email} на событие {ev.id}")
    return p

@app.post("/events/{event_id}/participants/{participant_id}/respond")
def participant_respond(event_id: int, participant_id: int, status: str = "accepted", db=Depends(get_db)):
    p = db.query(Participant).filter(Participant.id == participant_id, Participant.event_id == event_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Participant not found")
    if status not in ("accepted", "declined", "invited"):
        raise HTTPException(status_code=400, detail="Invalid status")
    p.status = status
    p.responded_at = datetime.utcnow()
    db.commit()
    db.refresh(p)
    logging.info(f"Участник {p.email} ответил: {p.status} на событие {event_id}")
    return {"status": "ok", "participant": ParticipantRead.from_orm(p)}

@app.get("/events/{event_id}/participants", response_model=List[ParticipantRead])
def list_participants(event_id: int, db=Depends(get_db)):
    ev = db.query(Event).filter(Event.id == event_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
    return ev.participants

@app.post("/events/{event_id}/reminders", response_model=ReminderRead)
def add_reminder(event_id: int, payload: ReminderCreate, db=Depends(get_db)):
    ev = db.query(Event).filter(Event.id == event_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
    r = Reminder(event=ev, minutes_before=payload.minutes_before)
    db.add(r)
    db.commit()
    db.refresh(r)
    return r

@app.get("/events/{event_id}/reminders", response_model=List[ReminderRead])
def list_reminders(event_id: int, db=Depends(get_db)):
    ev = db.query(Event).filter(Event.id == event_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
    return ev.reminders


+async def reminder_worker():
+    logging.info("Запущен background worker напоминаний")
+    while True:
+        try:
+            db = SessionLocal()
+            now = datetime.utcnow()
+            
+            reminders = db.query(Reminder).join(Event).filter(Reminder.sent == False).all()
+            for r in reminders:
+                ev = r.event
+                if not ev or not ev.start_time:
+                    continue
+                remind_time = ev.start_time - timedelta(minutes=r.minutes_before)
+               
+                if remind_time <= now <= ev.start_time + timedelta(minutes=1):
+                  
+                    logging.info(f"Напоминание: событие '{ev.title}' начнётся в {ev.start_time.isoformat()} (#{ev.id}); напоминание за {r.minutes_before} минут для {', '.join([p.email for p in ev.participants]) or 'владельца'}")
+                    r.sent = True
+                    db.add(r)
+            db.commit()
+        except Exception as exc:
+            logging.exception("Ошибка в reminder_worker: %s", exc)
+        finally:
+            try:
+                db.close()
+            except:
+                pass
+        await asyncio.sleep(30) 
+
+@app.get("/ping")
+def ping():
+    return {"status": "ok"}
+
+if __name__ == "__main__":
+    import uvicorn
+    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
