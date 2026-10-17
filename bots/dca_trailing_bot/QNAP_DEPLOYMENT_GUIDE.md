# Guide de Déploiement sur QNAP NAS

Ce guide explique comment déployer le **DCA Trailing Bot** sur votre NAS QNAP en utilisant **Container Station**.

---

## 📋 Prérequis

1. **QNAP NAS** avec Container Station installé
2. **Accès internet** depuis votre NAS
3. **Clé API Coinbase Advanced Trade** (pour le trading réel ou paper trading)
4. **Accès SSH** (optionnel, pour la construction via CLI)

---

## 🚀 Méthode 1: Déploiement via Container Station (Recommandé)

### Étape 1: Préparer les fichiers

1. Connectez-vous à votre NAS via **File Station**
2. Créez un dossier pour le bot, par exemple : `/share/Container/dca-trailing-bot`
3. Copiez tous les fichiers du bot dans ce dossier :
   - `bots/dca_trailing_bot/*.py` (tous les fichiers Python)
   - `bots/dca_trailing_bot/*.yaml` (configurations)
   - `bots/dca_trailing_bot/Dockerfile`
   - `bots/dca_trailing_bot/requirements.txt`
   - `bots/dca_trailing_bot/.dockerignore`

### Étape 2: Construire l'image Docker via Container Station

1. **Ouvrir Container Station** depuis le QTS
2. Cliquer sur **"Créer"** → **"Créer un conteneur"**
3. Choisir **"Créer une image Docker personnalisée"**

4. **Configurer la construction** :
   - **Nom de l'image** : `dca-trailing-bot`
   - **Dossier Dockerfile** : `/share/Container/dca-trailing-bot`
   - **Fichier Dockerfile** : `Dockerfile`
   - Cliquer sur **"Suivant"**

5. **Attendre la construction** (peut prendre 5-10 minutes)
   - Container Station va télécharger Python et les dépendances

6. **Une fois l'image construite**, elle apparaîtra dans **"Images"**

### Étape 3: Créer le conteneur

1. Dans **Container Station**, aller dans **"Conteneurs"**
2. Cliquer sur **"Créer"** → **"Créer un conteneur"**
3. Sélectionner votre image **`dca-trailing-bot`**

4. **Configurer le conteneur** :

   **Onglet "Général"** :
   - **Nom du conteneur** : `dca-trailing-bot-btc` (ou `dca-trailing-bot-eth`)
   - **Mode de démarrage** : `Toujours` (pour redémarrer automatiquement)

   **Onglet "Volumes"** :
   - Ajouter un volume pour persister les données :
     - **Chemin du conteneur** : `/app/state`
     - **Chemin de l'hôte** : `/share/Container/dca-trailing-bot/state`
   - Ajouter pour les logs :
     - **Chemin du conteneur** : `/app/logs`
     - **Chemin de l'hôte** : `/share/Container/dca-trailing-bot/logs`
   - Ajouter pour les rapports :
     - **Chemin du conteneur** : `/app/reports`
     - **Chemin de l'hôte** : `/share/Container/dca-trailing-bot/reports`

   **Onglet "Variables d'environnement"** :
   - Ajouter :
     - `COINBASE_API_KEY` = `votre_clé_API_Coinbase`
     - `COINBASE_API_SECRET` = `votre_secret_API_Coinbase`

   **Onglet "Commande"** :
   - **Commande** : `python3 __main__.py --config config_ultimate.yaml` (pour BTC)
   - Ou : `python3 __main__.py --config config_eth_ultimate.yaml` (pour ETH)

5. **Cliquer sur "Appliquer"** pour créer le conteneur

6. **Démarrer le conteneur**

---

## 🚀 Méthode 2: Déploiement via SSH (Alternative)

Si vous préférez utiliser la ligne de commande :

### Étape 1: Copier les fichiers sur le NAS

```bash
# Depuis votre ordinateur
scp -r bots/dca_trailing_bot/ admin@VOTRE_NAS:/share/Container/
```

### Étape 2: Construire l'image

```bash
ssh admin@VOTRE_NAS
cd /share/Container/dca_trailing_bot

# Construire l'image
docker build -t dca-trailing-bot .
```

### Étape 3: Lancer le conteneur BTC

```bash
docker run -d \
  --name dca-trailing-bot-btc \
  --restart unless-stopped \
  -v /share/Container/dca_trailing_bot/state:/app/state \
  -v /share/Container/dca_trailing_bot/logs:/app/logs \
  -v /share/Container/dca_trailing_bot/reports:/app/reports \
  -e COINBASE_API_KEY=votre_clé \
  -e COINBASE_API_SECRET=votre_secret \
  dca-trailing-bot \
  python3 __main__.py --config config_ultimate.yaml
```

### Étape 4: Lancer le conteneur ETH

```bash
docker run -d \
  --name dca-trailing-bot-eth \
  --restart unless-stopped \
  -v /share/Container/dca_trailing_bot/state:/app/state \
  -v /share/Container/dca_trailing_bot/logs:/app/logs \
  -v /share/Container/dca_trailing_bot/reports:/app/reports \
  -e COINBASE_API_KEY=votre_clé \
  -e COINBASE_API_SECRET=votre_secret \
  dca-trailing-bot \
  python3 __main__.py --config config_eth_ultimate.yaml
```

---

## 🔧 Configuration des Clés API Coinbase

### Pour le Paper Trading (simulation)

