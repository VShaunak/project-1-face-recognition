"""Server-side ArcFace/FAISS attendance API; recognition is never decided in the browser."""
from __future__ import annotations
import csv, io, os, secrets, time
from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal
import numpy as np
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, LargeBinary, String, create_engine, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

load_dotenv()

DB_URL=os.getenv("DATABASE_URL","sqlite:///./attendance.db"); SECRET=os.getenv("SECRET_KEY","change-me-in-production")
ADMIN_EMAIL=os.getenv("ADMIN_EMAIL","admin@example.com"); ADMIN_PASSWORD=os.getenv("ADMIN_PASSWORD","ChangeThisAdminPassword1!")
COOLDOWN=float(os.getenv("ATTENDANCE_COOLDOWN_HOURS","8")); THRESHOLD=float(os.getenv("FACE_MATCH_THRESHOLD","0.42"))
engine=create_engine(DB_URL,connect_args={"check_same_thread":False} if DB_URL.startswith("sqlite") else {}); SessionLocal=sessionmaker(bind=engine)
pwd=CryptContext(schemes=["bcrypt"],deprecated="auto"); model=None; proofs={}
class Base(DeclarativeBase): pass
class User(Base):
 __tablename__="users"; id:Mapped[int]=mapped_column(primary_key=True); name:Mapped[str]=mapped_column(String(160)); student_id:Mapped[str]=mapped_column(String(80),unique=True,index=True); email:Mapped[str]=mapped_column(String(254),unique=True,index=True); department:Mapped[str]=mapped_column(String(120)); password_hash:Mapped[str]=mapped_column(String(255)); role:Mapped[str]=mapped_column(String(20),default="user"); is_active:Mapped[bool]=mapped_column(Boolean,default=True); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc)); embeddings:Mapped[list["Embedding"]]=relationship(cascade="all,delete-orphan")
class Embedding(Base):
 __tablename__="face_embeddings"; id:Mapped[int]=mapped_column(primary_key=True); user_id:Mapped[int]=mapped_column(ForeignKey("users.id"),index=True); vector:Mapped[bytes]=mapped_column(LargeBinary); dimensions:Mapped[int]=mapped_column(Integer); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
class Attendance(Base):
 __tablename__="attendance"; id:Mapped[int]=mapped_column(primary_key=True); user_id:Mapped[int]=mapped_column(ForeignKey("users.id"),index=True); checked_in_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc)); checked_out_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True); confidence:Mapped[float]=mapped_column(Float); device:Mapped[str]=mapped_column(String(120)); method:Mapped[str]=mapped_column(String(80),default="arcface+liveness")
class Event(Base):
 __tablename__="recognition_events"; id:Mapped[int]=mapped_column(primary_key=True); user_id:Mapped[int|None]=mapped_column(ForeignKey("users.id"),nullable=True); confidence:Mapped[float]=mapped_column(Float); status:Mapped[str]=mapped_column(String(30)); box:Mapped[str|None]=mapped_column(String(120),nullable=True); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
class Register(BaseModel): name:str=Field(min_length=2); student_id:str=Field(min_length=2); email:EmailStr; department:str=Field(min_length=2); password:str=Field(min_length=10)
class Login(BaseModel): email:EmailStr; password:str
class CheckIn(BaseModel): user_id:int; confidence:float=Field(ge=0,le=1); device:str="browser-webcam"; liveness_token:str
class Proof(BaseModel): challenge_id:str; action:Literal["turn_left","turn_right"]; face_yaw:float
def db_session():
 db=SessionLocal()
 try: yield db
 finally: db.close()
def view(u:User): return {"id":u.id,"name":u.name,"student_id":u.student_id,"email":u.email,"department":u.department,"role":u.role,"is_active":u.is_active,"created_at":u.created_at.isoformat()}
def token(u): return jwt.encode({"sub":str(u.id),"role":u.role,"exp":datetime.now(timezone.utc)+timedelta(hours=12)},SECRET,algorithm="HS256")
def current(req:Request,db:Session=Depends(db_session)):
 auth=req.headers.get("authorization","")
 if not auth.startswith("Bearer "): raise HTTPException(401,"Authentication required")
 try: u=db.get(User,int(jwt.decode(auth[7:],SECRET,algorithms=["HS256"])["sub"]))
 except (JWTError,KeyError,ValueError): raise HTTPException(401,"Invalid or expired token")
 if not u or not u.is_active: raise HTTPException(401,"Account is unavailable")
 return u
def admin(u:User=Depends(current)):
 if u.role!="admin": raise HTTPException(403,"Administrator role required")
 return u
def arcface():
 global model
 if model is None:
  try:
   from insightface.app import FaceAnalysis
   model=FaceAnalysis(name="buffalo_l",providers=["CPUExecutionProvider"]); model.prepare(ctx_id=-1,det_size=(640,640))
  except ImportError as e: raise HTTPException(503,"InsightFace is not installed") from e
  except Exception as e: raise HTTPException(503,f"Face model unavailable: {e}") from e
 return model
