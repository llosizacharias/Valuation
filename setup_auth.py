"""
setup_auth.py — configura usuários do dashboard.
Execute UMA VEZ para criar o dashboard_auth.yaml.

Uso:
  python setup_auth.py

Edite a lista USUARIOS abaixo antes de rodar.
As senhas são armazenadas com hash bcrypt — nunca em plaintext.
"""

import yaml
import streamlit_authenticator as stauth

# ─────────────────────────────────────────────────────────────
# EDITE AQUI: lista de usuários
# ─────────────────────────────────────────────────────────────
USUARIOS = [
    {"username": "admin",    "name": "Administrador",  "password": "valuation@2025"},
    {"username": "analista", "name": "Analista",       "password": "analise@2025"},
    {"username": "gestor",   "name": "Gestor",         "password": "gestao@2025"},
]

# ─────────────────────────────────────────────────────────────
# Gera hashes bcrypt
# ─────────────────────────────────────────────────────────────
# Compatível com streamlit-authenticator 0.2.x e 0.3.x
try:
    # 0.3.x+: Hasher não recebe lista no __init__
    from streamlit_authenticator.utilities.hasher import Hasher
    senhas_hashed = [Hasher.hash(u["password"]) for u in USUARIOS]
except Exception:
    # 0.2.x fallback
    senhas_plain  = [u["password"] for u in USUARIOS]
    senhas_hashed = stauth.Hasher(senhas_plain).generate()

credentials = {
    "usernames": {
        u["username"]: {
            "name":     u["name"],
            "password": hashed,
        }
        for u, hashed in zip(USUARIOS, senhas_hashed)
    }
}

config = {
    "credentials": credentials,
    "cookie": {
        "name":         "valuation_dashboard",
        "key":          "chave_super_secreta_troque_isso_2025",  # troque por string aleatória
        "expiry_days":  7,
    },
    "preauthorized": {
        "emails": []
    }
}

with open("dashboard_auth.yaml", "w") as f:
    yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

print("✅ dashboard_auth.yaml criado com sucesso!")
print(f"   Usuários configurados: {[u['username'] for u in USUARIOS]}")
print()
print("⚠️  IMPORTANTE:")
print("   1. Troque 'chave_super_secreta_troque_isso_2025' por uma string aleatória em dashboard_auth.yaml")
print("   2. Não commite dashboard_auth.yaml no GitHub (adicione ao .gitignore)")
print()
print("Para iniciar o dashboard:")
print("   streamlit run dashboard.py")