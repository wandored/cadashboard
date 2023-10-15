"""
Dashboard app
"""

from dashapp import create_app
from asgiref.wsgi import WsgiToAsgi
import uvicorn

app = create_app()
asgi_app = WsgiToAsgi(app) # added for uvicorn

if __name__ == "__main__":
    uvicorn.run(asgi_app, host="0.0.0.0", port=5000)