async def face_from(file:UploadFile):
 if file.content_type not in {"image/jpeg","image/png","image/webp"}: raise HTTPException(415,"Upload JPEG, PNG, or WebP")
 raw=await file.read()
 if len(raw)>8_000_000: raise HTTPException(413,"Image must be smaller than 8 MB")
 import cv2
 image=cv2.imdecode(np.frombuffer(raw,np.uint8),cv2.IMREAD_COLOR)
 if image is None: raise HTTPException(400,"Invalid image")
 faces=arcface().get(image)
 if len(faces)!=1: raise HTTPException(422,"Exactly one well-lit face must be visible")
 if float(faces[0].det_score)<.70 or min(image.shape[:2])<160: raise HTTPException(422,"Face quality is too low")
 return faces[0]
def norm(x): x=x.astype("float32"); return x/max(float(np.linalg.norm(x)),1e-9)
def closest(db,q):
 rows=db.scalars(select(Embedding)).all()
 if not rows:return None,0.0
 vectors=np.stack([np.frombuffer(r.vector,dtype=np.float32) for r in rows])
 try:
  import faiss
  index=faiss.IndexFlatIP(vectors.shape[1]);index.add(vectors);score,pos=index.search(q[None,:],1); row=rows[int(pos[0][0])]; return db.get(User,row.user_id),float(score[0][0])
 except ImportError:
  scores=vectors@q;row=rows[int(np.argmax(scores))];return db.get(User,row.user_id),float(scores.max())
