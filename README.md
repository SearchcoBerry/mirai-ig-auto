# 未来探究ゼミ Instagram 自動投稿

毎日19:00（日本時間）に、`queue.json` の先頭から未投稿の1件をカルーセル（画像3枚）で投稿します。GitHub Actions が実行するので、パソコンを開いていなくても投稿されます。費用はかかりません。

投稿が尽きるとジョブが失敗し、GitHubからメールが届きます。残り3件以下になった日は、ログに警告が出ます。

## 中身

| ファイル | 役割 |
|---|---|
| `queue.json` | 投稿の一覧。公開順に14件入っています。投稿するとこのファイルに日時が記録されます |
| `images/` | 投稿画像42枚（1080×1350のJPEG） |
| `scripts/post.py` | 投稿の処理 |
| `.github/workflows/post.yml` | 毎日の実行設定 |

## 準備（30分ほど）

### 1. GitHubに公開リポジトリを作る

画像を `https://raw.githubusercontent.com/...` で配信するため、リポジトリは **Public** にしてください。非公開だと画像URLをMetaが取得できません。アクセストークンはSecretsに入れるので、リポジトリが公開でも漏れません。

このフォルダの中身をそのままpushします。

```
git init
git add .
git commit -m "Instagram 自動投稿"
git branch -M main
git remote add origin https://github.com/<あなた>/<リポジトリ名>.git
git push -u origin main
```

### 2. Metaの設定

1. [Meta for Developers](https://developers.facebook.com/) でアプリを作る（タイプ：ビジネス）。
2. Meta Business Suite の「ビジネス設定 → ユーザー → システムユーザー」でシステムユーザーを作る。
3. そのシステムユーザーに、Facebookページと Instagram アカウントを資産として割り当てる。
4. トークンを生成する。権限は `instagram_basic`、`instagram_content_publish`、`pages_show_list`、`pages_read_engagement`。
   - **システムユーザーのトークンには期限がありません。** 個人のユーザートークンを使うと60日で切れて投稿が止まるので、システムユーザーを使ってください。
5. Instagram のアカウントIDを調べる。

```
curl "https://graph.facebook.com/v21.0/me/accounts?access_token=<トークン>"
# 返ってきたページIDを使って
curl "https://graph.facebook.com/v21.0/<ページID>?fields=instagram_business_account&access_token=<トークン>"
```

`instagram_business_account.id` が次に使うIDです。

### 3. GitHubにSecretsを登録する

リポジトリの Settings → Secrets and variables → Actions で2つ登録します。

| 名前 | 値 |
|---|---|
| `IG_USER_ID` | 手順2で調べたInstagramアカウントID |
| `IG_ACCESS_TOKEN` | システムユーザーのトークン |

### 4. テストする

Actions タブ →「Instagram 自動投稿」→ Run workflow。`dry_run` を **true** のままにすると、投稿せずに画像URLとキャプションだけ表示します。URLがブラウザで開ければ準備は完了です。

その後、`dry_run` を false にして1回実行すると、1件目（固定①）が実際に投稿されます。問題がなければ、翌日から毎日19:00に自動で動きます。

## よく使う操作

- **投稿を追加する**：`queue.json` の末尾に `{"id": "...", "title": "...", "images": ["..."], "caption": "...", "posted_at": null, "media_id": null}` を足し、画像を `images/` に置く。
- **順番を変える**：`queue.json` の並びを入れ替える。上から順に投稿されます。
- **時間を変える**：`.github/workflows/post.yml` の `cron` を変える。UTC表記なので、日本時間から9時間引いた値を書きます（例：21:00 JST → `0 12 * * *`）。
- **1日休む**：Actions タブから workflow を Disable する。

## 制限

- APIからの投稿は24時間あたり50件まで。1日1件なら問題ありません。
- 画像はJPEGのみ。PNGは投稿できません。
- cronの実行時刻は、GitHubの混雑状況で数分〜十数分ずれることがあります。
- 固定投稿（①②③）は投稿後、Instagramアプリから手動でプロフィールに固定してください。固定操作はAPIではできません。
