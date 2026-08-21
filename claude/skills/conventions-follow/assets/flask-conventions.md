# Flask 拡張規約（ベース規約への追記サンプル）

`base-conventions.md` を土台に、Flask プロジェクト向けの具体値を埋めたもの。
`docs/CONVENTIONS.md` を起こすときは、ベースの各節をこの内容で置き換え／追記する。
節番号はベースに対応している。

---

## 0. 技術スタック

| ライブラリ | 担当範囲 | 触ってよい層 |
|---|---|---|
| Flask-Login | ログイン状態の保持、`@login_required`、`current_user` | views / api（認可判定のみ） |
| Flask-WTF | 入力フォームの定義・検証・CSRF | forms（定義） / views（検証呼び出し） |
| Flask-SQLAlchemy | モデル定義とクエリ | models / services |
| Flask-CORS | API のオリジン許可設定 | config（初期化のみ） |

`current_user` を service に直接持ち込まない。service には `user_id` などの素の値を渡す。
service が Flask のリクエスト文脈に依存すると、バッチや CLI から呼べなくなり、
テストのたびにアプリコンテキストを組み立てることになる。

---

## 2. ディレクトリ構成

```
<project_name>
├ app/
│ ├ api/          # JSON を返すエンドポイント（Blueprint）。薄く保つ
│ ├ config/       # 環境別設定、拡張（login_manager / db / cors）の初期化
│ ├ forms/        # Flask-WTF の Form 定義
│ ├ models/       # Flask-SQLAlchemy のモデル
│ ├ services/     # 業務ロジック。ここが最も厚い
│ ├ static/       # css / js / 画像
│ ├ templates/    # Jinja2 テンプレート。base.html とその継承先
│ ├ utils/        # 業務を知らない汎用処理
│ └ views/        # 画面を返すエンドポイント（Blueprint）。薄く保つ
├ db/             # マイグレーション、初期データ
├ instance/       # 環境固有ファイル（SQLite 実体、秘密設定）。git 管理外
├ docs/           # 設計・規約ドキュメント
├ scripts/        # 運用・移行スクリプト
└ tests/          # app/ の構成に対応させて配置
```

Blueprint は機能単位で `app/views/user_view.py`, `app/api/user_api.py` のように分け、
`app/__init__.py`（アプリケーションファクトリ）で登録する。

---

## 3. 配置判断表（Flask 版）

| 書こうとしている処理 | 置き場所 |
|---|---|
| ルーティング、テンプレート描画、リダイレクト | `app/views/` |
| JSON の入出力、ステータスコード | `app/api/` |
| 入力項目の定義・必須/長さ/形式の検証・CSRF | `app/forms/` |
| 「メールが既に登録済みなら弾く」等の業務判断 | `app/services/` |
| クエリ、保存、トランザクション | `app/services/`（クエリ式は `app/models/` のクラスメソッドでも可） |
| テーブル定義、リレーション、`__repr__` | `app/models/` |
| パスワードハッシュ、日付整形、スラッグ生成 | `app/utils/` |
| SECRET_KEY、DB URI、CORS 許可オリジン | `app/config/` |
| 初期データ投入、一括更新の手動実行 | `scripts/` |

---

## 4. 命名規約（Flask 版）

| 対象 | 規約 | 例 |
|---|---|---|
| ファイル | snake_case。役割サフィックスを付ける | `user_view.py` `user_api.py` `user_service.py` `user_form.py` |
| モデルクラス | PascalCase・単数形 | `User` `OrderItem` |
| テーブル名 | snake_case・複数形 | `users` `order_items` |
| Form クラス | PascalCase + `Form` | `UserRegisterForm` |
| Blueprint 変数 | `<機能>_bp` / API は `<機能>_api_bp` | `user_bp` `user_api_bp` |
| service 関数 | 動詞始まり snake_case | `register_user()` `fetch_active_users()` |
| テンプレート | `templates/<機能>/<画面>.html` | `templates/user/register.html` |
| テスト | `tests/test_<対象ファイル名>.py` | `tests/services/test_user_service.py` |

---

## 5. docstring 規約（日本語・Google スタイル）

日本語で、**1行タイトル → 空行 → 概要 → `Args:` / `Returns:` / `Raises:`** の順に書く。

```python
def register_user(email: str, password: str) -> User:
    """ユーザーの新規登録

    メールアドレスの重複を確認したうえでユーザーを作成する。
    パスワードは utils.security でハッシュ化してから保存するため、
    呼び出し側は平文のまま渡してよい。

    Args:
        email (str): 登録するメールアドレス。小文字化して保存される
        password (str): 平文パスワード。8文字以上であること

    Returns:
        User: 作成されたユーザー。ID は採番済み

    Raises:
        DuplicateEmailError: 同じメールアドレスが既に登録されている場合
    """
```

- 公開関数・クラス・Blueprint モジュールの先頭には必ず書く
- view / api の docstring には**エンドポイントの役割と対象 URL・メソッド**を書く
- 内部ヘルパーで名前から自明なものは省略してよい

