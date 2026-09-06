from enum import Enum

class UserRole(str, Enum):
    STUDENT = "student"
    FACULTY = "faculty"

class BadgeTier(str, Enum):
    COMMON = "common"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"

class RoadmapDifficulty(str, Enum):
    BEGINNER = "Beginner"
    INTERMEDIATE = "Intermediate"
    ADVANCED = "Advanced"

class CollabStatus(str, Enum):
    OPEN = "open"
    FULL = "full"

class ApplicantStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"

class ChannelKind(str, Enum):
    TEXT = "text"
    ANON = "anon"