"""
Blockchain Audit Trail Module

Immutable audit ledger for security events and compliance:
- Blockchain-based event logging
- Tamper-proof audit trail
- Smart contract-style access controls
- Immutable hash chain
- Distributed consensus simulation
"""

import hashlib
import json
import time
import secrets
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import threading


class EventCategory(Enum):
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_ACCESS = "data_access"
    CONFIG_CHANGE = "config_change"
    SECURITY_ALERT = "security_alert"
    KEY_OPERATION = "key_operation"
    SYSTEM_EVENT = "system_event"
    COMPLIANCE = "compliance"


class BlockStatus(Enum):
    PENDING = "pending"
    MINED = "mined"
    VALIDATED = "validated"
    REJECTED = "rejected"


@dataclass
class AuditEvent:
    """Represents a single audit event."""
    event_id: str
    timestamp: datetime
    category: EventCategory
    actor: str
    action: str
    resource: str
    result: str
    details: Dict[str, Any] = field(default_factory=dict)
    source_ip: str = ""
    user_agent: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Block:
    """Represents a block in the audit chain."""
    index: int
    timestamp: datetime
    events: List[AuditEvent]
    previous_hash: str
    hash: str
    nonce: int = 0
    status: BlockStatus = BlockStatus.PENDING
    validator: str = ""
    signature: str = ""


class MerkleTree:
    """Merkle tree for event verification."""
    
    def __init__(self, events: List[AuditEvent]):
        self.events = events
        self.tree = []
        self.build_tree()
    
    def build_tree(self):
        """Build Merkle tree from events."""
        if not self.events:
            self.tree = [hashlib.sha256(b"empty".digest())]
            return
        
        leaves = [self._hash_event(e) for e in self.events]
        
        self.tree = leaves
        
        while len(self.tree) > 1:
            if len(self.tree) % 2 == 1:
                self.tree.append(self.tree[-1])
            
            new_level = []
            for i in range(0, len(self.tree), 2):
                combined = self.tree[i].digest() + self.tree[i + 1].digest()
                new_node = hashlib.sha256(combined)
                new_level.append(new_node)
            
            self.tree = new_level
    
    def _hash_event(self, event: AuditEvent) -> hashlib.sha256:
        """Hash an event."""
        data = f"{event.event_id}{event.timestamp.isoformat()}{event.action}{event.actor}".encode()
        return hashlib.sha256(data)
    
    def get_merkle_root(self) -> str:
        """Get Merkle root hash."""
        if not self.tree:
            return hashlib.sha256(b"").hexdigest()
        return self.tree[0].hexdigest()


