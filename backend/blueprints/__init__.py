from backend.blueprints.auth import bp as auth_bp
from backend.blueprints.planner import bp as planner_bp
from backend.blueprints.settings import bp as settings_bp
from backend.blueprints.health import bp as health_bp

__all__ = ["auth_bp", "planner_bp", "settings_bp", "health_bp"]
