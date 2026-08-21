from app.db.database import init_db
from app.db.repositories import db_enabled, seed_profiles
from app.services.data_loader import load_profiles


def main() -> None:
    if not db_enabled():
        print("database disabled; set DATABASE_ENABLED=true and DATA_BACKEND=sql before seeding.")
        return
    init_db()
    profile_count = seed_profiles(load_profiles())
    print(f"database initialized; seeded profiles={profile_count}")


if __name__ == "__main__":
    main()
