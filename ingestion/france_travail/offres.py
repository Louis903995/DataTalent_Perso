# ingestion/france_travail/offres.py
import time
import requests
from auth import get_token, invalidate_token

API_URL = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"

BATCH_SIZE = 150        # max autorisé par France Travail
MAX_OFFRES = 3000       # limite dure de l'API (range max : 0-2999)
MAX_RETRIES = 5         # tentatives max sur rate limit
BACKOFF_BASE = 2        # secondes, exponentiel : 2, 4, 8, 16, 32


def _fetch_batch(code_rome: str, departement: str, start: int, end: int) -> tuple[list, int]:
    """
    Récupère un batch d'offres.
    Retourne offres en lisant le Content-Range de la réponse.
    Gère : retry 401 (token expiré) + backoff exponentiel sur 429.
    """
    for attempt in range(MAX_RETRIES):
        try:
            token = get_token()
            headers = {"Authorization": f"Bearer {token}"}
            params = {
                "codeROME": code_rome,
                "departement": departement,
                "range": f"{start}-{end}"
            }

            response = requests.get(API_URL, headers=headers, params=params)

            # --- Rate limit ---
            if response.status_code == 429:
                wait = BACKOFF_BASE ** attempt
                print(f"Rate limit (429), attente {wait}s (tentative {attempt + 1}/{MAX_RETRIES})")
                time.sleep(wait)
                continue

            # --- Token expiré ---
            if response.status_code == 401 and attempt == 0:
                print("Token invalide (401), renouvellement forcé...")
                invalidate_token()
                continue

            response.raise_for_status()
            data = response.json()

            # Content-Range: offres 0-149/523
            total = _parse_total(response.headers.get("Content-Range", ""))
            offres = data.get("resultats", [])
            return offres, total

        except requests.HTTPError as e:
            raise

    raise RuntimeError(f"Échec après {MAX_RETRIES} tentatives ({code_rome}, dept {departement})")


def _parse_total(content_range: str) -> int:
    """
    Parse 'offres 0-149/523' → 523.
    Retourne 0 si le header est absent ou malformé.
    """
    try:
        return int(content_range.split("/")[-1])
    except (IndexError, ValueError):
        return 0


def fetch_all_offres(code_rome: str, departement: str) -> list:
    """
    Récupère TOUTES les offres pour un code ROME + département
    en paginant automatiquement par batches de 150.
    Respecte la limite dure de l'API (3000 offres max).
    """
    all_offres = []
    start = 0

    while start < MAX_OFFRES:
        end = min(start + BATCH_SIZE - 1, MAX_OFFRES - 1)
        print(f"Batch {start}-{end} ({code_rome} / dept {departement})")

        offres, total = _fetch_batch(code_rome, departement, start, end)
        all_offres.extend(offres)

        print(f"  → {len(offres)} offres récupérées (total annoncé : {total})")

        # Arrêt si on a tout récupéré
        if not offres or start + BATCH_SIZE >= total:
            break

        start += BATCH_SIZE

    print(f"{len(all_offres)} offres au total ({code_rome} / dept {departement})")
    return all_offres
