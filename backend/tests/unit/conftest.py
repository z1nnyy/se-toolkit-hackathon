import os


os.environ["CAVA_NAME"] = "Cava Menu API"
os.environ["CAVA_DEBUG"] = "false"
os.environ["CAVA_ADDRESS"] = "127.0.0.1"
os.environ["CAVA_PORT"] = "8000"
os.environ["CAVA_RELOAD"] = "false"
os.environ["CAVA_CORS_ORIGINS"] = "[]"
os.environ["CAVA_DATABASE_URL"] = "sqlite+aiosqlite:///./data/test-menu.db"
os.environ["CAVA_MENU_RENDER_CACHE_DIR"] = "./data/test-menu-render-cache"
os.environ["CAVA_SEED_DEMO_DATA"] = "false"
os.environ["CAVA_AUTH_SESSION_HOURS"] = "12"
os.environ["CAVA_SUPERADMIN_USERNAME"] = "owner"
os.environ["CAVA_SUPERADMIN_PASSWORD"] = "owner12345"
os.environ["CAVA_SUPERADMIN_FULL_NAME"] = "Main Administrator"
