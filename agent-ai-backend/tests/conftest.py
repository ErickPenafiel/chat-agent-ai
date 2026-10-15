import os

# Los tests corren con la API de administración abierta salvo los que configuran Firebase explícitamente.
os.environ.setdefault("ALLOW_INSECURE_AUTH", "1")
