#!/bin/bash
# Script de déploiement sur QNAP
# ============================
# Ce script permet de déployer facilement le bot sur un NAS QNAP

# Configuration
QNAP_IP="192.168.1.X"  # Remplace par l'IP de ton QNAP
QNAP_USER="admin"      # Remplace si différent
QNAP_DIR="/share/Container/crypto-bot"  # Dossier sur le QNAP

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo ""
echo -e "${GREEN}🚀 Déploiement du Bot de Trading sur QNAP${NC}"
echo "============================================"
echo ""

# Vérifier que docker-compose.yml existe
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}❌ Erreur: docker-compose.yml introuvable !${NC}"
    echo "   Exécute ce script depuis le dossier python-swing-bot"
    exit 1
fi

# Vérifier que Dockerfile existe
if [ ! -f "Dockerfile" ]; then
    echo -e "${RED}❌ Erreur: Dockerfile introuvable !${NC}"
    echo "   Exécute ce script depuis le dossier python-swing-bot"
    exit 1
fi

# Étape 1: Construire l'image Docker (optionnel)
echo -e "${YELLOW}📦 Étape 1: Construction de l'image Docker (optionnel)${NC}"
echo "   Tu peux sauter cette étape si tu préfères construire directement sur le QNAP"
echo ""
read -p "Voulez-vous construire l'image Docker localement ? (y/n) " -n 1 -r
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo -e "${GREEN}🔨 Construction de l'image...${NC}"
    docker build -t crypto-bot:latest .
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Image construite avec succès !${NC}"
    else
        echo -e "${RED}❌ Échec de la construction${NC}"
        exit 1
    fi
fi

echo ""
echo -e "${YELLOW}📁 Étape 2: Copie des fichiers vers le QNAP${NC}"
echo ""

# Vérifier que scp est disponible
if ! command -v scp &> /dev/null; then
    echo -e "${RED}❌ scp n'est pas installé !${NC}"
    echo "   Installe OpenSSH ou utilise un autre outil de copie"
    exit 1
fi

# Créer l'archive
TAR_FILE="crypto-bot-$(date +%Y%m%d-%H%M%S).tar.gz"
echo "   Création de l'archive: $TAR_FILE"
tar -czf $TAR_FILE Dockerfile docker-compose.yml DOCKER_README.md requirements.txt config.yaml strategies.yaml .env.example bot/ deploy_to_qnap.sh

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Échec de la création de l'archive${NC}"
    rm -f $TAR_FILE
    exit 1
fi

echo -e "${GREEN}✅ Archive créée !${NC}"

# Copier vers le QNAP
echo "   Copie vers $QNAP_USER@$QNAP_IP:$QNAP_DIR/"
scp $TAR_FILE $QNAP_USER@$QNAP_IP:$QNAP_DIR/

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Échec de la copie vers le QNAP${NC}"
    echo "   Vérifie:"
    echo "   - L'IP du QNAP"
    echo "   - Le nom d'utilisateur"
    echo "   - Que le QNAP est allumé et connecté au réseau"
    rm -f $TAR_FILE
    exit 1
fi

echo -e "${GREEN}✅ Fichiers copiés vers le QNAP !${NC}"
rm -f $TAR_FILE

echo ""
echo -e "${YELLOW}🏗️  Étape 3: Configuration sur le QNAP${NC}"
echo ""
echo "   Connecte-toi à ton QNAP et exécute ces commandes :"
echo ""
echo "   1. Ouvre un terminal SSH ou utilise Container Station"
echo "   2. Extraire l'archive :"
echo "      cd $QNAP_DIR"
echo "      tar -xzf $TAR_FILE"
echo "   3. Créer les dossiers de persistance :"
echo "      mkdir -p $QNAP_DIR/data $QNAP_DIR/logs $QNAP_DIR/state $QNAP_DIR/reports"
echo "   4. Supprimer l'archive :"
echo "      rm $TAR_FILE"
echo ""
echo "   5. Dans Container Station :"
echo "      - Clique sur 'Create' → 'Import from docker-compose.yml'"
echo "      - Sélectionne $QNAP_DIR/docker-compose.yml"
echo "      - Clique sur 'Deploy'"
echo ""
echo -e "${GREEN}✨ Déploiement terminé !${NC}"
echo ""
echo "   Tes bots BTC et ETH devraient maintenant tourner sur ton QNAP !"
echo "   Vérifie avec : docker ps"
echo ""

# Option: Lancer automatiquement via SSH
read -p "Voulez-vous lancer automatiquement les conteneurs via SSH ? (y/n) " -n 1 -r
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo -e "${GREEN}🚀 Lancement automatique...${NC}"
    ssh $QNAP_USER@$QNAP_IP "cd $QNAP_DIR && docker-compose up -d"
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Conteneurs lancés !${NC}"
        echo ""
        echo "   Pour voir les logs :"
        echo "   - BTC: docker logs crypto-bot-btc -f"
        echo "   - ETH: docker logs crypto-bot-eth -f"
    else
        echo -e "${RED}❌ Échec du lancement${NC}"
        echo "   Vérifie la configuration et essaie manuellement"
    fi
fi

echo ""
echo -e "${GREEN}🎉 Terminé ! Ton bot tourne maintenant sur ton QNAP !${NC}"
