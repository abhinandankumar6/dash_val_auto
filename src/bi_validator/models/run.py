from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bi_validator.db.base import Base
from bi_validator.models.enums import FindingCategory, FindingSeverity, RunStatus


def enum_values(enum_cls):
    return [member.value for member in enum_cls]


class DashboardRun(Base):
    __tablename__ = "dashboard_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dashboard_name: Mapped[str] = mapped_column(String(255))
    dashboard_url: Mapped[str] = mapped_column(Text)
    platform: Mapped[str] = mapped_column(String(64))
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, name="runstatus", values_callable=enum_values),
        default=RunStatus.PENDING,
    )
    prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    rules_path: Mapped[str] = mapped_column(Text)
    dashboard_config_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_dir: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[dict] = mapped_column(JSON, default=dict)
    navigation_tree: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    events: Mapped[list["NavigationEvent"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    findings: Mapped[list["ValidationFinding"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    logs: Mapped[list["ExecutionLog"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    artifacts: Mapped[list["Artifact"]] = relationship(back_populates="run", cascade="all, delete-orphan")


class NavigationEvent(Base):
    __tablename__ = "navigation_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("dashboard_runs.id", ondelete="CASCADE"))
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("navigation_events.id", ondelete="CASCADE"),
        nullable=True,
    )
    sequence: Mapped[int] = mapped_column(Integer)
    depth: Mapped[int] = mapped_column(Integer)
    label: Mapped[str] = mapped_column(String(255))
    chart_type: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(64))
    page_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    target_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    state_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    screenshot_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    run: Mapped[DashboardRun] = relationship(back_populates="events")
    parent: Mapped["NavigationEvent | None"] = relationship(remote_side=[id], backref="children")
    findings: Mapped[list["ValidationFinding"]] = relationship(back_populates="event")


class ValidationFinding(Base):
    __tablename__ = "validation_findings"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("dashboard_runs.id", ondelete="CASCADE"))
    event_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("navigation_events.id", ondelete="SET NULL"),
        nullable=True,
    )
    category: Mapped[FindingCategory] = mapped_column(
        Enum(FindingCategory, name="findingcategory", values_callable=enum_values)
    )
    severity: Mapped[FindingSeverity] = mapped_column(
        Enum(FindingSeverity, name="findingseverity", values_callable=enum_values)
    )
    code: Mapped[str] = mapped_column(String(128))
    message: Mapped[str] = mapped_column(Text)
    expected: Mapped[str | None] = mapped_column(Text, nullable=True)
    actual: Mapped[str | None] = mapped_column(Text, nullable=True)
    path: Mapped[list[str]] = mapped_column(JSON, default=list)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    run: Mapped[DashboardRun] = relationship(back_populates="findings")
    event: Mapped[NavigationEvent | None] = relationship(back_populates="findings")


class ExecutionLog(Base):
    __tablename__ = "execution_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("dashboard_runs.id", ondelete="CASCADE"))
    level: Mapped[str] = mapped_column(String(32))
    event: Mapped[str] = mapped_column(String(128))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    run: Mapped[DashboardRun] = relationship(back_populates="logs")


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("dashboard_runs.id", ondelete="CASCADE"))
    event_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("navigation_events.id", ondelete="SET NULL"),
        nullable=True,
    )
    kind: Mapped[str] = mapped_column(String(64))
    path: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    run: Mapped[DashboardRun] = relationship(back_populates="artifacts")
