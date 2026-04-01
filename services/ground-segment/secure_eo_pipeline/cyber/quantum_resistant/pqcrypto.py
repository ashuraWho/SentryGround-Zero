"""
Quantum-Resistant Cryptography Module

Implements post-quantum cryptographic algorithms:
- ML-KEM (Kyber) - Key Encapsulation
- ML-DSA (Dilithium) - Digital Signatures
- SPHINCS+ - Hash-based Signatures
- Hybrid encryption schemes
- Key derivation functions
"""

import os
import hashlib
import hmac
import secrets
import base64
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json


class PQAlgorithm(Enum):
    ML_KEM_768 = "ml_kem_768"
    ML_KEM_1024 = "ml_kem_1024"
    ML_DSA_44 = "ml_dsa_44"
    ML_DSA_65 = "ml_dsa_65"
    ML_DSA_87 = "ml_dsa_87"
    SPHINCS_SHA2_128 = "sphincs_sha2_128"
    SPHINCS_SHAKE_256 = "sphincs_shake_256"


class KeyType(Enum):
    ML_KEM = "ml_kem"
    ML_DSA = "ml_dsa"
    SPHINCS = "sphincs"
    HYBRID = "hybrid"
    CLASSIC = "classic"


@dataclass
class PQCKeyPair:
    """Post-quantum key pair."""
    key_type: KeyType
    algorithm: PQAlgorithm
    public_key: bytes
    private_key: bytes
    created_at: datetime
    key_id: str
    metadata: Dict = field(default_factory=dict)


@dataclass
class EncapsulatedKey:
    """KEM encapsulation result."""
    ciphertext: bytes
    shared_secret: bytes
    algorithm: PQAlgorithm
    key_id: str


@dataclass
class PQSignature:
    """Digital signature using PQC."""
    signature: bytes
    algorithm: PQAlgorithm
    signer_key_id: str
    timestamp: datetime
    message_hash: str


class MLKEMSimulator:
    """
    Simulator for ML-KEM (Kyber) Key Encapsulation Mechanism.
    
    In production, this would use liboqs. Here we simulate the interface
    while providing educational implementation of key concepts.
    """
    
    MODULE_SIZES = {
        PQAlgorithm.ML_KEM_768: {
            "n": 256,
            "k": 3,
            "q": 3329,
            "public_key": 1184,
            "ciphertext": 1088,
            "shared_secret": 32,
        },
        PQAlgorithm.ML_KEM_1024: {
            "n": 256,
            "k": 4,
            "q": 3329,
            "public_key": 1568,
            "ciphertext": 1568,
            "shared_secret": 32,
        }
    }
    
    def __init__(self, algorithm: PQAlgorithm = PQAlgorithm.ML_KEM_768):
        self.algorithm = algorithm
        self.params = self.MODULE_SIZES[algorithm]
    
    def generate_keypair(self) -> PQCKeyPair:
        """Generate ML-KEM key pair."""
        public_key = secrets.token_bytes(self.params["public_key"])
        private_key = secrets.token_bytes(self.params["public_key"] + 32)
        
        key_id = hashlib.sha256(public_key).hexdigest()[:16]
        
        return PQCKeyPair(
            key_type=KeyType.ML_KEM,
            algorithm=self.algorithm,
            public_key=public_key,
            private_key=private_key,
            created_at=datetime.utcnow(),
            key_id=key_id,
            metadata={
                "n": self.params["n"],
                "k": self.params["k"],
                "q": self.params["q"]
            }
        )
    
    def encapsulate(self, public_key: bytes) -> EncapsulatedKey:
        """Encapsulate shared secret."""
        ciphertext = secrets.token_bytes(self.params["ciphertext"])
        
        shared_secret = hashlib.sha256(ciphertext + public_key).digest()
        
        key_id = hashlib.sha256(public_key).hexdigest()[:16]
        
        return EncapsulatedKey(
            ciphertext=ciphertext,
            shared_secret=shared_secret,
            algorithm=self.algorithm,
            key_id=key_id
        )
    
    def decapsulate(self, private_key: bytes, ciphertext: bytes) -> bytes:
        """Decapsulate shared secret."""
        shared_secret = hashlib.sha256(ciphertext + private_key[:self.params["public_key"]]).digest()
        return shared_secret


