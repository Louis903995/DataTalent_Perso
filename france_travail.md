# Documentation API France Travail

## 1. Inscription & Credentials

1. Créer un compte sur [francetravail.io](https://francetravail.io)
2. Créer une application dans l'espace développeur
3. Souscrire à l'API **"Offres d'emploi v2"**
4. Récupérer `CLIENT_ID` et `CLIENT_SECRET`

Variables d'environnement à définir dans `.env` :

```env
CLIENT_ID=PAR_xxxx_...
CLIENT_SECRET=...
```

---

## 2. OAuth2 — Flow client_credentials

France Travail utilise le flow **machine-to-machine** (pas de refresh token).

### Requête token

```http
POST https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=%2Fpartenaire
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials
&client_id=PAR_xxxx
&client_secret=...
&scope=api_offresdemploiv2 o2dsoffre
```

### Réponse

```json
{
  "access_token": "eyJ...",
  "token_type": "Bearer",
  "expires_in": 1499
}
```

### Utilisation

```http
GET https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search
Authorization: Bearer <access_token>
```

### Comportement du cache (auth.py)

| Situation | Comportement |
|---|---|
| Token valide en cache | Réutilisé sans appel réseau |
| Token expirant dans < 60s | Renouvellement anticipé |
| Réponse 401 de l'API | Invalidation forcée + retry immédiat |

---

## 3. Endpoints

### 3.1 Recherche d'offres

```
GET /partenaire/offresdemploi/v2/offres/search
```

**Paramètres principaux :**

| Paramètre | Type | Description |
|---|---|---|
| `codeROME` | string | Code métier ROME (ex: `M1805`) |
| `departement` | string | Numéro département (ex: `75`) |
| `range` | string | Pagination (ex: `0-149`) |
| `motsCles` | string | Mots-clés libres |
| `typeContrat` | string | `CDI`, `CDD`, `MIS`... |

**Limites :**
- Batch max : **150 offres** par requête (`range: 0-149`)
- Limite dure : **3000 offres** par requête (`range: 0-2999`)
- Au-delà : affiner les filtres (département, ROME, mots-clés)

**Réponse header :**
```
Content-Range: offres 0-149/523
```
→ `523` = nombre total d'offres disponibles pour cette recherche.

---

### 3.2 Détail d'une offre

```
GET /partenaire/offresdemploi/v2/offres/{id}
```

---

## 4. Schéma de réponse — Offre

```json
{
  "id": "187GHKL",
  "intitule": "Data Engineer H/F",
  "description": "...",
  "dateCreation": "2024-03-01T08:00:00.000Z",
  "dateActualisation": "2024-03-05T10:00:00.000Z",
  "lieuTravail": {
    "libelle": "75 - PARIS",
    "codePostal": "75008",
    "commune": "75108",
    "departement": "75"
  },
  "romeCode": "M1805",
  "romeLibelle": "Études et développement informatique",
  "entreprise": {
    "nom": "DataCorp",
    "description": "...",
    "secteurActivite": "62"
  },
  "typeContrat": "CDI",
  "typeContratLibelle": "Contrat à durée indéterminée",
  "natureContrat": "Contrat travail",
  "experienceExige": "E",
  "experienceLibelle": "3 ans et plus",
  "salaire": {
    "libelle": "Annuel de 45000 à 60000 €",
    "commentaire": "selon profil"
  },
  "competences": [
    { "code": "...", "libelle": "Python" },
    { "code": "...", "libelle": "Apache Spark" }
  ],
  "formations": [
    {
      "codeFormation": "26",
      "domaineLibelle": "informatique",
      "niveauLibelle": "Bac+5 et plus"
    }
  ],
  "nombrePostes": 1,
  "accessibleTH": false,
  "origineOffre": {
    "origine": "1",
    "urlOrigine": "https://..."
  }
}
```

---

## 5. Rate Limits

| Limite | Valeur |
|---|---|
| Offres par batch | 150 max |
| Offres par recherche | 3 000 max |
| Erreur rate limit | HTTP 429 |
| Stratégie implémentée | Backoff exponentiel : 2, 4, 8, 16, 32s (5 tentatives) |

En cas de dépassement fréquent : affiner les requêtes par département + code ROME pour rester sous 3000 résultats.

---

## 6. Architecture des fichiers

```
ingestion/france_travail/
├── auth.py          # Client OAuth2 avec cache et retry 401
├── offres.py        # Pagination + backoff 429
├── ingest.py        # Point d'entrée principal
└── raw/             # Fichiers JSON bruts (gitignore)
    └── france_travail/
        └── offres_M1805_75.json
```