# Publicar o site de graça (Supabase + Render)

Tempo: ~15 min. Custo: R$ 0. Nenhum dos dois pede cartão.

Você vai criar **2 contas gratuitas** e conectar tudo. Pode usar o login do GitHub
nas duas pra ser mais rápido.

---

## Parte 1 — Banco de dados (Supabase) — guarda a memória da carteira

1. Acesse **https://supabase.com** → **Start your project** → entre com o GitHub.
2. **New project**:
   - Name: `carteira-luca`
   - Database Password: **crie uma senha e ANOTE** (vai usar já já)
   - Region: **South America (São Paulo)** se aparecer
   - Plan: **Free**
   - Clique em **Create new project** e espere ~2 min (ele provisiona).
3. Quando terminar, clique na engrenagem **Project Settings** (canto inferior esquerdo)
   → **Database** → seção **Connection string** → aba **URI**.
4. **Copie** a string. Ela é parecida com:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.xxxxxxxx.supabase.co:5432/postgres
   ```
   Troque `[YOUR-PASSWORD]` pela senha que você anotou no passo 2.
   👉 Guarde essa string completa — é o seu **DATABASE_URL**.

---

## Parte 2 — Publicar o site (Render)

1. Acesse **https://render.com** → **Get Started** → entre com o GitHub.
2. Autorize o Render a ver seus repositórios (pode dar acesso só ao `carteira-luca`).
3. No painel: **New +** → **Blueprint**.
4. Selecione o repositório **carteira-luca** → **Connect**.
   (O Render lê o arquivo `render.yaml` automaticamente.)
5. Ele vai pedir 2 informações (as variáveis secretas):
   - **APP_PASSWORD** = a senha que VOCÊ quer usar pra entrar no site (escolha uma)
   - **DATABASE_URL** = a string do Supabase (Parte 1, passo 4)
6. Clique em **Apply** / **Create**. O Render vai construir e publicar (~3-5 min).
7. Pronto! Você recebe um endereço tipo:
   ```
   https://carteira-luca.onrender.com
   ```
   Abra, entre com a sua **APP_PASSWORD**, e faça o upload dos PDFs em **Atualizar carteira**.

---

## Observações
- **Plano grátis "dorme":** depois de ~15 min sem uso, o site hiberna. No primeiro
  acesso seguinte ele demora ~30-50s pra acordar — depois fica rápido. Normal.
- O banco de tabelas é criado sozinho no primeiro acesso.
- Para **trocar a senha** depois: Render → seu serviço → **Environment** → edite
  `APP_PASSWORD` → Save (ele republica sozinho).
- **Atualizações de código** que eu fizer: é só eu dar `git push` e o Render
  republica automático.

## Se algo der errado
- Render → seu serviço → aba **Logs**: mostra o erro. Me mande o que aparecer.
- Erro de banco normalmente é o `DATABASE_URL` com a senha errada/não substituída.
