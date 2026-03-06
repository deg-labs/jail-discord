# Discord 自動ロール付与バッチ

このBotは定期バッチでサーバーメンバーを走査し、条件に一致したユーザーへロールを付与します。

## 機能

- 既定で5分ごと（`AUTO_ROLE_INTERVAL_MINUTES`）に全メンバーを取得
- 次の **いずれか** を満たすユーザーに `testrole`（`AUTO_ROLE_TARGET_ROLE`）を付与
1. ユーザー名または表示名に `deg5`（`AUTO_ROLE_TARGET_KEYWORD`）を含む
2. アイコン画像がほぼ真っ黒、またはほぼ透過
- `AUTO_ROLE_EXCLUDED_USER_IDS` に指定したユーザーIDは常に除外

## 必要な環境変数

- `DISCORD_BOT_TOKEN`（必須）
- `PORT`（既定: `8080`）
- `AUTO_ROLE_TARGET_ROLE`（既定: `testrole`）
- `AUTO_ROLE_TARGET_KEYWORD`（既定: `deg5`）
- `AUTO_ROLE_EXCLUDED_USER_IDS`（既定: 空、カンマ区切りで複数指定）
- `AUTO_ROLE_INTERVAL_MINUTES`（既定: `5`）
- `AUTO_ROLE_BLACK_LUMINANCE_THRESHOLD`（既定: `8`）
- `AUTO_ROLE_BLACK_RATIO_THRESHOLD`（既定: `0.98`）
- `AUTO_ROLE_TRANSPARENT_ALPHA_THRESHOLD`（既定: `16`）
- `AUTO_ROLE_TRANSPARENT_RATIO_THRESHOLD`（既定: `0.98`）
- `AUTO_ROLE_VERBOSE_LOGGING`（既定: `true`）

## Discord Bot 側で必要な設定

1. Developer Portal の対象アプリで `Server Members Intent` を ON にする  
2. Bot をサーバーへ招待する際、`ロールの管理 (Manage Roles)` 権限を付与する  
   Permissions Integer: `268435456`
3. Discordサーバー内で、Botロールを付与対象ロール（例: `testrole`）より上に配置する  
   ロール階層が逆だと付与できません

## ローカル起動（Docker Compose）

1. `.env.example` を `.env` にコピー
2. `.env` に値を設定
3. 起動

```bash
docker compose up --build
```

停止:

```bash
docker compose down
```

## ログ確認

```bash
docker compose logs -f jail-discord
```

`AUTO_ROLE_VERBOSE_LOGGING=true` のとき、判定理由（`keyword_only` / `avatar_only` / `no_or_match` など）を詳細表示します。

## 構成

- `main.py`: Bot起動とヘルスチェックエンドポイント
- `member_role_batch/config.py`: 設定読み込み
- `member_role_batch/rules.py`: キーワード・黒/透過アイコン判定
- `member_role_batch/service.py`: 定期バッチ実行とロール付与
