# 🐳 Docker pour le Bot de Trading - Guide QNAP

Ce guide explique comment déployer le bot de trading sur ton **NAS QNAP** avec Docker.

---

## 📋 **PRÉREQUIS**

1. **QNAP avec Container Station** installé
   - Disponible dans App Center
   - Nécessite QTS 4.3+ 

2. **Espace disque** : Minimum 5Go libre
3. **Mémoire** : 2Go RAM recommandé
4. **Connexion Internet** : Pour accéder à l'API Coinbase

---

## 🚀 **DÉPLOIEMENT SUR QNAP**

### **Méthode 1: Utiliser Container Station (Recommandé - GUI)**

#### Étape 1: Copier les fichiers sur ton QNAP

1. **Sur ton Mac**, crée un archive des fichiers nécessaires :
```bash
cd /Users/dev/Documents/crypto/python-swing-bot
zip -r crypto-bot-docker.zip Dockerfile docker-compose.yml requirements.txt bot/ config.yaml strategies.yaml .env.example
```

2. **Copier l'archive** sur ton QNAP via File Station ou SCP

3. **Extraire** l'archive sur ton QNAP dans un dossier (ex: `/share/Container/crypto-bot`)

#### Étape 2: Créer les volumes pour la persistance

Dans File Station, crée ces dossiers :
```
/share/Container/crypto-bot/data
/share/Container/crypto-bot/logs
/share/Container/crypto-bot/state
/share/Container/crypto-bot/reports
```

#### Étape 3: Importer dans Container Station

1. Ouvre **Container Station** sur ton QNAP
2. Clique sur **"Create"** → **"Import from docker-compose.yml"**
3. Sélectionne le fichier `docker-compose.yml` que tu as copié
4. Clique sur **"Deploy"**

**✅ C'est tout !** Les deux conteneurs (BTC et ETH) devraient démarrer automatiquement.

---

### **Méthode 2: Utiliser Docker CLI (SSH)**

#### Étape 1: Copier les fichiers via SCP
```bash
# Depuis ton Mac, copier vers le QNAP
scp -r /Users/dev/Documents/crypto/python-swing-bot/* admin@IP_NAS:/share/Container/crypto-bot/
```

#### Étape 2: Se connecter au QNAP et construire
```bash
# Se connecter
ssh admin@IP_NAS

# Aller dans le dossier
cd /share/Container/crypto-bot

# Construire l'image
docker build -t crypto-bot:latest .

# Créer les volumes
mkdir -p data logs state reports

# Lancer avec docker-compose
docker-compose up -d
```

#### Étape 3: Vérifier
```bash
# Voir les conteneurs en cours
docker ps

# Voir les logs BTC
docker logs crypto-bot-btc -f

# Voir les logs ETH
docker logs crypto-bot-eth -f
```

---

## 📊 **COMMANDES UTILES**

| Action | Commande |
|--------|----------|
| **Voir les conteneurs** | `docker ps -a` |
| **Voir les logs BTC** | `docker logs crypto-bot-btc -f` |
| **Voir les logs ETH** | `docker logs crypto-bot-eth -f` |
| **Arrêter BTC** | `docker stop crypto-bot-btc` |
| **Arrêter ETH** | `docker stop crypto-bot-eth` |
| **Redémarrer BTC** | `docker start crypto-bot-btc` |
| **Redémarrer ETH** | `docker start crypto-bot-eth` |
| **Mettre à jour** | `docker-compose pull && docker-compose up -d --build` |
| **Voir l'utilisation** | `docker stats` |

---

## 🔄 **MISE À JOUR DU CODE**

### **Depuis ton Mac (développement)**

1. **Modifier le code** dans `/Users/dev/Documents/crypto/python-swing-bot/`
2. **Rebuild l'image** (optionnel, si tu veux pousser vers un registry)
```bash
cd /Users/dev/Documents/crypto/python-swing-bot
docker build -t crypto-bot:latest .
```

### **Sur le QNAP (mise à jour)**

**Option A: Copier les nouveaux fichiers**
```bash
# Depuis ton Mac
scp -r /Users/dev/Documents/crypto/python-swing-bot/* admin@IP_NAS:/share/Container/crypto-bot/

# Sur le QNAP
cd /share/Container/crypto-bot
docker-compose down
docker-compose up -d --build
```

**Option B: Utiliser un registry Docker (avancé)**
```bash
# Sur ton Mac
docker tag crypto-bot:latest ton-registry/crypto-bot:latest
docker push ton-registry/crypto-bot:latest

# Sur le QNAP
cd /share/Container/crypto-bot
docker-compose pull
docker-compose up -d
```

---

