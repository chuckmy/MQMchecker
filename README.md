# Reminders Review CLI

Mac の Reminders.app を読み取り、未完了タスクの偏りをレビューして 1 週間の進め方を提案する最小ツールです。

## できること

- リマインダーの一覧取得
- 期限切れタスクの抽出
- 今週締切のタスクの抽出
- 高優先度なのに期限がないタスクの抽出
- 曖昧なタイトルのタスクの抽出
- 今週の進め方の簡易サジェスチョン表示
- 日ごとの 1 週間プラン表示

## 実行方法

```bash
swift run "New project"
```

初回実行時には Reminders へのアクセス許可ダイアログが表示されます。

### オプション

```bash
swift run "New project" --days 7
swift run "New project" --include-completed
swift run "New project" --json
```

## 次に足すとよいもの

- カレンダー空き時間と合わせた週次プラン提案
- タスクの所要時間推定
- リスト別の重み付け
- LLM を使った自然な週次レビュー文の生成
