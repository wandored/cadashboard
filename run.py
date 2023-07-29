"""
Dashboard app
"""

from dashapp import create_app
from asgiref.wsgi import WsgiToAsgi

app = create_app()
asgi_app = WsgiToAsgi(app) # added for uvicorn

#if __name__ == "__main__":
#    app.run(host="127.0.0.1", port=5000, debug=True)