---

## 9. Flask 固有の決めごと

### 9.1 入力は必ず Flask-WTF の Form 経由

画面からの入力は Form クラスを `app/forms/` に定義し、view では
`form.validate_on_submit()` で検証する。**`request.form` を直接読まない。**

理由は二つ。CSRF トークンの検証が Form 側に集約されているため、直接読むと保護が抜ける。
また検証ルールが Form に集まっていれば、項目を増やしたときの修正箇所が1つで済む。

API（`app/api/`）で JSON を受ける場合も、可能な限り同じ Form を
`Form(data=request.get_json(), meta={"csrf": False})` の形で再利用する。
再利用できない場合は検証ルールを service 側に置き、api には書かない。

### 9.2 テンプレートは base.html を継承する

`templates/base.html` にレイアウト・ナビゲーション・フラッシュメッセージ・
CSS/JS の読み込みをまとめ、個別画面は必ず継承する。

```jinja
{% extends "base.html" %}
{% block title %}ユーザー登録{% endblock %}
{% block content %}
  <form method="post" novalidate>
    {{ form.hidden_tag() }}
    {{ form.email.label }} {{ form.email() }}
    ...
  </form>
{% endblock %}
```

`{{ form.hidden_tag() }}` を必ず入れる（CSRF トークンがここに入る）。
継承しない独立 HTML を作らない。共通要素が二重管理になり、片方だけ古くなる。

### 9.3 views / api は薄く、service は厚く

view の責務は **認可 → Form 検証 → service 呼び出し → 描画/リダイレクト** のみ。

**DO:**

```python
@user_bp.route("/register", methods=["GET", "POST"])
def register():
    """ユーザー登録画面

    GET でフォームを表示し、POST で登録を実行する。
    登録可否の判断は user_service に委譲する。

    Returns:
        Response: 登録成功時は一覧へのリダイレクト、それ以外はフォーム画面
    """
    form = UserRegisterForm()
    if form.validate_on_submit():
        try:
            user_service.register_user(form.email.data, form.password.data)
        except DuplicateEmailError:
            flash("このメールアドレスは既に登録されています", "error")
        else:
            return redirect(url_for("user.index"))
    return render_template("user/register.html", form=form)
```

**DON'T:**

```python
@user_bp.route("/register", methods=["POST"])
def register():
    email = request.form["email"]                      # Form を通していない（CSRF が抜ける）
    if User.query.filter_by(email=email).first():      # 業務判断が view にある
        flash("登録済み")
        return render_template("user/register.html")
    user = User(email=email,
                password=hashlib.sha256(...).hexdigest())  # 汎用処理が view に埋まっている
    db.session.add(user)                               # 永続化が view にある
    db.session.commit()
    return redirect(url_for("user.index"))
```

DON'T 側の問題は、同じ登録処理を API から呼びたくなった瞬間に全部書き写すことになる点。
service に置いてあれば `user_api.py` は service を呼ぶだけで済む。

### 9.4 views と api は同じ service を共有する

同じ業務操作に対して service 関数は1つ。views と api はその共通の関数を呼び、
それぞれの入口が結果を HTML か JSON に変換するだけにする。

service は `flash` / `render_template` / `jsonify` / `request` を import しない。
これらが入った時点で、その service は片方の入口からしか使えなくなる。

### 9.5 例外設計

- service は業務的な失敗を専用例外（`DuplicateEmailError` など）で表す。
  `app/services/exceptions.py` に定義する
- views は例外を捕まえて `flash` + 再描画、api は捕まえて `jsonify` + 4xx に変換する
- SQLAlchemy の例外を入口までそのまま漏らさない。service で意味のある例外に包む

### 9.6 DB とトランザクション

- `db.session.commit()` は service の中で呼ぶ。view / api では呼ばない
- 複数テーブルにまたがる更新は1つの service 関数にまとめ、失敗時は `rollback()` する
- クエリは service か、モデルのクラスメソッド（`User.find_by_email()` 等）に置く。
  テンプレートからクエリを叩かない

### 9.7 設定と CORS

- 設定値は `app/config/` のクラス（`DevelopmentConfig` / `ProductionConfig`）に集約し、
  秘密値は `instance/` または環境変数から読む。ソースに直書きしない
- `Flask-CORS` は `app/__init__.py` のファクトリ内で `api` Blueprint に限定して適用する。
  アプリ全体に無条件で許可を出さない

---

## セルフチェック（Flask 追加分）

ベースのチェックに加えて照合する。

- [ ] 入力を `request.form` から直接読んでいないか（Form 経由か）
- [ ] テンプレートが `base.html` を継承し、`form.hidden_tag()` があるか
- [ ] view / api に DB クエリ・`db.session.commit()` が無いか
- [ ] service が `request` / `current_user` / `render_template` / `jsonify` を import していないか
- [ ] 同じ業務操作の service が views 用と api 用で二重化していないか
- [ ] docstring が日本語で、タイトル・概要・Args・Returns の形式になっているか
- [ ] CORS が `api` Blueprint に限定されているか