app=FastAPI(title="Face Recognition + Attendance",version="2.0.0")
app.add_middleware(CORSMiddleware,allow_origins=os.getenv("CORS_ORIGINS","http://localhost:3000,http://127.0.0.1:3000").split(","),allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
@app.on_event("startup")
def start():
 Base.metadata.create_all(engine)
 with SessionLocal() as db:
  if not db.scalar(select(User).where(User.email==ADMIN_EMAIL)): db.add(User(name="System Administrator",student_id="ADMIN-001",email=ADMIN_EMAIL,department="Administration",password_hash=pwd.hash(ADMIN_PASSWORD),role="admin"));db.commit()
@app.get("/health")
def health(): return {"status":"healthy","engine":"ArcFace loaded on first frame"}
@app.post("/auth/register")
def register(p:Register,db:Session=Depends(db_session)):
 if db.scalar(select(User).where((User.email==p.email)|(User.student_id==p.student_id))):raise HTTPException(409,"Email or ID already exists")
 u=User(**p.model_dump(exclude={"password"}),password_hash=pwd.hash(p.password));db.add(u);db.commit();db.refresh(u);return view(u)
@app.post("/auth/login")
def login(p:Login,db:Session=Depends(db_session)):
 u=db.scalar(select(User).where(User.email==p.email))
 if not u or not pwd.verify(p.password,u.password_hash):raise HTTPException(401,"Invalid email or password")
 return {"access_token":token(u),"token_type":"bearer","user":view(u)}
@app.get("/users")
def users(_:User=Depends(admin),db:Session=Depends(db_session)):return [view(u) for u in db.scalars(select(User).order_by(User.name)).all()]
@app.get("/users/{user_id}")
def get_user(user_id:int,_:User=Depends(current),db:Session=Depends(db_session)):
 u=db.get(User,user_id)
 if not u:raise HTTPException(404,"User not found")
 return view(u)
@app.put("/users/{user_id}")
def update(user_id:int,p:Register,_:User=Depends(admin),db:Session=Depends(db_session)):
 u=db.get(User,user_id)
 if not u:raise HTTPException(404,"User not found")
 for k,v in p.model_dump(exclude={"password"}).items():setattr(u,k,v)
 u.password_hash=pwd.hash(p.password);db.commit();return view(u)
@app.delete("/users/{user_id}")
def deactivate(user_id:int,_:User=Depends(admin),db:Session=Depends(db_session)):
 u=db.get(User,user_id)
 if not u:raise HTTPException(404,"User not found")
 u.is_active=False;db.commit();return {"message":"User deactivated"}
@app.post("/face/enroll")
async def enroll(user_id:Annotated[int,Form()],file:UploadFile=File(...),_:User=Depends(admin),db:Session=Depends(db_session)):
 u=db.get(User,user_id)
 if not u:raise HTTPException(404,"User not found")
 f=await face_from(file);v=norm(f.embedding);db.add(Embedding(user_id=u.id,vector=v.tobytes(),dimensions=len(v)));db.commit();count=db.scalar(select(func.count(Embedding.id)).where(Embedding.user_id==u.id));return {"user_id":u.id,"samples_captured":count,"required_samples":10,"complete":count>=10}
@app.post("/face/re-enroll")
async def reenroll(user_id:Annotated[int,Form()],file:UploadFile=File(...),user:User=Depends(admin),db:Session=Depends(db_session)):
 db.query(Embedding).filter(Embedding.user_id==user_id).delete();db.commit();return await enroll(user_id,file,user,db)
@app.post("/face/recognize")
async def recognize(file:UploadFile=File(...),db:Session=Depends(db_session)):
 f=await face_from(file);u,score=closest(db,norm(f.embedding));ok=bool(u and u.is_active and score>=THRESHOLD);db.add(Event(user_id=u.id if ok else None,confidence=score,status="recognized" if ok else "unknown",box=",".join(map(str,f.bbox.astype(int).tolist()))));db.commit();return {"user_id":u.id if ok else None,"name":u.name if ok else "Unknown","student_id":u.student_id if ok else None,"confidence":round(score,4),"is_recognized":ok,"box":f.bbox.astype(int).tolist(),"timestamp":datetime.now(timezone.utc).isoformat()}
@app.post("/liveness/challenge")
def challenge(_:User=Depends(current)):
 i=secrets.token_urlsafe(18);action=secrets.choice(["turn_left","turn_right"]);proofs[i]={"action":action,"expires":time.time()+90};return {"challenge_id":i,"action":action,"notice":"Practical head-turn check, not biometric-security grade."}
@app.post("/liveness/verify")
def verify(p:Proof,_:User=Depends(current)):
 c=proofs.pop(p.challenge_id,None);ok=bool(c and c["expires"]>time.time() and c["action"]==p.action and ((p.action=="turn_left" and p.face_yaw<-.06)or(p.action=="turn_right" and p.face_yaw>.06)))
 if not ok:raise HTTPException(422,"Liveness challenge was not satisfied")
 t=secrets.token_urlsafe(24);proofs[t]={"verified":True,"expires":time.time()+120};return {"liveness_token":t,"verified":True}
@app.post("/attendance/check-in")
def checkin(p:CheckIn,_:User=Depends(current),db:Session=Depends(db_session)):
 proof=proofs.pop(p.liveness_token,None)
 if not proof or not proof.get("verified") or proof["expires"]<time.time():raise HTTPException(422,"Valid liveness verification required")
 old=db.scalar(select(Attendance).where(Attendance.user_id==p.user_id,Attendance.checked_in_at>=datetime.now(timezone.utc)-timedelta(hours=COOLDOWN)).order_by(Attendance.checked_in_at.desc()))
 if old:return {"created":False,"attendance_id":old.id,"reason":"cooldown"}
 r=Attendance(user_id=p.user_id,confidence=p.confidence,device=p.device);db.add(r);db.commit();db.refresh(r);return {"created":True,"attendance_id":r.id,"checked_in_at":r.checked_in_at.isoformat()}
@app.get("/attendance")
def attendance(date:str|None=None,department:str|None=None,search:str|None=None,_:User=Depends(current),db:Session=Depends(db_session)):
 q=select(Attendance,User).join(User).order_by(Attendance.checked_in_at.desc())
 if date:q=q.where(func.date(Attendance.checked_in_at)==date)
 if department:q=q.where(User.department==department)
 if search:q=q.where((User.name.ilike(f"%{search}%"))|(User.student_id.ilike(f"%{search}%")))
 return [{"id":a.id,"user_id":u.id,"name":u.name,"student_id":u.student_id,"department":u.department,"check_in_time":a.checked_in_at.isoformat(),"check_out_time":a.checked_out_at.isoformat() if a.checked_out_at else None,"confidence":a.confidence,"status":"checked_in"}for a,u in db.execute(q).all()]
@app.get("/attendance/export")
def export(_ :User=Depends(current),db:Session=Depends(db_session)):
 rows=attendance(_=_,db=db);out=io.StringIO();w=csv.DictWriter(out,fieldnames=rows[0].keys()if rows else ["id","name"]);w.writeheader();w.writerows(rows);return StreamingResponse(iter([out.getvalue()]),media_type="text/csv",headers={"Content-Disposition":"attachment; filename=attendance.csv"})
@app.get("/analytics")
def analytics(_ :User=Depends(current),db:Session=Depends(db_session)):
 deps=db.execute(select(User.department,func.count(Attendance.id)).join(Attendance).group_by(User.department)).all();events=db.execute(select(Event.status,func.count(Event.id)).group_by(Event.status)).all();return {"registered_users":db.scalar(select(func.count(User.id)).where(User.is_active))or 0,"todays_attendance":db.scalar(select(func.count(Attendance.id)).where(func.date(Attendance.checked_in_at)==datetime.now().date().isoformat()))or 0,"by_department":[{"department":x,"count":y}for x,y in deps],"recognition_events":[{"status":x,"count":y}for x,y in events]}
@app.get("/system/status")
def status(db:Session=Depends(db_session)):
 data=analytics(_=None,db=db);return {"status":"operational",**data,"engine":"ArcFace + FAISS","cooldown_hours":COOLDOWN}
@app.websocket("/ws/recognition")
async def ws(socket:WebSocket):
 await socket.accept()
 try:
  while True:await socket.receive_text();await socket.send_json({"type":"heartbeat","at":datetime.now(timezone.utc).isoformat()})
 except Exception:await socket.close()
