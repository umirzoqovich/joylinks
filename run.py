import uvicorn
from config import settings
import main

if __name__ == "__main__":
    print(f"==================================================", flush=True)
    print(f"  🚀 {settings.CENTER_NAME} TARGET CRM ISHGA TUSHDI!", flush=True)
    print(f"==================================================", flush=True)
    print(f"  🌐 Web CRM Panel:    http://127.0.0.1:{settings.PORT}", flush=True)
    print(f"  🎯 Target Formasi:   http://127.0.0.1:{settings.PORT}/form", flush=True)
    print(f"  📖 API Hujjatlari:   http://127.0.0.1:{settings.PORT}/docs", flush=True)
    print(f"==================================================", flush=True)
    print(f"  💡 Maslahat: Bot Token va Guruh ID sini Web CRM", flush=True)
    print(f"     interfeysidagi 'Sozlamalar' bo'limidan kiritasiz.", flush=True)
    print(f"==================================================\n", flush=True)

    uvicorn.run(main.app, host="127.0.0.1", port=settings.PORT, log_level="info")
