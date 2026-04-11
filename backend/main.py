import uvicorn

from app import create_app

app = None


def get_app():
    global app
    if app is None:
        app = create_app()
    return app


if __name__ == "__main__":
    uvicorn.run("main:get_app", host="0.0.0.0", port=8000, factory=True)
