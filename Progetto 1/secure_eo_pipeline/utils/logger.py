import logging  # For audit trail
import sys  # For stdout

from secure_eo_pipeline import config
from secure_eo_pipeline.db import sqlite_adapter

# =============================================================================
# Logging & Audit Module
# =============================================================================
# PURPOSE:
# In mission-critical systems, "Auditability" is a core security requirement.
# This module creates a permanent record (Audit Trail) of all system events.
#
# SECURITY GOALS:
# 1. Accountability: We can prove who did what and when.
# 2. Incident Response: If a hack occurs, we use logs to reconstruct the timeline.
# 3. Non-repudiation: A user cannot deny an action if it is securely logged.
# =============================================================================

class SQLiteLogHandler(logging.Handler):
    
    """
    Custom logging handler that mirrors audit events into the SQLite database.
    """

    def emit(self, record: logging.LogRecord) -> None:
        try:
            # Best-effort extraction of structured fields from the log record.
            user = getattr(record, "user", None)
            action = getattr(record, "action", None)
            message = self.format(record)
            sqlite_adapter.insert_audit_event(
                level=record.levelname,
                component=record.name,
                details=message,
                user=user,
                action=action,
            )
        except Exception:
            # We deliberately swallow exceptions here to avoid breaking the main
            # application flow if the DB becomes unavailable.
            pass


def setup_logger(name="EO_Pipeline", log_file="audit.log"):
    
    """
    Initializes and configures a standardized logging object.
    
    ARGUMENTS:
        name (str): The logical name of the component being logged.
        log_file (str): The file path where logs should be persisted.
        
    DESIGN RATIONALE:
    We use a unified format so that automated security tools
    can easily parse our logs and alert us of anomalies.
    """
    
    # Create or retrieve a logger instance with the specified name
    logger = logging.getLogger(name)
    
    # Set the global logging sensitivity to INFO.
    # This captures important events (Logins, Successes, Failures) while ignoring
    # low-level DEBUG noise that would clutter the audit trail.
    logger.setLevel(logging.INFO)
    
    # Create the Log Formatting structure.
    # [TIMESTAMP]: When did it happen? (ISO 8601 format)
    # [NAME]: Which system component reported it?
    # [LEVEL]: How serious is it? (INFO, WARNING, ERROR)
    # [MESSAGE]: What actually happened?
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # CRITICAL CHECK: Does the logger already have handlers?
    # This prevents the common bug where logs are printed twice or three times
    # if this setup function is called multiple times during the lifecycle.
    if not logger.handlers:
        # 1. CONSOLE HANDLER (Standard Output)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # 2. FILE HANDLER (Persistent Audit Trail)
        # Security Requirement: Logs must survive system restarts.
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # 3. OPTIONAL SQLITE HANDLER (Structured Security Telemetry)
        # When enabled, every audit event is also mirrored into the SQLite DB.
        if getattr(config, "USE_SQLITE", False):
            sqlite_handler = SQLiteLogHandler()
            sqlite_handler.setFormatter(formatter)
            logger.addHandler(sqlite_handler)
        
    # Return the fully configured logger object to the caller
    return logger

# Create a GLOBAL SINGLETON instance of the audit log.
# This allows any module in the project to simply import 'audit_log' and use it.
# It ensures all parts of the pipeline speak in a consistent format.
audit_log = setup_logger()  # Creates the global `audit_log` instance
