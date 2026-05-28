"""
Skrypt jednorazowy — usuwa ghost profiles (konta bez nicku i bez hasła).
Uruchom JEDEN RAZ: python scripts/cleanup_ghost_profiles.py
"""

import sys

sys.path.insert(0, ".")

from sqlmodel import Session, select

from app.database import engine
from app.models import DailyLogDB, DrillResultDB, ExerciseResultDB, UserDB


def cleanup():
    with Session(engine) as session:
        all_users = session.exec(select(UserDB)).all()
        ghosts = []
        for user in all_users:
            if user.nickname or user.hashed_password or user.email:
                continue
            has_data = (
                session.exec(select(DailyLogDB).where(DailyLogDB.user_id == user.id)).first()
                or session.exec(select(ExerciseResultDB).where(ExerciseResultDB.user_id == user.id)).first()
                or session.exec(select(DrillResultDB).where(DrillResultDB.user_id == user.id)).first()
            )
            if not has_data:
                ghosts.append(user)

        print(f"Znaleziono {len(ghosts)} ghost profiles:")
        for ghost in ghosts:
            print(f"  id={ghost.id}  user_key={ghost.user_key}  created={ghost.created_at}")
        if not ghosts:
            print("Brak ghost profiles.")
            return
        confirm = input(f"Usunąć {len(ghosts)} ghost profiles? [tak/NIE]: ")
        if confirm.strip().lower() != "tak":
            print("Anulowano.")
            return
        for ghost in ghosts:
            session.delete(ghost)
        session.commit()
        print(f"✅ Usunięto {len(ghosts)} ghost profiles.")


if __name__ == "__main__":
    cleanup()
