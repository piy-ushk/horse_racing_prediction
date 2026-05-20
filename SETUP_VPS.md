# VPS セットアップ手順 — ConoHa Windows Server

本番稼働のための手順書です。ConoHa VPS（Windows Server）上での作業を想定しています。

> **自動セットアップ (推奨):**  
> プロジェクトを `C:\keiba\horce_racing_prediction\` にコピーした後、管理者PowerShellで:
> ```powershell
> Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
> .\setup\vps_setup.ps1
> ```
> Python 32-bit・依存パッケージ・COM登録確認・デモテストまで自動実行されます。  
> 以下の手順書は各ステップの詳細説明です。

---

## 1. 前提条件の確認

| 項目 | 必要なもの |
|------|------------|
| OS | Windows Server 2019 / 2022 |
| Python | 3.11 以上 |
| JV-Link | JRA-VAN公式サイトからダウンロード・インストール済み |
| 利用キー | JRAVAN: `3UJC-3XNU-1KME-U68B-4` / UmaConn: `EMPC-3PAB-9TLY-L4UX-8` |

---

## 2. Python のインストール

> **重要:** UmaConn (NVDTLab.dll) は **32ビットDLL** です。
> UmaConn を使う場合は必ず **Python 3.11 (32ビット / x86)** をインストールしてください。
> 64ビットPythonではDLLをロードできません。

1. https://www.python.org/downloads/ → **Windows installer (32-bit)** を選択してダウンロード
2. インストール時に **「Add Python to PATH」にチェックを入れる**
3. インストール後、確認（`32 bit` と表示されること）:
   ```
   python --version
   ```

---

## 3. JV-Link / UmaConn のセットアップ

### JV-Link (JRA-VAN 中央競馬)

1. JRA-VAN Data Lab ページからJV-Linkインストーラーをダウンロード
2. インストール後、JV-Link管理画面を起動
3. **利用キー `3UJC-3XNU-1KME-U68B-4` を登録**
4. データ取得テストを実行して正常に動作することを確認
5. JRA-VANより発行される **ソフトウェアID** を `.env` の `JRAVAN_SOFTWARE_ID` に記入

### UmaConn (地方競馬DATA)

> UmaConn は **HTTPサービスではありません**。JV-Linkと同様の Windows COM DLL です。
> (`C:\Windows\SysWOW64\NVDTLab.dll` / COM ProgID: `NVDTLabLib.NVLink`)

1. 競馬最強の法則WEB（saikyo.k-ba.com）からUmaConnインストーラーをダウンロード
2. インストール後、UmaConnを**一度GUIで起動**し、利用キー `EMPC-3PAB-9TLY-L4UX-8` を登録
3. 初回セットアップを完了する（この手順を踏まないとNVInitが失敗します）
4. `C:\Windows\SysWOW64\NVDTLab.dll` が存在することを確認

---

## 4. プロジェクトの配置

```
C:\keiba\
  └── horce_racing_prediction\   ← ここにプロジェクトを配置
```

プロジェクトフォルダをVPSにコピー後:

```cmd
cd C:\keiba\horce_racing_prediction
pip install -r requirements.txt
pip install pywin32
python -m pywin32_postinstall -install
```

---

## 5. 環境変数の設定 (.env)

`.env` ファイルを開き、以下の項目を埋める:

```env
WP_BASE_URL=https://www.keiba-tips.top
WP_USERNAME=（WordPressユーザー名）
WP_APP_PASSWORD=（アプリケーションパスワード — 下記参照）
JRAVAN_LICENSE_KEY=3UJC-3XNU-1KME-U68B-4
JRAVAN_SOFTWARE_ID=（JRA-VANより発行）
UMACONN_API_KEY=EMPC-3PAB-9TLY-L4UX-8  # COM DLL経由 — URLは不要
DEMO_MODE=false
SCHEDULED_HOUR=9
SCHEDULED_MINUTE=30
```

### WordPress アプリケーションパスワードの取得

1. WordPress管理画面 → ユーザー → プロフィール
2. 「アプリケーションパスワード」セクション
3. 新しいアプリケーション名（例: `keiba-system`）を入力 → 「追加」
4. 表示されたパスワード（`xxxx xxxx xxxx xxxx xxxx xxxx` 形式）を `.env` に貼り付け

---

## 6. WordPress の設定

### 6-1. REST API の有効化

WordPress 5.6 以降はデフォルトで有効。確認:
```
https://www.keiba-tips.top/wp-json/wp/v2/
```
にアクセスして JSON が返ること。

### 6-2. 認証ゲートの設置（必須）

`wordpress-snippets/auth-gate.php` の内容を、以下のいずれかに追加:

**方法 A: functions.php に追加**
- WordPress管理画面 → 外観 → テーマエディター → functions.php
- ファイル末尾にコードを貼り付けて「ファイルを更新」

**方法 B: Must-Use プラグインとして設置（推奨）**
- FTP/SSH で `wp-content/mu-plugins/` フォルダを開く（なければ作成）
- `auth-gate.php` ファイルをそのまま配置

これにより:
- `race-` で始まるスラッグのページは `?auth=line_only` がないとトップページへリダイレクト
- 該当ページは自動的に noindex/nofollow に設定

---

## 7. 接続テスト

```cmd
cd C:\keiba\horce_racing_prediction

# WordPress接続テスト
python scripts/test_wp_connection.py

# パイプライン全体のスモークテスト（デモモード）
python scripts/test_pipeline.py

# JV-Link + UmaConn 実接続テスト（DEMO_MODE=false 設定後）
python scripts/test_connections.py

# 個別テスト
python scripts/test_connections.py --jvlink-only
python scripts/test_connections.py --umaconn-only
```

---

## 8. 本番パイプラインのテスト実行

`.env` で `DEMO_MODE=false` に設定後:

```cmd
python main.py
```

ログを確認:
```cmd
type logs\YYYY-MM-DD.log
```

---

## 9. タスクスケジューラの登録

**管理者権限でコマンドプロンプトを開き**実行:

```cmd
cd C:\keiba\horce_racing_prediction
python scheduler\setup_windows_task.py
```

確認:
```cmd
python scheduler\setup_windows_task.py --status
```

---

## 10. 管理画面（オッズ取得時刻の変更）

Flaskサーバー起動:
```cmd
python web\app.py
```

ブラウザで `http://127.0.0.1:5000/admin` を開く。

「オッズ取得時刻」を変更して「保存・タスク更新」をクリックすると:
- `data/settings.json` が更新される
- Windowsタスクスケジューラのタスクが新しい時刻で再登録される

---

## 11. LINE リッチメニューの設定

LINE公式アカウントのリッチメニューに以下URLを設定:

```
https://www.keiba-tips.top/（レースページスラッグ）/?auth=line_only
```

例（今日の東京1Rの場合）:
```
https://www.keiba-tips.top/race-20260518_05_01/?auth=line_only
```

毎日パイプライン実行後、ログに記載されるURLをリッチメニューに設定してください。

---

## 12. 運用チェックリスト（毎週末）

- [ ] ログファイル（`logs/YYYY-MM-DD.log`）に「Pipeline completed successfully」があるか確認
- [ ] WordPress上の予想ページが正常に表示されるか確認
- [ ] `?auth=line_only` なしでアクセスするとトップページへリダイレクトされるか確認
- [ ] 印（◎○▲△）が表示されているか確認
- [ ] レース開始後に印が変わっていないことを確認（固定されているか）