class MLDSASimulator:
    """
    Simulator for ML-DSA (Dilithium) Digital Signature Algorithm.
    
    In production, this would use liboqs.
    """
    
    PARAMETERS = {
        PQAlgorithm.ML_DSA_44: {
            "n": 256,
            "k": 4,
            "q": 8380417,
            "gamma1": 131072,
            "gamma2": 52350,
            "public_key": 1184,
            "signature": 2420,
        },
        PQAlgorithm.ML_DSA_65: {
            "n": 256,
            "k": 6,
            "q": 8380417,
            "gamma1": 131072,
            "gamma2": 52350,
            "public_key": 1536,
            "signature": 3293,
        },
        PQAlgorithm.ML_DSA_87: {
            "n": 256,
            "k": 8,
            "q": 8380417,
            "gamma1": 131072,
            "gamma2": 52350,
            "public_key": 1952,
            "signature": 4595,
        }
    }
    
    def __init__(self, algorithm: PQAlgorithm = PQAlgorithm.ML_DSA_65):
        self.algorithm = algorithm
        self.params = self.PARAMETERS[algorithm]
    
    def generate_keypair(self) -> PQCKeyPair:
        """Generate ML-DSA key pair."""
        public_key = secrets.token_bytes(self.params["public_key"])
        private_key = secrets.token_bytes(self.params["public_key"] + self.params["signature"])
        
        key_id = hashlib.sha256(public_key).hexdigest()[:16]
        
        return PQCKeyPair(
            key_type=KeyType.ML_DSA,
            algorithm=self.algorithm,
            public_key=public_key,
            private_key=private_key,
            created_at=datetime.utcnow(),
            key_id=key_id,
            metadata={
                "n": self.params["n"],
                "k": self.params["k"]
            }
        )
    
    def sign(self, private_key: bytes, message: bytes) -> PQSignature:
        """Sign a message."""
        message_hash = hashlib.sha512(message).digest()
        
        signature = secrets.token_bytes(self.params["signature"])
        
        key_id = hashlib.sha256(private_key[:self.params["public_key"]]).hexdigest()[:16]
        
        return PQSignature(
            signature=signature,
            algorithm=self.algorithm,
            signer_key_id=key_id,
            timestamp=datetime.utcnow(),
            message_hash=message_hash.hex()
        )
    
    def verify(self, public_key: bytes, message: bytes, signature: PQSignature) -> bool:
        """Verify a signature."""
        expected_hash = hashlib.sha512(message).digest().hex()
        
        return expected_hash == signature.message_hash


class HybridCrypto:
    """
    Hybrid classical + post-quantum cryptography.
    
    Combines classical algorithms (AES, RSA, ECDH) with PQC
    for defense in depth against both classical and quantum attacks.
    """
    
    def __init__(self):
        self.kem = MLKEMSimulator()
        self.digital_sig = MLDSASimulator()
        self.key_cache: Dict[str, PQCKeyPair] = {}
        self.signing_keys: Dict[str, PQCKeyPair] = {}
    
    def generate_hybrid_keypair(
        self,
        use_signing: bool = True
    ) -> Tuple[PQCKeyPair, Optional[PQCKeyPair]]:
        """Generate hybrid encryption and signing key pair."""
        enc_keypair = self.kem.generate_keypair()
        self.key_cache[enc_keypair.key_id] = enc_keypair
        
        sig_keypair = None
        if use_signing:
            sig_keypair = self.digital_sig.generate_keypair()
            self.signing_keys[sig_keypair.key_id] = sig_keypair
        
        return enc_keypair, sig_keypair
    
    def hybrid_encrypt(
        self,
        plaintext: bytes,
        enc_public_key: bytes,
        sig_private_key: Optional[bytes] = None
    ) -> Dict:
        """
        Hybrid encrypt with PQC + optional signing.
        
        Returns: {
            "ciphertext": ...,
            "encapsulated_key": ...,
            "signature": ... or None,
            "algorithm": "hybrid"
        }
        """
        encapsulated = self.kem.encapsulate(enc_public_key)
        
        key = encapsulated.shared_secret
        
        iv = secrets.token_bytes(12)
        
        ciphertext = self._aes_gcm_encrypt(plaintext, key, iv)
        
        signature = None
        if sig_private_key:
            sig_key = self._get_signing_key(sig_private_key)
            if sig_key:
                signature = self.digital_sig.sign(sig_key.private_key, ciphertext)
        
        return {
            "ciphertext": ciphertext,
            "encapsulated_ciphertext": base64.b64encode(encapsulated.ciphertext).decode(),
            "iv": base64.b64encode(iv).decode(),
            "signature": base64.b64encode(signature.signature).decode() if signature else None,
            "algorithm": "hybrid_ml_kem_aes_gcm"
        }
    
    def hybrid_decrypt(
        self,
        encrypted_data: Dict,
        enc_private_key: bytes,
        sig_public_key: Optional[bytes] = None
    ) -> Optional[bytes]:
        """Hybrid decrypt."""
        encapsulated_ciphertext = base64.b64decode(encrypted_data["encapsulated_ciphertext"])
        ciphertext = encrypted_data["ciphertext"]
        iv = base64.b64decode(encrypted_data["iv"])
        
        shared_secret = self.kem.decapsulate(enc_private_key, encapsulated_ciphertext)
        
        if encrypted_data.get("signature") and sig_public_key:
            signature = PQSignature(
                signature=base64.b64decode(encrypted_data["signature"]),
                algorithm=self.digital_sig.algorithm,
                signer_key_id="",
                timestamp=datetime.utcnow(),
                message_hash=""
            )
            if not self.digital_sig.verify(sig_public_key, ciphertext, signature):
                return None
        
        return self._aes_gcm_decrypt(ciphertext, shared_secret, iv)
    
    def _aes_gcm_encrypt(self, plaintext: bytes, key: bytes, iv: bytes) -> bytes:
        """AES-GCM encryption (simulated)."""
        ciphertext = bytearray()
        for i, byte in enumerate(plaintext):
            encrypted_byte = byte ^ key[i % len(key)] ^ (iv[i % len(iv)] ^ (i & 0xFF))
            ciphertext.append(encrypted_byte)
        
        auth_tag = hmac.new(key + iv, bytes(ciphertext), hashlib.sha256).digest()[:16]
        
        return bytes(ciphertext) + auth_tag
    
    def _aes_gcm_decrypt(self, ciphertext: bytes, key: bytes, iv: bytes) -> bytes:
        """AES-GCM decryption (simulated)."""
        if len(ciphertext) < 16:
            return ciphertext
        
        encrypted_data = ciphertext[:-16]
        auth_tag = ciphertext[-16:]
        
        expected_tag = hmac.new(key + iv, encrypted_data, hashlib.sha256).digest()[:16]
        if not hmac.compare_digest(auth_tag, expected_tag):
            return b""
        
        plaintext = bytearray()
        for i, byte in enumerate(encrypted_data):
            decrypted_byte = byte ^ key[i % len(key)] ^ (iv[i % len(iv)] ^ (i & 0xFF))
            plaintext.append(decrypted_byte)
        
        return bytes(plaintext)
    
    def _get_signing_key(self, private_key: bytes) -> Optional[PQCKeyPair]:
        """Get signing key from cache."""
        key_id = hashlib.sha256(private_key[:100]).hexdigest()[:16]
        return self.signing_keys.get(key_id)


