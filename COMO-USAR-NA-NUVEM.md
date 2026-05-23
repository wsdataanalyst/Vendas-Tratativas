# Vendas & Tratativas — usar na nuvem (recomendado)

## Por que na nuvem?

| No PC (localhost) | Na nuvem |
|-------------------|----------|
| PC precisa estar ligado | PC pode estar desligado |
| Wi-Fi / ngrok complicado | Link fixo no celular |
| Difícil para Mayara | Abre como um site normal |

**Solução:** hospedar grátis no **Render** + banco grátis no **Supabase**.

Depois de configurado **uma vez**, Mayara e Willame só abrem o link no celular (pode salvar na tela inicial).

---

## Passo 1 — Banco de dados (Supabase, grátis)

1. Acesse [supabase.com](https://supabase.com) e crie conta
2. **New project** → escolha nome e senha do banco (anote a senha)
3. Menu **Project Settings** → **Database**
4. Em **Connection string**, copie a URI **URI** (modo `Transaction` ou `Session`)
   - Exemplo: `postgresql://postgres.xxxx:SUASENHA@aws-0-sa-east-1.pooler.supabase.com:6543/postgres`
5. Troque `[YOUR-PASSWORD]` pela senha que você criou

---

## Passo 2 — Colocar o sistema na internet (Render, grátis)

### Opção A — Com GitHub (mais estável)

1. Crie repositório no GitHub e envie esta pasta do projeto
2. Acesse [render.com](https://render.com) → cadastro grátis
3. **New** → **Blueprint** → conecte o GitHub e selecione o repositório
4. Quando pedir `DATABASE_URL`, cole a URI do Supabase
5. Deploy → aguarde alguns minutos
6. Render mostra a URL: `https://vendas-tratativas-xxxx.onrender.com`

### Opção B — Sem GitHub

1. [render.com](https://render.com) → **New** → **Web Service**
2. **Deploy an existing image** ou conecte repositório manualmente
3. Build: Docker | Start: `gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2`
4. Variáveis de ambiente:
   - `DATABASE_URL` = URI do Supabase
   - `APP_SECRET_KEY` = qualquer texto longo e aleatório
5. Criar serviço

---

## Passo 3 — Usar no celular

1. Abra a URL do Render no Chrome/Safari
2. **Mayara Barros** — senha: `mayara`
3. **Willame Sousa (Gestor)** — senha: `161217`
4. No iPhone: Compartilhar → **Adicionar à Tela de Início**
5. No Android: Menu → **Instalar app** / Adicionar atalho

Pronto: funciona como app, sem PC ligado.

---

## Plano gratuito — o que esperar

- **Render grátis:** o site “dorme” após ~15 min sem uso; a **primeira abertura** pode levar 30–60 segundos. Depois fica rápido.
- **Supabase grátis:** dados guardados com segurança; suficiente para 1–2 usuários.
- Se quiser **sempre instantâneo** (sem esperar): plano pago Render (~US$ 7/mês).

---

## Uso no PC (opcional, desenvolvimento)

- `iniciar.bat` — só na sua máquina, dados no arquivo local
- Para testar com o mesmo banco da nuvem, crie `.env` com `DATABASE_URL=...` (URI Supabase)

---

## Segurança

- Senhas Mayara e Willame continuam obrigatórias
- Use `APP_SECRET_KEY` forte no Render
- Não compartilhe a URL publicamente além da equipe

---

## Resumo

1. Supabase = onde ficam os dados (sempre ligado)
2. Render = onde roda o site (link para o celular)
3. PC desligado = tudo continua funcionando
