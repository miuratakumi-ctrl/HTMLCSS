"""config.env を読み込んで辞書で返す（外部ライブラリ不要）"""

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_config():
    env_path = os.path.join(BASE_DIR, "config.env")
    if not os.path.exists(env_path):
        raise FileNotFoundError(f"config.env が見つかりません: {env_path}")

    config = {}
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, val = line.partition("=")
                config[key.strip()] = val.strip()

    required = ["CREDENTIALS_JSON", "GA4_PROPERTY_ID", "GSC_PROPERTY"]
    missing = [k for k in required if not config.get(k)]
    if missing:
        raise ValueError(
            f"config.env に必須項目が不足しています: {', '.join(missing)}\n"
            f"config.env を開いて値を設定してください。"
        )

    return config
