from slowapi import Limiter
from slowapi.util import get_remote_address

# Limiteur partagé par toutes les routes. Stockage en mémoire par défaut :
# suffisant pour un seul processus, mais chaque worker/instance aurait son
# propre compteur si l'app tourne un jour derrière plusieurs processus —
# prévoir un backend Redis (`storage_uri=`) avant de scaler horizontalement.
limiter = Limiter(key_func=get_remote_address)
