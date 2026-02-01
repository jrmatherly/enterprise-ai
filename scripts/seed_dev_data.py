#!/usr/bin/env python3
"""Seed development data for testing.

Run with: uv run python scripts/seed_dev_data.py
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from src.db.database import async_session_maker
from src.db.models import Tenant, User, TenantType


async def seed_dev_data():
    """Create development tenant and user for testing."""
    
    async with async_session_maker() as db:
        # Check if dev tenant already exists
        result = await db.execute(
            select(Tenant).where(Tenant.id == "00000000-0000-0000-0000-000000000000")
        )
        existing_tenant = result.scalar_one_or_none()
        
        if existing_tenant:
            print("✓ Dev tenant already exists")
        else:
            # Create dev tenant
            tenant = Tenant(
                id="00000000-0000-0000-0000-000000000000",
                name="Development Organization",
                type=TenantType.ORGANIZATION,
                external_id="dev-org",
                tpm_limit=500000,  # Higher limits for dev
                rpm_limit=300,
                settings={"environment": "development"},
            )
            db.add(tenant)
            print("✓ Created dev tenant")
        
        # Check if dev user already exists
        result = await db.execute(
            select(User).where(User.id == "00000000-0000-0000-0000-000000000001")
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            print("✓ Dev user already exists")
        else:
            # Create dev user
            user = User(
                id="00000000-0000-0000-0000-000000000001",
                external_id="dev-user",
                email="dev@example.com",
                display_name="Developer",
                tenant_id="00000000-0000-0000-0000-000000000000",
                roles=["OrgAdmin", "Developer"],
                is_active=True,
            )
            db.add(user)
            print("✓ Created dev user")
        
        await db.commit()
        print("\n✓ Dev data seeded successfully!")
        print("  - Tenant ID: 00000000-0000-0000-0000-000000000000")
        print("  - User ID:   00000000-0000-0000-0000-000000000001")


if __name__ == "__main__":
    asyncio.run(seed_dev_data())