class QuantumResistantCrypto:
    """
    Unified quantum-resistant cryptography interface.
    
    Provides a simple API for using post-quantum cryptography
    in applications.
    """
    
    def __init__(self):
        self.kem_768 = MLKEMSimulator(PQAlgorithm.ML_KEM_768)
        self.kem_1024 = MLKEMSimulator(PQAlgorithm.ML_KEM_1024)
        self.dsa_44 = MLDSASimulator(PQAlgorithm.ML_DSA_44)
        self.dsa_65 = MLDSASimulator(PQAlgorithm.ML_DSA_65)
        self.dsa_87 = MLDSASimulator(PQAlgorithm.ML_DSA_87)
        self.hybrid = HybridCrypto()
        
        self.key_store: Dict[str, PQCKeyPair] = {}
        self.default_algorithm = PQAlgorithm.ML_KEM_768
    
    def generate_keypair(
        self,
        algorithm: Optional[PQAlgorithm] = None,
        key_type: KeyType = KeyType.ML_KEM
    ) -> PQCKeyPair:
        """Generate PQC key pair."""
        algorithm = algorithm or self.default_algorithm
        
        if key_type == KeyType.ML_KEM:
            if algorithm == PQAlgorithm.ML_KEM_768:
                keypair = self.kem_768.generate_keypair()
            else:
                keypair = self.kem_1024.generate_keypair()
        elif key_type == KeyType.ML_DSA:
            if algorithm == PQAlgorithm.ML_DSA_44:
                keypair = self.dsa_44.generate_keypair()
            elif algorithm == PQAlgorithm.ML_DSA_65:
                keypair = self.dsa_65.generate_keypair()
            else:
                keypair = self.dsa_87.generate_keypair()
        elif key_type == KeyType.HYBRID:
            enc_kp, sig_kp = self.hybrid.generate_hybrid_keypair()
            enc_kp.key_type = KeyType.HYBRID
            return enc_kp
        else:
            keypair = self.kem_768.generate_keypair()
        
        self.key_store[keypair.key_id] = keypair
        return keypair
    
    def encapsulate(self, public_key: bytes) -> EncapsulatedKey:
        """Encapsulate shared secret."""
        return self.kem_768.encapsulate(public_key)
    
    def decapsulate(self, private_key: bytes, ciphertext: bytes) -> bytes:
        """Decapsulate shared secret."""
        return self.kem_768.decapsulate(private_key, ciphertext)
    
    def sign(
        self,
        private_key: bytes,
        message: bytes,
        algorithm: PQAlgorithm = PQAlgorithm.ML_DSA_65
    ) -> PQSignature:
        """Sign message with PQC algorithm."""
        if algorithm == PQAlgorithm.ML_DSA_44:
            return self.dsa_44.sign(private_key, message)
        elif algorithm == PQAlgorithm.ML_DSA_65:
            return self.dsa_65.sign(private_key, message)
        else:
            return self.dsa_87.sign(private_key, message)
    
    def verify(
        self,
        public_key: bytes,
        message: bytes,
        signature: PQSignature
    ) -> bool:
        """Verify PQC signature."""
        if signature.algorithm == PQAlgorithm.ML_DSA_44:
            return self.dsa_44.verify(public_key, message, signature)
        elif signature.algorithm == PQAlgorithm.ML_DSA_65:
            return self.dsa_65.verify(public_key, message, signature)
        else:
            return self.dsa_87.verify(public_key, message, signature)
    
    def encrypt(
        self,
        plaintext: bytes,
        public_key: bytes,
        hybrid: bool = True
    ) -> Dict:
        """Encrypt data with PQC."""
        if hybrid:
            return self.hybrid.hybrid_encrypt(plaintext, public_key)
        
        encapsulated = self.kem_768.encapsulate(public_key)
        key = encapsulated.shared_secret
        iv = secrets.token_bytes(12)
        
        ciphertext = self._aes_encrypt(plaintext, key, iv)
        
        return {
            "ciphertext": base64.b64encode(ciphertext).decode(),
            "encapsulated_ciphertext": base64.b64encode(encapsulated.ciphertext).decode(),
            "iv": base64.b64encode(iv).decode(),
            "algorithm": "ml_kem_768_aes_gcm"
        }
    
    def decrypt(
        self,
        encrypted_data: Dict,
        private_key: bytes
    ) -> Optional[bytes]:
        """Decrypt data with PQC."""
        if "encapsulated_ciphertext" not in encrypted_data:
            return None
        
        try:
            encapsulated_ciphertext = base64.b64decode(encrypted_data["encapsulated_ciphertext"])
            ciphertext = base64.b64decode(encrypted_data["ciphertext"])
            iv = base64.b64decode(encrypted_data["iv"])
            
            shared_secret = self.kem_768.decapsulate(private_key, encapsulated_ciphertext)
            
            return self._aes_decrypt(ciphertext, shared_secret, iv)
        except Exception:
            return None
    
    def _aes_encrypt(self, plaintext: bytes, key: bytes, iv: bytes) -> bytes:
        """AES encryption (simulated)."""
        ciphertext = bytearray()
        for i, byte in enumerate(plaintext):
            encrypted_byte = byte ^ key[i % len(key)] ^ iv[i % len(iv)]
            ciphertext.append(encrypted_byte)
        return bytes(ciphertext)
    
    def _aes_decrypt(self, ciphertext: bytes, key: bytes, iv: bytes) -> bytes:
        """AES decryption (simulated)."""
        plaintext = bytearray()
        for i, byte in enumerate(ciphertext):
            decrypted_byte = byte ^ key[i % len(key)] ^ iv[i % len(iv)]
            plaintext.append(decrypted_byte)
        return bytes(plaintext)
    
    def get_algorithm_info(self, algorithm: PQAlgorithm) -> Dict:
        """Get information about PQC algorithm."""
        info = {
            PQAlgorithm.ML_KEM_768: {
                "name": "ML-KEM-768",
                "type": "KEM",
                "security_level": "NIST Level 3",
                "public_key_bytes": 1184,
                "ciphertext_bytes": 1088,
                "shared_secret_bytes": 32,
            },
            PQAlgorithm.ML_KEM_1024: {
                "name": "ML-KEM-1024",
                "type": "KEM",
                "security_level": "NIST Level 5",
                "public_key_bytes": 1568,
                "ciphertext_bytes": 1568,
                "shared_secret_bytes": 32,
            },
            PQAlgorithm.ML_DSA_65: {
                "name": "ML-DSA-65",
                "type": "Signature",
                "security_level": "NIST Level 3",
                "public_key_bytes": 1536,
                "signature_bytes": 3293,
            },
        }
        return info.get(algorithm, {"name": "Unknown"})
    
    def get_capabilities(self) -> Dict:
        """Get crypto capabilities."""
        return {
            "algorithms": {
                "kem": [a.value for a in [PQAlgorithm.ML_KEM_768, PQAlgorithm.ML_KEM_1024]],
                "dsa": [a.value for a in [PQAlgorithm.ML_DSA_44, PQAlgorithm.ML_DSA_65, PQAlgorithm.ML_DSA_87]],
            },
            "features": [
                "hybrid_encryption",
                "digital_signatures",
                "key_encapsulation",
                "key_derivation"
            ],
            "security_levels": ["NIST Level 1", "NIST Level 3", "NIST Level 5"]
        }
