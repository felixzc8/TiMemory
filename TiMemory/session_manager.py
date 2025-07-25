from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import and_, desc
from .models import Session, Message, Summary
from .schemas.session import (
    Session as SessionSchema, 
    SessionMessage, 
    SessionSummary,
    CreateSessionRequest,
    CreateSessionResponse,
    UpdateSessionRequest
)
from datetime import datetime, timezone
import uuid
import logging

logger = logging.getLogger(__name__)

class SessionManager:
    """Manager for user sessions and message history"""
    
    def __init__(self, db_session_factory=None):
        self.db_session_factory = db_session_factory
    
    def create_session(self, user_id: str, title: Optional[str] = None) -> CreateSessionResponse:
        """Create a new session for the user"""
        with self.db_session_factory() as db:
            try:
                session_id = str(uuid.uuid4())
                
                if not title:
                    title = f"Session {datetime.now(timezone.utc).strftime('%b %d, %Y')}"
                
                session = Session(
                    session_id=session_id,
                    user_id=user_id,
                    title=title
                )
                
                db.add(session)
                db.commit()
                db.refresh(session)
                
                logger.info(f"Created session {session_id} for user {user_id}")
                
                return CreateSessionResponse(
                    session_id=session_id,
                    user_id=user_id,
                    title=title,
                    created_at=session.created_at
                )
            except Exception as e:
                db.rollback()
                logger.error(f"Error creating session for user {user_id}: {e}")
                raise Exception(f"Failed to create session for user {user_id}: {e}")
    
    def get_session(self, session_id: str) -> Optional[SessionSchema]:
        """Get session with all messages"""
        with self.db_session_factory() as db:
            try:
                session = db.query(Session).filter(
                    Session.session_id == session_id
                ).first()
                
                if not session:
                    return None
                
                messages_query = db.query(Message).filter(
                    Message.session_id == session_id
                ).order_by(Message.created_at).all()
                
                messages = [
                    SessionMessage(
                        role=msg.role,
                        content=msg.content,
                        timestamp=msg.created_at
                    ) for msg in messages_query
                ]
                
                return SessionSchema(
                    session_id=session.session_id,
                    user_id=session.user_id,
                    title=session.title,
                    messages=messages,
                    created_at=session.created_at,
                    last_activity=session.last_activity,
                    message_count=len(messages)
                )
            except Exception as e:
                logger.error(f"Error getting session {session_id}: {e}")
                raise Exception(
                    f"Failed to retrieve session {session_id}: {e}"
                )
    
    def get_user_sessions(self, user_id: str) -> List[SessionSummary]:
        """Get list of user's sessions (summaries only)"""
        with self.db_session_factory() as db:
            try:
                sessions = db.query(
                    Session.session_id,
                    Session.user_id,
                    Session.title,
                    Session.created_at,
                    Session.last_activity
                ).filter(Session.user_id == user_id).order_by(desc(Session.last_activity)).all()
                
                summaries = []
                for sess in sessions:
                    message_count = db.query(Message).filter(
                        Message.session_id == sess.session_id
                    ).count()
                    
                    summaries.append(SessionSummary(
                        session_id=sess.session_id,
                        user_id=sess.user_id,
                        title=sess.title,
                        created_at=sess.created_at,
                        last_activity=sess.last_activity,
                        message_count=message_count,
                    ))
                
                return summaries
            except Exception as e:
                logger.error(f"Error getting sessions for user {user_id}: {e}")
                return []
    
    def add_message_to_session(self, session_id: str, role: str, content: str, created_at: datetime) -> bool:
        """Add message to session with explicit timestamp"""
        with self.db_session_factory() as db:
            try:
                session = db.query(Session).filter(
                    Session.session_id == session_id
                ).first()
                
                if not session:
                    logger.warning(f"Session {session_id} not found")
                    return False
                
                message = Message(
                    id=str(uuid.uuid4()),
                    session_id=session_id,
                    role=role,
                    content=content,
                    created_at=created_at
                )
                
                db.add(message)
                session.message_count += 1
                
                db.commit()
                
                logger.info(f"Added {role} message to session {session_id}")
                return True
                
            except Exception as e:
                db.rollback()
                logger.error(f"Error adding message to session {session_id}: {e}")
                return False
    
    def update_session(self, session_id: str, update_data: UpdateSessionRequest) -> bool:
        """Update session metadata"""
        with self.db_session_factory() as db:
            try:
                session = db.query(Session).filter(
                    Session.session_id == session_id
                ).first()
                
                if not session:
                    return False
                
                if update_data.title is not None:
                    session.title = update_data.title
                
                session.last_activity = datetime.now(timezone.utc)
                db.commit()
                
                logger.info(f"Updated session {session_id}")
                return True
                
            except Exception as e:
                db.rollback()
                logger.error(f"Error updating session {session_id}: {e}")
                return False
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session and all its messages"""
        with self.db_session_factory() as db:
            try:
                session = db.query(Session).filter(
                    Session.session_id == session_id
                ).first()
                
                if not session:
                    return False
                
                db.delete(session)
                db.commit()
                
                logger.info(f"Deleted session {session_id}")
                return True
                
            except Exception as e:
                db.rollback()
                logger.error(f"Error deleting session {session_id}: {e}")
                return False
    
    def generate_session_title(self, first_message: str) -> str:
        """Generate a session title from the first message"""
        title = first_message.strip()[:50]
        if len(first_message) > 50:
            title += "..."
        
        title = " ".join(title.split())
        
        return title if title else f"Session {datetime.now(timezone.utc).strftime('%b %d')}"
    
    def get_session_message_context(self, session_id: str, message_limit: int) -> List[Dict[str, str]]:
        """Get the most recent message_limit number of messages from the session."""
        with self.db_session_factory() as db:
            all_messages = db.query(Message).filter(
                Message.session_id == session_id
            ).order_by(Message.created_at).all()
            
            recent_messages = all_messages[-message_limit:] if len(all_messages) > message_limit else all_messages
            
            return [{"role": msg.role, "content": msg.content} for msg in recent_messages]

    def create_summary(self, session_id: str, content: str, vector: List[float], message_count: int) -> bool:
        """Create a new summary record for the session."""
        with self.db_session_factory() as db:
            try:
                summary = Summary(
                    id=str(uuid.uuid4()),
                    session_id=session_id,
                    content=content,
                    vector=vector,
                    message_count_at_creation=message_count
                )
                
                db.add(summary)
                db.commit()
                
                logger.info(f"Created summary for session {session_id} at message count {message_count}")
                return True
            except Exception as e:
                db.rollback()
                logger.error(f"Error creating summary for session {session_id}: {e}")
                return False

    def get_message_count(self, session_id: str) -> int:
        """Get total message count for session."""
        with self.db_session_factory() as db:
            return db.query(Message).filter(Message.session_id == session_id).count()

    def get_session_summary(self, session_id: str) -> Optional[str]:
        """Get current session summary content."""
        latest_summary = self.get_latest_summary(session_id)
        return latest_summary.content if latest_summary else None

    def get_latest_summary(self, session_id: str) -> Optional[Summary]:
        """Get the most recent summary for a session."""
        with self.db_session_factory() as db:
            return db.query(Summary).filter(
                Summary.session_id == session_id
            ).order_by(Summary.created_at.desc()).first()

    def should_generate_summary(self, session_id: str, message_limit: int, summary_threshold: int) -> bool:
        """
        Check if summary should be generated:
        1. Once total message count reaches message_limit, generate first summary
        2. When difference between current count and latest summary's message_count_at_creation >= summary_threshold, generate new summary
        """
        with self.db_session_factory() as db:
            session = db.query(Session).filter(Session.session_id == session_id).first()
            if not session:
                return False
                
            current_count = session.message_count
            
            if current_count < message_limit:
                return False
            
            latest_summary = self.get_latest_summary(session_id)
            
            if latest_summary is None:
                return True
            
            messages_since_last_summary = current_count - latest_summary.message_count_at_creation
            return messages_since_last_summary >= summary_threshold



session_manager = SessionManager()