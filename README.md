# Vendas & Tratativas

Ferramenta para **Mayara Barros** registrar vendas e tratativas, com visão estratégica para apoio ao time comercial e conversão.

## Uso recomendado (celular sem PC ligado)

Leia o guia **[COMO-USAR-NA-NUVEM.md](COMO-USAR-NA-NUVEM.md)** — hospedagem grátis (Render + Supabase), link fixo no celular, dados sempre disponíveis.

## Segurança e persistência

- **Rede local** — PC (`127.0.0.1`) e celulares na mesma Wi-Fi (IP do PC, ex.: `http://192.168.1.10:5050`)
- Não fica exposto na internet pública
- **Senha opcional** via arquivo `.env`
- Banco **SQLite** com modo WAL e `synchronous=FULL` (menor risco de perda em queda de energia)
- **Backups automáticos** em `data/backups/` antes de inicialização e exportações
- Botão **Backup** no menu gera cópia `.db` + snapshot `.json`
- Pasta `data/` fora do Git (dados sensíveis permanecem na máquina)

## Campos — Tratativas

| Campo | Descrição |
|-------|-----------|
| Data | Automática (data e hora do registro) |
| ID | Automático e sequencial |
| Setor | Logística, Compras, Financeiro, TI Infra, TI Sistemas |
| Situação | Lista conforme planilha original |
| Tempo de solução | Faixas (> 30 min, > 1 h, etc.) |
| Impacto R$ | Valor financeiro |
| Status | Resolvido com/sem impacto, em andamento, etc. |
| Observação | Texto livre |

## Campos — Vendas

| Campo | Descrição |
|-------|-----------|
| Data | Automática |
| Pedido | Número do pedido |
| Valor | Valor em R$ |
| Convertido | Sim/Não |
| ID da perda | Vínculo com tratativa (#ID) |

## Como executar

```powershell
cd "c:\Users\wsana\Projeto python\Vendas & Tratativas"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python run.py
```

- **No PC:** http://127.0.0.1:5050  
- **No celular:** mesma rede Wi-Fi → use o IP exibido ao rodar `iniciar.bat` (ex.: http://192.168.0.15:5050)

### Usuários de acesso

| Perfil | Nome | Senha | Função |
|--------|------|-------|--------|
| Operacional | **Mayara Barros** | `mayara` | Acompanha clientes e fecha negócios com vendedores |
| Gestor | **Willame Sousa** | `161217` | Acompanha números e também pode registrar no sistema |

**Vendas** = acompanhamento comercial e conversão. **Tratativas** = problemas internos da empresa. Venda perdida deve vincular o **ID da tratativa** (origem do impacto).

## Estrutura

```
app/           # Lógica Flask, serviços, banco
templates/     # Telas HTML
static/        # CSS e JS
data/          # Banco e backups (criado ao rodar)
run.py         # Inicialização
```

## Atualizações da ferramenta

Ao atualizar o código, **não apague** a pasta `data/`. O banco `vendas_tratativas.db` mantém todos os registros. Faça backup pelo botão no app antes de atualizações grandes.
