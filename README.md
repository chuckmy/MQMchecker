# MQM Translation Checker

OpenAIを用いて、原文と訳文を[MQM（Multidimensional Quality Metrics）](https://themqm.org/)の観点でレビューするシンプルなWebアプリ。社内向けの翻訳品質チェックに利用することを想定しています。

## 構成

- **バックエンド**: FastAPI (`main.py`) — OpenAIのResponses APIをJSON Schemaつきで呼び出し、構造化されたレビュー結果を返す
- **フロントエンド**: 単一HTML (`index.html`) — ブラウザでフォーム入力し、バックエンドを呼び出して結果を表示
- **認証**: HTTP Basic認証（全エンドポイント）
- **デプロイ**: Render（Python 3 / Free Instance）

## エンドポイント

| Method | Path | 説明 |
|---|---|---|
| POST | `/review` | レビュー結果をJSONで返す |
| POST | `/review/csv` | レビュー結果（issues一覧）をCSVで返す |

いずれも以下のJSONを受け取ります：

```json
{
  "source_text": "原文",
  "target_text": "訳文",
  "purpose": "社内情報共有",
  "audience": "ITエンジニア",
  "tone": "自然で明確",
  "terminology_policy": "特になし",
  "priority": "内容把握とAccuracy重視"
}
```

レスポンスには `assumptions` / `summary` / `issues` / `revised_translation` が含まれます（JSON Schema準拠）。

## 必要な環境変数

`.env.example` を参考に `.env` を作成するか、デプロイ先で環境変数として設定してください。

| Key | 説明 |
|---|---|
| `OPENAI_API_KEY` | OpenAI APIキー |
| `APP_USER` | Basic認証のユーザー名 |
| `APP_PASSWORD` | Basic認証のパスワード |

## ローカルで動かす

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # 中身を自分の値に書き換える
uvicorn main:app --reload
```

サーバーが `http://127.0.0.1:8000` で起動します。`index.html` 内の `API_BASE` をローカル検証用に `http://127.0.0.1:8000` に変更してブラウザで開いてください。

## デプロイ（Render）

1. このリポジトリをGitHubにpush
2. Renderで **New → Web Service** からリポジトリを連携
3. 以下を設定
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: Free
4. Environment Variables に `OPENAI_API_KEY` / `APP_USER` / `APP_PASSWORD` を登録
5. Create Web Service → 発行されたURL（例: `https://xxx.onrender.com`）を `index.html` の `API_BASE` に反映
6. `index.html` のみを社内Dropbox等で配布

> Free Instanceは15分のアイドルでスリープし、次の初回リクエストに最大50秒程度かかります。

## ファイル構成

```
.
├── main.py             # FastAPIバックエンド
├── index.html          # フロントエンド（単一HTML）
├── requirements.txt    # Python依存
├── Procfile            # Renderのstart command
├── .env.example        # 環境変数テンプレ
├── .gitignore          # .env/.venv等を除外
└── README.md
```

## セキュリティ上の注意

- `.env` は絶対にコミットしない（`.gitignore`で除外済み）
- 配布するのは `index.html` のみ。`main.py` やAPIキーは配らない
- Basic認証の認証情報は社内でのみ共有し、必要に応じてRender側で変更
- OpenAI APIキーは定期的にローテーションすることを推奨

## ライセンス

社内利用を想定した個人プロジェクト。再配布・商用利用時は要相談。
