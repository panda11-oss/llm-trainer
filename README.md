# llm-trainer

技術記事・ドキュメントを複数のソースから自動収集し、ベクトルDB（ChromaDB）に蓄積、Open WebUIのナレッジベースへ自動反映する個人用RAG（Retrieval-Augmented Generation）パイプラインです。**FastAPI + React + ChromaDB** 構成で、収集ダッシュボードをWeb UIから操作できます。

## 実行環境

**現在は `homelab-main`（自宅Linuxサーバー）上でDockerコンテナとして常時稼働しています。** Ansibleでプロビジョニングされており、Tailscale経由（MagicDNSホスト名 `homelab-main.tail043c04.ts.net`）でLAN外からもアクセス可能です。

> ⚠️ 元々はWindows PC上のDocker Desktopで稼働させる想定で作られた機能（後述の「収集後自動シャットダウン」など）が一部残っています。homelab-main環境ではその前提が成立しない箇所があるため、[シャットダウン機能について](#シャットダウン機能について実装の実態)を必ず確認してください。

---

## ディレクトリ構成

```
llm-trainer/
├── docker-compose.yml      # api / frontend / chromadb の3サービスを定義
├── Dockerfile               # api サービス（FastAPI）のビルド定義
├── .env                     # APIキー・Webhook URLなど（gitignore対象、Ansibleで配置）
├── app_data/                 # api コンテナの永続データ（settings.json / logs.db / shutdown.flag 等）
├── chromadb_data/             # ChromaDBの永続データ
├── src/
│   ├── api.py                # FastAPIアプリ本体。全APIエンドポイント・スケジューラ・Discord通知・シャットダウン処理を集約
│   ├── db.py                  # ChromaDBクライアント（保存・検索・統計）
│   └── collectors/            # データソースごとの収集ロジック
│       ├── github.py           # GitHub トレンドリポジトリ
│       ├── qiita.py            # Qiita 記事
│       ├── zenn.py             # Zenn 記事（RSS）
│       ├── stackoverflow.py    # Stack Overflow 質問
│       ├── hackernews.py       # Hacker News トップ記事
│       ├── wikipedia.py        # Wikipedia 記事
│       ├── devto.py            # Dev.to 記事
│       ├── archwiki.py         # Arch Wiki 記事
│       ├── manpages.py         # Linuxコマンドのman page
│       └── serper.py           # Serper API（Web検索、キーワード都度収集時のみ使用）
└── frontend/
    ├── src/App.jsx             # UI全体（ダッシュボード/データソース/収集ログ/データ閲覧/設定の5タブ、単一ファイル）
    ├── src/main.jsx             # Reactエントリポイント
    └── vite.config.js           # Vite開発サーバ設定（Tailscaleホスト名を許可）
```

**補足**：`main.py` という名前のファイルは存在しません（Pythonエントリポイントは `src/api.py` で、`uvicorn src.api:app` として直接起動）。`.bat` スクリプト（`llm-trainer-start.bat` 等）もリポジトリ内には存在しません。

---

## 画面構成（フロントエンド）

React製SPA（`frontend/src/App.jsx`）で、上部ナビゲーションから5タブを切り替えます。

| タブ | 内容 |
|---|---|
| **ダッシュボード** | 総ドキュメント数・アクティブソース数・コレクション数・ログ件数のKPI表示、キーワード都度収集、ソース別ドキュメント数グラフ（recharts）、全ソース一括収集ボタン、収集進捗バー、最新ログ5件のプレビュー |
| **データソース** | 収集対象9ソース（GitHub / Qiita / Zenn / Stack Overflow / HackerNews / Wikipedia / Dev.to / Arch Wiki / Man Pages）の有効状態とソースごとの保存件数一覧、キーワード都度収集フォーム |
| **収集ログ** | 過去の収集結果ログ（成功/エラー、件数、メッセージ）の一覧表示、手動収集実行、ログ全クリア |
| **データ閲覧** | ChromaDBに対する全文（ベクトル）検索。キーワードを入力するとタイトル・出典・URL・取得日を一覧表示 |
| **設定** | スケジュール設定（取得時刻・リトライ回数・タイムアウト・タイムゾーン）、DB情報表示、**収集後自動シャットダウンのON/OFF**、タグセット管理（収集対象タグのカテゴリ分け・複数タグセットの有効化） |

ヘッダー右上には常時「🔴 シャットダウン」ボタンがあり、即時シャットダウン要求を送信できます（実際の挙動は後述）。

---

## docker-compose.yml の構成

```yaml
services:
  chromadb:   # ベクトルDB本体
  api:        # FastAPIバックエンド
  frontend:   # Vite開発サーバ（React）
```

### `chromadb`
- イメージ：`chromadb/chroma:latest`（公式イメージ、ビルドなし）
- 役割：記事本文のベクトル埋め込み・保存・類似検索を担うリトリーバルエンジン
- ボリューム：`./chromadb_data:/chroma/chroma`（DBファイルの永続化）
- 環境変数：`ANONYMIZED_TELEMETRY=false`（Chroma社への利用統計送信を無効化）
- ポート：`8000:8000`

### `api`
- ビルド：ローカル `Dockerfile`（`python:3.12-slim` ベース、FastAPI + uvicorn + apscheduler + chromadb + beautifulsoup4等）
- 役割：各ソースからの収集処理、ChromaDBへの保存、定期収集スケジューラ（APScheduler）、Discord通知、Open WebUIナレッジベース更新、設定・ログ・シャットダウンフラグの管理API
- ボリューム：
  - `./src:/app/src` — ソースコードをマウント（コード変更が即時反映される開発向け構成）
  - `./.env:/app/.env` — 環境変数ファイル
  - `./app_data:/app/data` — 設定（`settings.json`）、収集ログDB（`logs.db`）、タグセット（`tagsets.json`）、シャットダウンフラグ（`shutdown.flag`）などの永続データ
- 環境変数：`env_file: .env`（各種APIキー・Webhook URL）、`TZ=Asia/Tokyo`（コンテナのタイムゾーンをホストOSに依存せず固定）
- ポート：`8001:8001`
- `depends_on: chromadb`

### `frontend`
- イメージ：`node:24-slim`（ビルド済みイメージではなく、コンテナ起動時に `npm install --no-bin-links && npm run dev` を実行する開発サーバ構成）
- 役割：React SPAのVite開発サーバ配信
- ボリューム：`./frontend:/app`（フロントエンドのソース一式をマウント、ホットリロード対応）
- ポート：`5174:5174`
- 本番ビルド（`vite build`）や静的配信用の構成は現状 compose に含まれていません

### `.env` に定義される主な変数
`GITHUB_TOKEN`, `QIITA_TOKEN`, `OPENWEBUI_URL`, `OPENWEBUI_API_KEY`, `OPENWEBUI_KNOWLEDGE_ID`, `SERPER_API_KEY`, `DISCORD_WEBHOOK_URL`

---

## シャットダウン機能について（実装の実態）

⚠️ **設定の「収集後自動シャットダウン」およびヘッダーの「シャットダウン」ボタンは、いずれもPCを直接シャットダウンさせるコードを持っていません。** `os.system("shutdown ...")` のようなOSコマンド実行、WinRM/SSH/Tapo APIなどの外部制御は一切実装されておらず、やっていることは以下だけです。

- `POST /api/shutdown`（即時シャットダウン要求）／定期収集完了後に `auto_shutdown` 設定がONの場合 → `app_data/shutdown.flag` というファイルに `"shutdown"` という文字列を書き込むだけ
- `DELETE /api/shutdown` → そのフラグファイルを削除するだけ
- フロントエンドは「60秒後にシャットダウンします」という確認ダイアログを出しますが、**実際に60秒待ってから何かを実行する処理はどこにも存在しません**

つまり、**このリポジトリの中だけでは何も物理的に起こりません。** `shutdown.flag` の出現を監視して実際に電源を落とす役目は、リポジトリ外の仕組み（ホストOS側の監視スクリプトやタスク）に委ねられている設計ですが、そのようなスクリプトは現在このリポジトリには含まれていません。

### homelab-main環境での注意点
- Windows PC + Docker Desktopを前提にした「離席中に収集が終わったらPCを消す」という運用を想定して作られた機能ですが、現在の homelab-main は**常時稼働のホームサーバー**であり、他のAnsible管理下サービスも同居している可能性があります。
  - もし homelab-main 側に `shutdown.flag` を検知して `shutdown` を実行する仕組み（cron / systemdタイマー等）が残っている場合、「収集後自動シャットダウン」をONにすると**サーバー全体が落ち、同居する他サービスも巻き添えで停止する**リスクがあります。
  - そのような仕組みが存在しない（＝移行時に廃止された）場合は、この機能は**見た目だけ動くダミー**（フラグファイルが作られるだけで何も起きない）になっています。
- どちらの状態であるかは、このリポジトリだけでは判別できません。homelab-main側のcron / systemd / Ansible playbookを確認するまでは、**「収集後自動シャットダウン」をONにしない**ことを推奨します。

---

## Discord通知について

`src/api.py` の `notify_discord()` が、`DISCORD_WEBHOOK_URL` が設定されていれば以下のタイミングでWebhook通知を送ります。

| 通知 | 実際のトリガー |
|---|---|
| 🖥️ 起動しました | **PCの電源投入ではなく**、`api` コンテナ（FastAPIプロセス）の起動時。`docker compose up` / `restart` / 再デプロイのたびに発火する |
| 🔄 収集開始 / ✅⚠️ 収集完了 | APSchedulerによる定期収集ジョブの開始・終了 |
| 🔴 リモートシャットダウン | `POST /api/shutdown` 呼び出し時（実際の電源断は伴わない） |
| 🟢 シャットダウンキャンセル | `DELETE /api/shutdown` 呼び出し時 |

「PCシャットダウン時」に対応する通知は存在しません。また「起動しました」通知は**PCの起動イベントではなくコンテナプロセスの起動イベント**を検知しているため、homelab-mainのようにAnsibleで頻繁に再デプロイ・再起動される環境では、想定より高頻度に通知が飛ぶ可能性があります。

---

## 起動・停止・デプロイ手順

### 現状の運用（homelab-main / Ansible）
本番相当の環境は Ansible が管理しており、**このリポジトリを `git clone` してAnsible経由でデプロイする方式**が前提です。手動でファイルを配置する運用は想定されていません。

1. Ansible playbook が homelab-main 上に本リポジトリを `git clone`（または `git pull` で更新）
2. `.env` ファイルは Ansible側で配置（各種APIキー・Discord Webhook URLを含むためリポジトリにはコミットしない）
3. `docker compose up -d` でコンテナ群を起動
4. 以降のコード更新は、Ansible playbook の再実行（`git pull` → `docker compose up -d --build`相当）で反映

### 手動での起動・停止（開発・検証用）
```bash
# 起動（初回はイメージビルドも実行される）
docker compose up -d

# ログ確認
docker compose logs -f api

# 停止
docker compose down

# コード変更後の再ビルド（api の Dockerfile 依存パッケージを変更した場合）
docker compose up -d --build api
```

- `api` と `frontend` はソースディレクトリをボリュームマウントしているため、`src/` や `frontend/src/` の変更はコンテナ再起動なしで反映されます（`frontend` はVite HMR、`api` はuvicornの自動リロードには未対応な点に注意 — コード変更を確実に反映するには `docker compose restart api` を推奨）。
- アクセスURL：フロントエンド `http://<host>:5174`、API `http://<host>:8001`、ChromaDB `http://<host>:8000`
- フロントエンドのAPI接続先は `window.location.hostname` を動的に使用するため、`localhost` でも Tailscaleホスト名でも同じビルドでアクセス可能です。

---

## 既知の不整合・注意点まとめ

このプロジェクトはWindows PC + Docker Desktop稼働を前提にした機能を残したまま、homelab-main（Linuxサーバー）上のコンテナ運用に移行しています。以下は移行に伴い挙動が変わりうる、または矛盾しうる箇所です。

1. **収集後自動シャットダウン／リモートシャットダウン**：`shutdown.flag` を作るだけで完結しており、実際の電源制御は別途ホスト側の仕組みが必要。homelab-main側にその仕組みが残っているかどうか未確認（[上記参照](#シャットダウン機能について実装の実態)）。ONにする前に必ず確認すること。
2. **「起動しました」Discord通知**：PCの電源投入ではなく `api` コンテナのプロセス起動を検知している。Ansibleによる再デプロイのたびに発火するため、Windows PC運用時とは通知の意味合いが変わっている。
3. **frontendサービスは開発サーバ構成のまま**：`vite build` による本番ビルド・静的配信ではなく、`npm run dev` を常時起動する構成。常時稼働のhomelab-main上でこの構成を続けることの妥当性（リソース消費・安定性）は要検討。
4. **`api` の `env_file`／`.env` マウント**：APIキーを含む `.env` がホストのファイルシステム上に平文で存在する前提。homelab-main上でのファイルパーミッション・アクセス制御はAnsible側の管理に依存する。
