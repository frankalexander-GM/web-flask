#!/bin/bash
# Sube web-flask a un repo NUEVO de GitHub llamado "web-flask".
# Uso:  ./push-to-github.sh TU_TOKEN_DE_GITHUB
# El token necesita permiso "repo". Créalo en:
#   https://github.com/settings/tokens?type=beta  (classic → scope repo)
#
# ⚠️ NUNCA pegues el token en el código ni lo subas a ningún repo.
set -e
TOKEN="${1:?Uso: ./push-to-github.sh TU_TOKEN_DE_GITHUB}"
REPO_NAME="web-flask"
BRANCH="main"

echo "── 1. Creando repo $REPO_NAME en GitHub…"
HTTP=$(curl -s -o /tmp/gh-resp.json -w "%{http_code}" \
  -H "Authorization: token $TOKEN" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/user/repos \
  -d "{\"name\":\"$REPO_NAME\",\"description\":\"DevPlay Flask — red social para devs indie (Python + Flask)\",\"private\":false}")
if [ "$HTTP" = "201" ]; then
  echo "   ✅ Repo creado"
elif [ "$HTTP" = "422" ]; then
  echo "   ℹ️  El repo ya existía, sigo con él"
else
  echo "   ❌ Error $HTTP:"; cat /tmp/gh-resp.json; exit 1
fi

echo "── 2. Conectando remote…"
USER=$(curl -s -H "Authorization: token $TOKEN" https://api.github.com/user | python3 -c "import sys,json;print(json.load(sys.stdin)['login'])")
if git remote get-url origin >/dev/null 2>&1; then
  git remote set-url origin "https://$USER:$TOKEN@github.com/$USER/$REPO_NAME.git"
else
  git remote add origin "https://$USER:$TOKEN@github.com/$USER/$REPO_NAME.git"
fi

echo "── 3. Empujando $BRANCH…"
git push -u origin "$BRANCH"
echo "✅ Listo: https://github.com/$USER/$REPO_NAME"
echo "💡 Si el token quedó en la URL del remote, límpialo con:"
echo "   git remote set-url origin https://github.com/$USER/$REPO_NAME.git"
