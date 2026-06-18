# Carteira do Luca — site

Site que consolida a carteira **Brasil (XP Investimentos)** + **EUA (XP Global)** e
atualiza sozinho a partir do upload do relatório.

## Como abrir o site
Dê **duplo-clique em `iniciar.command`** (abre no navegador em `http://127.0.0.1:8848/`).
Para parar, feche a janela do Terminal que abrir.

## Como atualizar a carteira
1. No site, clique em **"Atualizar carteira"**.
2. Suba o **PDF da XPerformance** (relatório BR da XP).
3. Suba o **PDF do XP Global** (relatório EUA — no portal web: Imprimir → Salvar como PDF).
   ⚠️ **Antes de imprimir, expanda/role a seção _Equities_** até aparecerem **todas** as ações,
   senão o PDF corta alguns ativos. O sistema **avisa** se a soma não bater com o subtotal.
4. Câmbio: deixe em branco para usar a cotação que vem no próprio PDF do XP Global
   (ou informe manual / busque a atual). Bitcoin é opcional.
5. Clique em processar — o dashboard se atualiza e guarda o mês no histórico.

## O que está automático hoje
- ✅ **Brasil:** lido 100% automático do PDF da XPerformance (posição, rentabilidade, histórico).
- ✅ **EUA:** lido automático do PDF do XP Global (Equities, Mutual Funds, Bonds, Cash) +
  cotação do dólar do próprio PDF. Validação automática contra os subtotais de cada seção.

## Estrutura
- `backend/parser_br.py` — leitor do PDF XPerformance (BR)
- `backend/us_data.py` — posição EUA (XP Global)
- `backend/categorias.py` — categorias, metas e regras de classificação
- `backend/consolidate.py` — junta tudo em R$ e monta a carteira
- `backend/app.py` — servidor (API + páginas)
- `frontend/` — dashboard e tela de atualização
- `backend/storage/` — snapshots mensais (histórico)

## Próximos passos possíveis
- Leitura automática do PDF do XP Global (EUA).
- Publicar online com login (acesso por link / o cliente acessa).
- Série histórica de patrimônio incluindo o lado EUA.
- Exportar PDF do relatório para enviar ao cliente.