## 📁 **STRUCTURE DES FICHIERS**

```
/share/Container/crypto-bot/
├── Dockerfile              # Définition de l'image Docker
├── docker-compose.yml      # Configuration des services
├── requirements.txt        # Dépendances Python
├── config.yaml             # Configuration du bot
├── strategies.yaml         # Stratégies
├── bot/                    # Code du bot
│   └── ...                 # Modules Python
├── data/                   # Données persistantes (bougies, etc.)
├── logs/                   # Logs des trades
├── state/                  # État du bot
└── reports/                # Rapports générés
```

---

## 🎯 **STRATÉGIES ACTIVES**

| Conteneur | Paire | Stratégie | Commande |
|-----------|-------|-----------|----------|
| `crypto-bot-btc` | BTC-USDC | `bull_rider_optimized_6h` | `python -m bot -p BTC-USDC paper --strategy bull_rider_optimized_6h` |
| `crypto-bot-eth` | ETH-USDC | `bull_rider_6h` | `python -m bot -p ETH-USDC paper --strategy bull_rider_6h` |

### **Pour changer de stratégie**

1. **Modifier** le `docker-compose.yml`
2. **Redémarrer** les conteneurs :
```bash
cd /share/Container/crypto-bot
docker-compose down
docker-compose up -d
```

---

## ⚠️ **DÉPANNAGE**

### **Problème: Conteneur ne démarre pas**
```bash
# Voir les logs
docker logs crypto-bot-btc

# Vérifier la construction
docker build -t crypto-bot:latest . 2>&1 | tail -20
```

### **Problème: Erreur de dépendances**
```bash
# Rebuild avec cache désactivé
docker-compose build --no-cache
```

### **Problème: Permission refusée**
```bash
# Vérifier les permissions
ls -la /share/Container/crypto-bot/

# Donner les permissions
chmod -R 755 /share/Container/crypto-bot/
```

### **Problème: Pas assez de mémoire**
- **Solution 1** : Augmenter la mémoire allouée à Container Station dans QNAP
- **Solution 2** : Utiliser une image plus légère (Alpine)

---

## 💡 **CONSEILS**

### **1. Sauvegarder régulièrement**
```bash
# Sauvegarder les volumes importants
cd /share/Container/crypto-bot
tar -czvf backup_$(date +%Y%m%d).tar.gz data/ logs/ state/
```

### **2. Surveiller l'espace disque**
```bash
# Voir l'espace utilisé
du -sh /share/Container/crypto-bot/*
```

### **3. Nettoyer les old images**
```bash
# Liste des images
docker images

# Supprimer les images inutilisées
docker image prune
```

### **4. Redémarrage automatique**
Les conteneurs sont configurés avec `restart: unless-stopped`, donc ils redémarrent automatiquement après un redémarrage du QNAP ou un crash.

---

## 📈 **ACCÈS AUX DONNÉES**

### **Voir les trades**
```bash
# Dans File Station
/share/Container/crypto-bot/logs/

# Ou via SSH
cat /share/Container/crypto-bot/logs/trades_BTC-USDC.csv
cat /share/Container/crypto-bot/logs/trades_ETH-USDC.csv
```

### **Voir les rapports**
```bash
# Dans File Station
/share/Container/crypto-bot/reports/
```

### **Voir l'état actuel**
```bash
cat /share/Container/crypto-bot/state/bot_state_BTC-USDC.json
cat /share/Container/crypto-bot/state/bot_state_ETH-USDC.json
```

---

## 🎉 **C'EST PRÊT !**

Tu peux maintenant :

1. ✅ **Copier** les fichiers Docker sur ton QNAP
2. ✅ **Importer** le docker-compose.yml dans Container Station
3. ✅ **Lancer** les deux bots en un clic
4. ✅ **Surveiller** via les logs

**Le bot tournera 24/7 sur ton QNAP sans que tu aies besoin de garder ton PC allumé !**

---

## 🔗 **LIENS UTILES**

- [Container Station Documentation](https://www.qnap.com/en/how-to/tutorial/article/container-station-the-best-container-management-platform)
- [Docker sur QNAP](https://wiki.qnap.com/wiki/Container_Station)
- [Docker Compose Documentation](https://docs.docker.com/compose/)

---

## 📞 **SUPPORT**

Si tu as des problèmes :
1. Vérifie que **Container Station** est bien installé
2. Vérifie que ton **QNAP a assez de ressources** (CPU, RAM, espace disque)
3. Vérifie que **Docker a les permissions** nécessaires
4. Consulte les **logs** avec `docker logs`

N'hésite pas à me demander si tu as besoin d'aide supplémentaire ! 😊