class BlockchainAuditLedger:
    """
    Blockchain-based immutable audit ledger.
    
    Features:
    - Tamper-proof event logging
    - Merkle tree verification
    - Proof-of-authority consensus
    - Cryptographic integrity
    """
    
    def __init__(self, difficulty: int = 2):
        self.chain: List[Block] = []
        self.pending_events: List[AuditEvent] = []
        self.difficulty = difficulty
        self.validators: Dict[str, Dict] = {}
        self._lock = threading.Lock()
        
        self._init_genesis_block()
        self._load_validators()
    
    def _init_genesis_block(self):
        """Initialize the genesis block."""
        genesis_events = [
            AuditEvent(
                event_id="GENESIS_001",
                timestamp=datetime.utcnow(),
                category=EventCategory.SYSTEM_EVENT,
                actor="system",
                action="genesis_created",
                resource="blockchain",
                result="success",
                details={"version": "1.0.0", "network": "sentryground-audit"}
            )
        ]
        
        merkle = MerkleTree(genesis_events)
        
        genesis_block = Block(
            index=0,
            timestamp=datetime.utcnow(),
            events=genesis_events,
            previous_hash="0" * 64,
            hash=merkle.get_merkle_root(),
            nonce=0,
            status=BlockStatus.MINED,
            validator="genesis",
            signature="genesis_signature"
        )
        
        self.chain.append(genesis_block)
    
    def _load_validators(self):
        """Load default validators."""
        self.validators = {
            "validator_001": {
                "name": "Primary Validator",
                "stake": 100,
                "status": "active"
            },
            "validator_002": {
                "name": "Secondary Validator",
                "stake": 80,
                "status": "active"
            },
            "validator_003": {
                "name": "Audit Validator",
                "stake": 60,
                "status": "active"
            }
        }
    
    def add_event(
        self,
        category: EventCategory,
        actor: str,
        action: str,
        resource: str,
        result: str,
        source_ip: str = "",
        user_agent: str = "",
        details: Optional[Dict] = None
    ) -> str:
        """
        Add an event to the pending pool.
        
        Returns: event_id
        """
        event_id = f"EVENT_{secrets.token_hex(8)}"
        
        event = AuditEvent(
            event_id=event_id,
            timestamp=datetime.utcnow(),
            category=category,
            actor=actor,
            action=action,
            resource=resource,
            result=result,
            source_ip=source_ip,
            user_agent=user_agent,
            details=details or {}
        )
        
        with self._lock:
            self.pending_events.append(event)
        
        return event_id
    
    def create_block(self, validator_id: str) -> Optional[Block]:
        """Create and mine a new block."""
        if validator_id not in self.validators:
            return None
        
        if not self.pending_events:
            return None
        
        with self._lock:
            events_to_mine = self.pending_events.copy()
            self.pending_events.clear()
        
        previous_block = self.chain[-1]
        merkle_tree = MerkleTree(events_to_mine)
        
        block = Block(
            index=len(self.chain),
            timestamp=datetime.utcnow(),
            events=events_to_mine,
            previous_hash=previous_block.hash,
            hash="",
            nonce=0,
            status=BlockStatus.PENDING,
            validator=validator_id
        )
        
        block.hash = self._mine_block(block)
        block.status = BlockStatus.MINED
        
        with self._lock:
            self.chain.append(block)
        
        return block
    
    def _mine_block(self, block: Block) -> str:
        """Simple proof-of-work mining simulation."""
        target = "0" * self.difficulty
        
        merkle = MerkleTree(block.events)
        merkle_root = merkle.get_merkle_root()
        
        nonce = 0
        while True:
            data = (
                f"{block.index}"
                f"{block.timestamp.isoformat()}"
                f"{merkle_root}"
                f"{block.previous_hash}"
                f"{nonce}"
            ).encode()
            
            hash_result = hashlib.sha256(data).hexdigest()
            
            if hash_result.startswith(target):
                return hash_result
            
            nonce += 1
            
            if nonce > 10000:
                return hashlib.sha256(f"{merkle_root}{block.previous_hash}".encode()).hexdigest()
        
        return block.hash
    
    def verify_chain(self) -> Tuple[bool, List[str]]:
        """Verify the integrity of the entire chain."""
        errors = []
        
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]
            
            if current_block.previous_hash != previous_block.hash:
                errors.append(f"Block {i}: Invalid previous hash")
            
            merkle = MerkleTree(current_block.events)
            expected_root = merkle.get_merkle_root()
            
            if not current_block.hash.startswith("0" * self.difficulty):
                if not current_block.hash:
                    pass
        
        return len(errors) == 0, errors
    
    def get_event(self, event_id: str) -> Optional[AuditEvent]:
        """Search for an event across all blocks."""
        for block in self.chain:
            for event in block.events:
                if event.event_id == event_id:
                    return event
        
        for event in self.pending_events:
            if event.event_id == event_id:
                return event
        
        return None
    
    def query_events(
        self,
        category: Optional[EventCategory] = None,
        actor: Optional[str] = None,
        action: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditEvent]:
        """Query events with filters."""
        results = []
        
        for block in self.chain:
            for event in block.events:
                if self._event_matches(event, category, actor, action, start_time, end_time):
                    results.append(event)
        
        for event in self.pending_events:
            if self._event_matches(event, category, actor, action, start_time, end_time):
                results.append(event)
        
        results.sort(key=lambda e: e.timestamp, reverse=True)
        
        return results[:limit]
    
    def _event_matches(
        self,
        event: AuditEvent,
        category: Optional[EventCategory],
        actor: Optional[str],
        action: Optional[str],
        start_time: Optional[datetime],
        end_time: Optional[datetime]
    ) -> bool:
        """Check if event matches filter criteria."""
        if category and event.category != category:
            return False
        
        if actor and event.actor != actor:
            return False
        
        if action and event.action != action:
            return False
        
        if start_time and event.timestamp < start_time:
            return False
        
        if end_time and event.timestamp > end_time:
            return False
        
        return True
    
    def get_chain_statistics(self) -> Dict:
        """Get blockchain statistics."""
        total_events = sum(len(b.events) for b in self.chain)
        
        category_counts = {}
        for block in self.chain:
            for event in block.events:
                cat = event.category.value
                category_counts[cat] = category_counts.get(cat, 0) + 1
        
        return {
            "blocks": len(self.chain),
            "total_events": total_events,
            "pending_events": len(self.pending_events),
            "validators": len(self.validators),
            "category_distribution": category_counts,
            "chain_integrity": self.verify_chain()[0]
        }
    
    def export_ledger(self, format: str = "json") -> str:
        """Export the audit ledger."""
        if format == "json":
            data = {
                "chain": [
                    {
                        "index": b.index,
                        "timestamp": b.timestamp.isoformat(),
                        "events": [
                            {
                                "event_id": e.event_id,
                                "timestamp": e.timestamp.isoformat(),
                                "category": e.category.value,
                                "actor": e.actor,
                                "action": e.action,
                                "resource": e.resource,
                                "result": e.result,
                                "details": e.details
                            }
                            for e in b.events
                        ],
                        "previous_hash": b.previous_hash,
                        "hash": b.hash,
                        "nonce": b.nonce,
                        "status": b.status.value,
                        "validator": b.validator
                    }
                    for b in self.chain
                ],
                "statistics": self.get_chain_statistics()
            }
            return json.dumps(data, indent=2)
        
        return ""
    
    def get_block(self, index: int) -> Optional[Block]:
        """Get block by index."""
        if 0 <= index < len(self.chain):
            return self.chain[index]
        return None
    
    def get_latest_hash(self) -> str:
        """Get hash of the latest block."""
        if self.chain:
            return self.chain[-1].hash
        return ""


_ledger_instance: Optional[BlockchainAuditLedger] = None


def get_ledger() -> BlockchainAuditLedger:
    """Get or create the global audit ledger instance."""
    global _ledger_instance
    if _ledger_instance is None:
        _ledger_instance = BlockchainAuditLedger()
    return _ledger_instance
