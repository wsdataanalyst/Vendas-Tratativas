# Colocar o projeto no GitHub

O Git já está inicializado nesta pasta. Falta criar o repositório no GitHub e enviar o código.

## Forma mais rápida (automático)

1. Instale o GitHub CLI (se não tiver): `winget install GitHub.cli`
2. Dê dois cliques em **`criar-repo-github.bat`**
3. Na primeira vez, faça login no navegador quando pedir
4. Pronto — o script cria o repo **vendas-tratativas** (privado) e envia o código

---

## Forma manual

### Passo 1 — Criar repositório no GitHub

1. Acesse [github.com/new](https://github.com/new)
2. Nome sugerido: `vendas-tratativas`
3. **Private** (recomendado — dados comerciais)
4. **Não** marque "Add README" (já temos arquivos)
5. Clique em **Create repository**

## Passo 2 — Conectar e enviar (no terminal desta pasta)

Seu usuário: **wsdataanalyst**

```powershell
cd "c:\Users\wsana\Projeto python\Vendas & Tratativas"

git remote add origin https://github.com/wsdataanalyst/vendas-tratativas.git

git push -u origin main
```

Repositório: https://github.com/wsdataanalyst/vendas-tratativas

Se pedir login, use seu usuário GitHub e um **Personal Access Token** como senha (não use a senha da conta).

Criar token: GitHub → Settings → Developer settings → Personal access tokens → Generate new token (marque `repo`).

## Passo 3 — Render (deploy na nuvem)

Depois que o código estiver no GitHub:

1. [render.com](https://render.com) → **New** → **Blueprint**
2. Conecte o GitHub e escolha o repositório `vendas-tratativas`
3. Informe `DATABASE_URL` (Supabase) quando pedir
4. Deploy

---

## Comandos úteis depois

```powershell
git status
git add .
git commit -m "Descrição da alteração"
git push
```

**Nunca** envie o arquivo `.env` (senhas) — ele já está no `.gitignore`.
