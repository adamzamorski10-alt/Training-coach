# Endpointy brakujace po modularizacji

Lista endpointow z `fitai_api.py`, ktorych nie ma w:
`app/fitness/routes.py`, `app/ai/routes.py`, `app/auth/routes.py`,
`app/health/routes.py`.

| Method | Path | Function |
| --- | --- | --- |
| POST | `/users/{user_id}` | `create_or_update_user` |
| GET | `/users/{user_id}` | `get_user` |
| POST | `/users/{user_id}/logs` | `add_log` |
| GET | `/users/{user_id}/logs` | `get_logs` |
| GET | `/app/exercise-history` | `get_exercise_history` |
| GET | `/app/progression-summary` | `get_progression_summary` |
| POST | `/app/onboarding` | `app_onboarding` |
| POST | `/app/water` | `app_log_water` |
| POST | `/app/link-discord` | `app_link_discord` |
| GET | `/app/reminders` | `app_get_reminders` |
| POST | `/app/reminders` | `app_set_reminders` |
| GET | `/app/reminders-due` | `app_reminders_due` |
| GET | `/app/plan` | `app_get_plan` |
| POST | `/app/plan/generate` | `app_generate_plan` |
| POST | `/app/plan/swap` | `app_swap_plan_item` |
| GET | `/app/sport-suggest-day` | `sport_suggest_day` |
| GET | `/app/training-load/{user_id}` | `get_training_load` |
| POST | `/app/plan/regenerate-ai` | `regenerate_plan_with_ai` |
| GET | `/app/sport-drills` | `list_sport_drills` |
| GET | `/app/drill-history` | `get_drill_history` |
| POST | `/billing/plan` | `billing_set_plan` |
| POST | `/billing/stripe/webhook` | `stripe_webhook` |
| POST | `/ai/analyze-log` | `ai_analyze_log` |
| GET | `/app/xp` | `app_get_xp` |
| POST | `/app/injuries` | `app_update_injuries` |
| GET | `/app/overload` | `app_check_overload` |
| POST | `/app/fridge-chef` | `app_fridge_chef` |
| POST | `/app/kitchen/generate` | `app_kitchen_generate` |
| GET | `/app/meal-prep-plan` | `app_meal_prep_plan` |
| GET | `/app/stats` | `app_get_stats` |
| POST | `/app/diet/add-meal` | `app_diet_add_meal` |
| POST | `/app/logout` | `app_logout` |
| GET | `/` | `root` |
| GET | `/app/version` | `get_version` |
