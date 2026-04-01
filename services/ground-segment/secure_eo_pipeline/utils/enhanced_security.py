"""
Enhanced Security Module for SentryGround-Zero

Features:
- Rate limiting for authentication attempts
- Multi-factor authentication (TOTP)
- Advanced audit logging
- Session management
- IP-based access control
"""

import os
import hashlib
import hmac
import secrets
import time
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from functools import wraps

from secure_eo_pipeline import config


@dataclass
class SecurityEvent:
    timestamp: datetime
    event_type: str
    severity: str
    user: Optional[str]
    source_ip: str
    details: str
    blocked: bool = False


@dataclass
class Session:
    session_id: str
    username: str
    created_at: datetime
    last_activity: datetime
    ip_address: str
    user_agent: str
    mfa_verified: bool = False
    permissions: List[str] = field(default_factory=list)


class RateLimiter:
    """Token bucket rate limiter for authentication attempts."""
    
    def __init__(self, max_attempts: int = 5, window_seconds: int = 300):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: Dict[str, List[float]] = defaultdict(list)
        self._lockouts: Dict[str, float] = {}
    
    def is_allowed(self, identifier: str) -> Tuple[bool, int]:
        """
        Check if request is allowed.
        Returns: (is_allowed, seconds_until_reset)
        """
        now = time.time()
        
        if identifier in self._lockouts:
            lockout_end = self._lockouts[identifier]
            if now < lockout_end:
                return False, int(lockout_end - now)
            else:
                del self._lockouts[identifier]
        
        self._attempts[identifier] = [
            t for t in self._attempts[identifier]
            if now - t < self.window_seconds
        ]
        
        if len(self._attempts[identifier]) >= self.max_attempts:
            self._lockouts[identifier] = now + self.window_seconds
            return False, self.window_seconds
        
        return True, 0
    
    def record_attempt(self, identifier: str, success: bool):
        """Record an authentication attempt."""
        now = time.time()
        
        if not success:
            self._attempts[identifier].append(now)
        else:
            self._attempts[identifier].clear()
            if identifier in self._lockouts:
                del self._lockouts[identifier]