Le bot fonctionne déjà en mode **paper** par défaut (simulation sans argent réel).

### Pour le Trading Réel

1. **Créer une clé API Coinbase Advanced Trade** :
   - Allez sur [Coinbase Advanced Trade](https://www.coinbase.com/advanced-trade)
   - Paramètres → API Keys → Créer une nouvelle clé
   - **Permissions requises** :
     - ✅ **View** (pour lire les prix)
     - ✅ **Trade** (pour passer des ordres)
   - **Restrictions IP** : Ajoutez l'IP de votre NAS (optionnel mais recommandé)

2. **Stocker les clés en sécurité** :
   - **Ne jamais committer** les clés dans Git
   - Utilisez les **Variables d'environnement** dans Container Station
   - Ou créez un fichier `.env` dans le dossier (exclus du Git via `.dockerignore`)

---

## 📊 Commandes Utiles

### Vérifier les logs

**Via Container Station** :
- Sélectionner le conteneur → onglet "Logs"

**Via SSH** :
```bash
# Voir les logs en temps réel
docker logs -f dca-trailing-bot-btc

# Voir les derniers logs
docker logs --tail 100 dca-trailing-bot-btc
```

### Redémarrer le conteneur

```bash
docker restart dca-trailing-bot-btc
```

### Arrêter le conteneur

```bash
docker stop dca-trailing-bot-btc
```

### Mettre à jour le bot

1. Arrêter le conteneur :
   ```bash
docker stop dca-trailing-bot-btc
   ```

2. Tirer les dernières modifications depuis Git :
   ```bash
   cd /share/Container/dca_trailing_bot
   git pull
   ```

3. Reconstruire l'image :
   ```bash
docker build -t dca-trailing-bot .
   ```

4. Re-créer le conteneur avec la nouvelle image :
   ```bash
docker rm dca-trailing-bot-btc
docker run -d ... (même commande que précédemment)
   ```

---

## 🎯 Gestion des Configurations

Le bot utilise des fichiers de configuration YAML différents :

| Fichier | Description | Token |
|--------|-------------|-------|
| `config_ultimate.yaml` | Config optimisée avec DCA | BTC-USDC |
| `config_eth_ultimate.yaml` | Config optimisée pour ETH | ETH-USDC |
| `config.yaml` | Config par défaut | BTC-USDC |

Pour changer de configuration, modifiez la commande du conteneur :
```bash
python3 __main__.py --config config_eth_ultimate.yaml
```

---

## 📈 Générer les Rapports Discord

Pour générer un rapport de performance :

```bash
# Créer un conteneur temporaire pour générer le rapport
docker run --rm \
  -v /share/Container/dca_trailing_bot/state:/app/state \
  -v /share/Container/dca_trailing_bot/logs:/app/logs \
  -v /share/Container/dca_trailing_bot/reports:/app/reports \
  -e COINBASE_API_KEY=votre_clé \
  -e COINBASE_API_SECRET=votre_secret \
  dca-trailing-bot \
  python3 generate_discord_report.py
```

Les graphiques seront générés dans `/share/Container/dca_trailing_bot/reports/` et peuvent être partagés sur Discord.

---

## ⚠️ Résolution des Problèmes

### Problème: Le conteneur ne démarre pas

**Vérifier les logs** :
```bash
docker logs dca-trailing-bot-btc
```

**Problèmes courants** :
- Clés API manquantes → Vérifiez les variables d'environnement
- Permission refusée → Vérifiez les permissions des volumes montés
- Erreur de dépendance → Reconstruisez l'image

### Problème: Connexion à Coinbase échoue

- Vérifiez que votre NAS a accès à internet
- Vérifiez que les clés API sont correctes
- Vérifiez que l'IP de votre NAS est autorisée dans Coinbase

### Problème: Les données ne sont pas persistes

- Vérifiez que les volumes sont correctement montés
- Vérifiez les permissions : `chmod -R 777 /share/Container/dca_trailing_bot/state`

---

## 🔒 Sécurité

1. **Ne jamais exposer** les clés API dans le code ou Git
2. **Utilisez les variables d'environnement** ou un fichier `.env` (exclus du Git)
3. **Limitez les permissions** de l'API Coinbase (seulement View + Trade)
4. **Restreignez par IP** dans Coinbase si possible
5. **Mettez à jour régulièrement** l'image Docker pour les correctifs de sécurité

---

## 📚 Fichiers Importants

| Fichier | Description |
|--------|-------------|
| `Dockerfile` | Configuration de l'image Docker |
| `docker-compose.yml` | Configuration multi-conteneurs (optionnel) |
| `requirements.txt` | Dépendances Python |
| `.dockerignore` | Fichiers à exclure de l'image |
| `config_ultimate.yaml` | Configuration optimisée BTC |
| `config_eth_ultimate.yaml` | Configuration optimisée ETH |

---

## 🎉 Résumé

✅ **Méthode recommandée** : Utilisez **Container Station** (Méthode 1) - plus simple et graphique

✅ **Alternative** : Utilisez **SSH** (Méthode 2) - plus flexible

✅ **Clés API** : À configurer dans les variables d'environnement

✅ **Données persistantes** : Utilisez les volumes pour state/, logs/, reports/

✅ **Mises à jour** : Git pull + rebuild + restart

---

**Besoin d'aide?** Consultez le README.md dans le dossier du bot ou contactez-moi!