class TOTPAuthenticator:
    """Time-based One-Time Password (TOTP) authenticator."""
    
    def __init__(self, issuer: str = "SentryGround-Zero"):
        self.issuer = issuer
        self._secrets: Dict[str, str] = {}
    
    def generate_secret(self, username: str) -> str:
        """Generate a new TOTP secret for user."""
        secret = secrets.token_hex(20)
        self._secrets[username] = secret
        return secret
    
    def get_provisioning_uri(self, username: str, secret: str) -> str:
        """Get TOTP provisioning URI for authenticator apps."""
        import urllib.parse
        params = urllib.parse.urlencode({
            'secret': secret,
            'issuer': self.issuer,
            'algorithm': 'SHA1',
            'digits': 6,
            'period': 30,
        })
        return f"otpauth://totp/{self.issuer}:{username}?{params}"
    
    def verify(self, username: str, token: str) -> bool:
        """Verify TOTP token."""
        if username not in self._secrets:
            return False
        
        secret = self._secrets[username]
        expected = self._generate_token(secret)
        
        return hmac.compare_digest(token, expected)
    
    def _generate_token(self, secret: str) -> str:
        """Generate current TOTP token."""
        import struct
        import time
        
        counter = struct.pack('>Q', int(time.time()) // 30)
        
        import hashlib
        import hmac
        digest = hmac.new(
            bytes.fromhex(secret),
            counter,
            hashlib.sha1
        ).digest()
        
        offset = digest[-1] & 0x0F
        code = struct.unpack('>I', digest[offset:offset + 4])[0] & 0x7FFFFFFF
        token = str(code % 1000000).zfill(6)
        
        return token


class SessionManager:
    """Secure session management."""
    
    def __init__(self, session_timeout_minutes: int = 60):
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        self._sessions: Dict[str, Session] = {}
        self._user_sessions: Dict[str, List[str]] = defaultdict(list)
    
    def create_session(
        self,
        username: str,
        ip_address: str,
        user_agent: str,
        permissions: List[str]
    ) -> str:
        """Create new session."""
        session_id = secrets.token_urlsafe(32)
        
        session = Session(
            session_id=session_id,
            username=username,
            created_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            ip_address=ip_address,
            user_agent=user_agent,
            permissions=permissions
        )
        
        self._sessions[session_id] = session
        self._user_sessions[username].append(session_id)
        
        self._cleanup_user_sessions(username)
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get session if valid."""
        session = self._sessions.get(session_id)
        
        if not session:
            return None
        
        if datetime.utcnow() - session.last_activity > self.session_timeout:
            self.terminate_session(session_id)
            return None
        
        session.last_activity = datetime.utcnow()
        return session
    
    def terminate_session(self, session_id: str):
        """Terminate a session."""
        session = self._sessions.pop(session_id, None)
        if session:
            self._user_sessions[session.username].remove(session_id)
    
    def terminate_all_user_sessions(self, username: str):
        """Terminate all sessions for a user."""
        session_ids = self._user_sessions.get(username, [])
        for sid in session_ids:
            self._sessions.pop(sid, None)
        self._user_sessions[username] = []
    
    def _cleanup_user_sessions(self, username: str, max_sessions: int = 5):
        """Limit concurrent sessions per user."""
        sessions = self._user_sessions.get(username, [])
        while len(sessions) > max_sessions:
            oldest = sessions.pop(0)
            self._sessions.pop(oldest, None)
    
    def get_active_count(self, username: str) -> int:
        """Get number of active sessions for user."""
        return len(self._user_sessions.get(username, []))


class SecurityAuditor:
    """Advanced security audit logging."""
    
    def __init__(self, log_file: str = "security_audit.log"):
        self.log_file = log_file
        self._logger = logging.getLogger('security')
        self._logger.setLevel(logging.INFO)
        
        handler = logging.FileHandler(log_file)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s'
        ))
        self._logger.addHandler(handler)
    
    def log_event(
        self,
        event_type: str,
        severity: str,
        user: Optional[str],
        source_ip: str,
        details: str,
        blocked: bool = False
    ):
        """Log a security event."""
        event = SecurityEvent(
            timestamp=datetime.utcnow(),
            event_type=event_type,
            severity=severity,
            user=user,
            source_ip=source_ip,
            details=details,
            blocked=blocked
        )
        
        level = {
            'CRITICAL': logging.CRITICAL,
            'HIGH': logging.ERROR,
            'MEDIUM': logging.WARNING,
            'LOW': logging.INFO
        }.get(severity, logging.INFO)
        
        self._logger.log(level, self._format_event(event))
    
    def _format_event(self, event: SecurityEvent) -> str:
        """Format event for logging."""
        return (
            f"EVENT={event.event_type} | "
            f"SEV={event.severity} | "
            f"USER={event.user or 'N/A'} | "
            f"IP={event.source_ip} | "
            f"BLOCKED={event.blocked} | "
            f"DETAILS={event.details}"
        )
    
    def get_recent_events(
        self,
        count: int = 100,
        severity: Optional[str] = None
    ) -> List[SecurityEvent]:
        """Get recent security events."""
        events = []
        
        if not os.path.exists(self.log_file):
            return events
        
        with open(self.log_file, 'r') as f:
            lines = f.readlines()
        
        for line in lines[-count:]:
            if severity and severity not in line:
                continue
            
            try:
                parts = line.strip().split(' | ')
                event = SecurityEvent(
                    timestamp=datetime.fromisoformat(parts[0]),
                    event_type=parts[1].replace('EVENT=', ''),
                    severity=parts[2].replace('SEV=', ''),
                    user=parts[3].replace('USER=', '') if 'USER=' in parts[3] else None,
                    source_ip=parts[4].replace('IP=', ''),
                    blocked='BLOCKED=True' in line,
                    details=parts[-1].replace('DETAILS=', '') if 'DETAILS=' in parts[-1] else ''
                )
                events.append(event)
            except:
                continue
        
        return events


class EnhancedSecurity:
    """
    Enhanced security manager combining all security features.
    """
    
    def __init__(
        self,
        max_auth_attempts: int = 5,
        lockout_duration: int = 300,
        session_timeout: int = 60
    ):
        self.rate_limiter = RateLimiter(max_auth_attempts, lockout_duration)
        self.totp = TOTPAuthenticator()
        self.session_manager = SessionManager(session_timeout)
        self.auditor = SecurityAuditor()
        
        self._trusted_ips: set = set()
        self._blocked_ips: set = set()
    
    def authenticate(
        self,
        username: str,
        password: str,
        ip_address: str,
        user_agent: str,
        access_control
    ) -> Tuple[bool, Optional[str], List[str]]:
        """
        Enhanced authentication with rate limiting and audit.
        
        Returns: (success, session_id, permissions)
        """
        if ip_address in self._blocked_ips:
            self.auditor.log_event(
                'AUTH_BLOCKED_IP',
                'CRITICAL',
                username,
                ip_address,
                'Blocked IP attempted authentication',
                blocked=True
            )
            return False, None, []
        
        allowed, wait_time = self.rate_limiter.is_allowed(ip_address)
        
        if not allowed:
            self.auditor.log_event(
                'AUTH_RATE_LIMITED',
                'HIGH',
                username,
                ip_address,
                f'Rate limited, wait {wait_time}s',
                blocked=True
            )
            return False, None, []
        
        success = access_control.authenticate(username, password)
        
        if success:
            self.rate_limiter.record_attempt(ip_address, True)
            role = access_control.get_role(username)
            permissions = access_control.get_permissions(role)
            
            session_id = self.session_manager.create_session(
                username, ip_address, user_agent, permissions
            )
            
            self.auditor.log_event(
                'AUTH_SUCCESS',
                'LOW',
                username,
                ip_address,
                f'Session {session_id[:8]}... created'
            )
            
            return True, session_id, permissions
        else:
            self.rate_limiter.record_attempt(ip_address, False)
            
            self.auditor.log_event(
                'AUTH_FAILURE',
                'MEDIUM',
                username,
                ip_address,
                'Invalid credentials'
            )
            
            return False, None, []
    
    def verify_session(self, session_id: str) -> Optional[Session]:
        """Verify and return session."""
        session = self.session_manager.get_session(session_id)
        
        if session:
            self.auditor.log_event(
                'SESSION_VALIDATED',
                'LOW',
                session.username,
                session.ip_address,
                'Session validated'
            )
        else:
            self.auditor.log_event(
                'SESSION_INVALID',
                'MEDIUM',
                None,
                'Unknown',
                f'Invalid session attempt: {session_id[:8]}...'
            )
        
        return session
    
    def block_ip(self, ip_address: str, duration_minutes: int = 60):
        """Block an IP address temporarily."""
        self._blocked_ips.add(ip_address)
        
        self.auditor.log_event(
            'IP_BLOCKED',
            'HIGH',
            None,
            ip_address,
            f'IP blocked for {duration_minutes} minutes'
        )
        
        if duration_minutes > 0:
            import threading
            timer = threading.Timer(
                duration_minutes * 60,
                self._unblock_ip,
                args=[ip_address]
            )
            timer.daemon = True
            timer.start()
    
    def _unblock_ip(self, ip_address: str):
        """Unblock an IP address."""
        self._blocked_ips.discard(ip_address)
    
    def get_security_status(self) -> Dict:
        """Get current security status summary."""
        return {
            'blocked_ips': len(self._blocked_ips),
            'active_sessions': len(self.session_manager._sessions),
            'rate_limited_ips': len(self.rate_limiter._lockouts),
            'recent_events': len(self.auditor.get_recent_events(10)),
        }


def require_auth(func):
    """Decorator to require authentication."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        session_id = kwargs.get('session_id')
        
        if not session_id:
            return {'error': 'Authentication required'}
        
        from secure_eo_pipeline.utils.enhanced_security import get_security_manager
        
        sec_mgr = get_security_manager()
        
        session = sec_mgr.session_manager.get_session(session_id)
        if not session:
            return {'error': 'Invalid or expired session'}
        
        kwargs['session'] = session
        return func(*args, **kwargs)
    
    return wrapper


_security_manager: Optional[EnhancedSecurity] = None


def get_security_manager() -> EnhancedSecurity:
    """Get or create security manager singleton."""
    global _security_manager
    if _security_manager is None:
        _security_manager = EnhancedSecurity()
    return _security_manager
